'use strict';
const {createTransport,responseJSON}=require('../adapters/transport');
const {requestId}=require('../adapters/id');
const {sha256,utf8}=require('../adapters/hash');
const contract=require('../shared/feature_contract');
const prefix='/api/mini/account/v1';
const copy=x=>JSON.parse(JSON.stringify(x));
function createAccountClient(wx,config,guest) {
 const transport=createTransport(wx,{enabled:true,baseURL:config.origin,allowLocal:config.kind==='fixture',namespace:'account'});
 const anonymousTransport=createTransport(wx,{enabled:true,baseURL:config.origin,allowLocal:config.kind==='fixture',namespace:'account'});
 let current=null,generation=0,availability=null,contractFlight=null,pendingAuth=null;const listeners=new Set(),operations=new Map(),pendingWrites=new Map(),privateFiles=new Set();
 function emit(){for(const fn of listeners)fn(state());}
 function state(){return current?copy({actor:current.actor,features:current.features,expires_at:current.expires_at,authenticated_at:current.authenticated_at}):{actor:null,features:null};}
 function clear(){generation++;current=null;availability=null;contractFlight=null;pendingAuth=null;transport.clearSession();operations.clear();pendingWrites.clear();for(const f of privateFiles)wx.getFileSystemManager().unlink({filePath:f,complete:()=>{}});privateFiles.clear();emit();}
 function actor(){if(!current||current.expires_at*1000<=Date.now()){if(current)clear();throw Object.assign(Error('请先登录RacePick账号'),{status:401});}return current.actor;}
 function validateSession(value,tokenRequired){const now=Date.now(),parent=guest.session?.current();
  const issuedAt=value?.authenticated_at;
  const issuedMs=config.kind==='platform'&&Number.isInteger(issuedAt)?issuedAt*1000:null;
  // The server caps lifetime from issuance, which can be slightly ahead of the device clock.
  const maxExpiry=(issuedMs!==null&&issuedMs<=now+30000?Math.max(now,issuedMs):now)+3600000;
  if(!value||value.session_kind!=='racepick_account'||(tokenRequired&&(typeof value.token!=='string'||!/^rpa1\.[A-Za-z0-9._-]+$/.test(value.token)))||!value.actor||typeof value.actor.id!=='string'||!value.actor.id||/[\r\n]/.test(value.actor.id)||!['player','admin','superadmin'].includes(value.actor.role)||!Number.isInteger(value.expires_at)||value.expires_at*1000<=now||value.expires_at*1000>maxExpiry)throw Error('账号会话响应无效');if(config.kind==='platform'&&(value.schema_version!==1||value.token_type!=='Bearer'||!parent?.identity||!value.association||value.association.kind!=='session_only'||value.association.persistent_binding!==false||value.association.guest_identity!==parent.identity||value.expires_at*1000>parent.expiresAt))throw Error('账号会话与父访客绑定不符');}
 function install(value,ticket){sameActor(ticket);validateSession(value,true);clear();current=value;transport.setToken(value.token);emit();return state();}
 const uncertain=e=>!e.status||e.status>=500||e.code==='OPERATION_UNCERTAIN'||e.diagnostic?.kind==='response_decode';
 function sameActor(ticket){if(ticket!==generation)throw Error('账号已变化，已取消旧操作');}
 const wechatActions=['wechat-bind','wechat-unbind'];
 function wechatBinding(){
  const value=current?.features?.wechat_binding_v1;
  return config.wechatBinding===true&&value?.enabled===true&&typeof value.bound==='boolean'
   ? {bound:value.bound}:null;
 }
 function applyWechatResult(value,action,ticket,id){
  sameActor(ticket);
  if(value?.actor_id!==id||value.bound!==(action==='wechat-bind')||!wechatBinding()){
   throw Object.assign(Error('微信绑定回执未通过校验，请查询原操作'),{code:'OPERATION_UNCERTAIN'});
  }
  current.features={...current.features,wechat_binding_v1:{enabled:true,bound:value.bound}};
  emit();
  return {bound:value.bound};
 }
 function freshWechatCode(){
  return new Promise((resolve,reject)=>wx.login({
   timeout:10000,
   success(result){if(typeof result?.code==='string'&&result.code)resolve(result.code);else reject(Error('未取得微信身份，请重新操作'));},
   fail(){reject(Error('微信身份验证未完成'));}
  }));
 }
 let wechatFlight=false,authFlight=false;
 async function changeWechatBinding(action,password){
  const binding=wechatBinding();
  if(!binding||!wechatActions.includes(action))throw Error('当前服务未开放微信绑定管理');
  if(pendingAuth||wechatFlight||authFlight)throw Error('请先完成当前账号操作');
  if(binding.bound===(action==='wechat-bind'))throw Error('微信绑定状态已变化，请重新查看');
  if(typeof password!=='string'||!password||password.length>128)throw Error('请输入当前账号密码');
  const ticket=generation,id=actor().id;
  wechatFlight=true;
  try{
   const key=await requestId(wx);
   sameActor(ticket);
   const code=action==='wechat-bind'?await freshWechatCode():null;
   sameActor(ticket);
   try{
    const value=await direct('/auth/'+action,{method:'POST',data:{schema:1,request_key:key,password,...(code?{code}:{})}});
    return applyWechatResult(value,action,ticket,id);
   }catch(e){
    if(ticket===generation&&uncertain(e)&&e.body?.operation_resolved!==true)pendingAuth={key,action};
    throw e;
   }
  }finally{wechatFlight=false;}
 }
 async function recoverWechatBinding(key,action){
  if(wechatFlight||!wechatBinding()||pendingAuth?.key!==key||pendingAuth.action!==action)
   throw Error('只能查询当前会话的原微信绑定操作');
  const ticket=generation,id=actor().id;
  wechatFlight=true;
  try{
   const value=await direct('/operations/'+encodeURIComponent(key)+'?action='+action);
   const result=applyWechatResult(value,action,ticket,id);
   pendingAuth=null;
   return result;
  }catch(e){
   if(ticket===generation&&e.body?.operation_resolved===true)pendingAuth=null;
   throw e;
  }finally{wechatFlight=false;}
 }
 function blockPending(path){if(pendingWrites.has(path))throw Object.assign(Error('上次操作结果尚未确定，请先查询原操作'),{operationKey:pendingWrites.get(path)});}
 async function direct(path,{method='GET',data,account=true,anonymous=false,header={}}={}) {
  const ticket=generation,id=account?actor().id:null;
  try {
   const options={method,header:{...(data?{'Content-Type':'application/json'}:{}),...header,...(account?{'X-Account-ID':id}:{})},...(data!==undefined?{data}: {})};
   const result=account?responseJSON(await transport.request(prefix+path,options).promise):anonymous?responseJSON(await anonymousTransport.request(prefix+path,options).promise):await guest.accountRequest(path,options);
   if(ticket!==generation)throw Error('账号已变化，已丢弃旧响应');return result;
  }catch(e){if(account&&ticket===generation&&(e.status===401||['ACCOUNT_DISABLED','ROLE_CHANGED'].includes(e.code)))clear();throw e;}
 }
 function route(path,method){const url=path.split('?')[0];for(const [pattern,methods] of Object.entries(contract.paths)){const re=new RegExp('^'+pattern.replace(/\{[^}]+\}/g,'[a-zA-Z0-9_-]+')+'$');if(re.test(prefix+url)&&methods[method.toLowerCase()])return {pattern,op:methods[method.toLowerCase()]};}throw Error('该功能不在固定原生协议中');}
 function access(op){const a=op['x-access'];if(a&&a!=='public'){const role=actor().role;if(a==='superadmin'&&role!=='superadmin'||a==='reviewer'&&!['admin','superadmin'].includes(role))throw Object.assign(Error('当前账号没有该操作权限'),{status:403});}}
 async function call(path,{method='GET',data,key,header={}}={}){
  const ticket=generation;
  const {pattern,op}=route(path,method);access(op);
  if(!availability&&current){if(!contractFlight){const work=direct('/contract',{account:true}).then(r=>{sameActor(ticket);availability=r;}).finally(()=>{if(contractFlight===work)contractFlight=null;});contractFlight=work;}await contractFlight;}
  sameActor(ticket);
  const publicRead=op['x-access']==='public',account=!!current||!publicRead;
  if(availability){const entry=availability['x-native-policy']?.routes?.find(r=>r.path===pattern&&r.method===method);if(entry&&entry.available===false)throw Object.assign(Error('服务器尚未启用此功能'),{status:503});}
  const mutation=op['x-fixture-write']===true||(!['GET'].includes(method)&&!['/coverage/view','/usage/session'].includes(path.split('?')[0]));
  if(mutation)blockPending(method+':'+path);
  if(mutation){key=key||await requestId(wx);header={...header,'Idempotency-Key':key};}
  sameActor(ticket);
  try{return await direct(path,{method,data,account,anonymous:publicRead&&!current,header});}
  catch(e){if(mutation&&ticket===generation){operations.set(key,{path,method,actor:current?.actor.id});if(uncertain(e))pendingWrites.set(method+':'+path,key);e.operationKey=key;}throw e;}
 }
 return {
  sessionProof(group){const a=actor();if(!/^w[34]-[a-zA-Z0-9_-]{6,80}$/.test(group))throw Error('Invalid session proof scope');const parent=guest.identity?.()||guest.session?.current()?.identity;if(!parent)throw Error('Missing parent session');const tag=(kind,v)=>sha256(utf8(config.origin+'|'+group+'|'+kind+'|'+v));return {group,role:a.role,expiresAt:current.expires_at,actorTag:tag('actor',a.id),parentTag:tag('parent',parent),sessionTag:tag('native',current.token)};},
  state,clear,wechatBinding,changeWechatBinding,pendingAuth:()=>pendingAuth&&{...pendingAuth},subscribe:fn=>{listeners.add(fn);return()=>listeners.delete(fn);},generation:()=>generation,
  async refresh(){if(!current)return state();const ticket=generation,value=await direct('/session');try{validateSession(value,false);if(value.actor.id!==current.actor.id)throw Error('账号会话身份不符');}catch(e){if(ticket===generation)clear();throw Object.assign(Error('账号会话校验未通过，原草稿已保留'),{code:'ACCOUNT_SESSION_RESPONSE_INVALID',status:401});}current={...current,...value};emit();return state();},
  async auth(action,fields,key){if(!['register','login','resend-verification','forgot-password','verify-email','reset-password','redeem-invitation','reauth','wechat-login'].includes(action))throw Error('无效账号操作');
   if(action==='wechat-login'&&(config.wechatLogin!==true||current))throw Error('当前无法使用微信快捷登录');
   if(wechatFlight||authFlight)throw Error('请先完成当前账号操作');
   if(pendingAuth)throw Object.assign(Error('上次账号操作结果未确定，请先查询原操作'),{code:'AUTH_RECOVERY_REQUIRED',operationKey:pendingAuth.key,operationAction:pendingAuth.action});
   const allowed={register:['email','password','invite_code'],login:['email','password'],'resend-verification':['email'],'forgot-password':['email'],'verify-email':['token'],'reset-password':['token','password'],'redeem-invitation':['invite_code'],reauth:['password'],'wechat-login':[]};if(!fields||typeof fields!=='object'||Object.keys(fields).some(k=>!allowed[action].includes(k)))throw Error('账号请求字段不符合固定协议');
   const ticket=generation;authFlight=true;
   try{key=key||await requestId(wx);sameActor(ticket);
   if(action==='wechat-login'){fields={code:await freshWechatCode()};sameActor(ticket);}
   const account=['reauth','redeem-invitation'].includes(action),data={schema:1,request_key:key,...fields};
   try{const value=await direct('/auth/'+action,{method:'POST',data,account});sameActor(ticket);if(['login','reauth','wechat-login'].includes(action))return install(value,ticket);if(action==='redeem-invitation')clear();return value;}
   catch(e){if(e.status===401&&ticket===generation)clear();else if(ticket===generation&&uncertain(e)&&e.body?.operation_resolved!==true)pendingAuth={key,action};e.operationKey=key;e.operationAction=action;throw e;}
   }finally{authFlight=false;}
  },
  async recoverAuth(key,action,server){if(wechatActions.includes(action))return recoverWechatBinding(key,action);if(pendingAuth&&action!=='profile-save'&&(pendingAuth.key!==key||pendingAuth.action!==action))throw Error('只能查询原账号操作');const ticket=generation,account=['profile-save','redeem-invitation'].includes(action);let value;try{value=await direct('/operations/'+encodeURIComponent(key)+'?action='+action+(server?'&server='+server:''),{account});}catch(e){if(ticket===generation&&pendingAuth?.key===key&&pendingAuth.action===action&&e.body?.operation_resolved===true)pendingAuth=null;throw e;}sameActor(ticket);if(['login','reauth','wechat-login'].includes(action))return install(value,ticket);if(pendingAuth?.key===key&&pendingAuth.action===action)pendingAuth=null;return value;},
  async logout(){const ticket=generation;try{await direct('/session',{method:'DELETE'});}catch(e){if(e.status!==401)throw e;}finally{if(ticket===generation)clear();}},
  async contract(){const ticket=generation,value=await direct('/contract',{account:true});sameActor(ticket);availability=value;return availability;},call,
  async recover(key){const operation=operations.get(key);if(!operation)throw Error('当前会话没有此待核对操作');const r=await direct('/feature-operations/'+encodeURIComponent(key));pendingWrites.delete((operation.method||'POST')+':'+operation.path);operations.delete(key);return r;},
  async profile(server){return direct('/profile?server='+server);},
  async saveProfile(server,profile,revision,{intent='save',key}={}) {const ticket=generation;key=key||await requestId(wx);sameActor(ticket);try{return await direct('/profile?server='+server,{method:'PUT',data:{schema:1,request_key:key,explicit_save:true,intent,...(intent==='import_guest'?{confirm_guest_import:true}:{}),revision,cars:profile.cars,stars:profile.stars,...(server==='global'?{ocMap:profile.ocMap||{}}:{})}});}catch(e){e.operationKey=key;throw e;}},
  async uploadEvidence(sid,revision,file,key){const ticket=generation;actor();if(file.size>2097152)throw Error('证据图片不能超过2MiB');key=key||await requestId(wx);sameActor(ticket);const id=current.actor.id,path='/submissions/'+sid+'/images/upload?revision='+revision;blockPending('POST:'+path);
   try{const r=responseJSON(await transport.upload(prefix+path,{filePath:file.path,name:'image',formData:{},header:{'X-Account-ID':id,'Idempotency-Key':key}}).promise);if(ticket!==generation)throw Error('账号已变化');return r;}catch(e){if(ticket===generation){if(e.status===401){clear();throw e;}operations.set(key,{path,actor:id,method:'POST'});if(uncertain(e))pendingWrites.set('POST:'+path,key);e.operationKey=key;}throw e;}
  },
  async downloadEvidence(url){const id=actor().id,ticket=generation;if(!/^\/api\/mini\/account\/v1\/submissions\/[a-f0-9]+\/images\/[a-f0-9]+$/.test(url))throw Error('私有图片地址无效');
   return new Promise((resolve,reject)=>wx.downloadFile({url:config.origin+url,timeout:30000,header:{Authorization:'Bearer '+current.token,'X-Account-ID':id},success:r=>{if(r.statusCode!==200||ticket!==generation){if(r.tempFilePath)wx.getFileSystemManager().unlink({filePath:r.tempFilePath,complete:()=>{}});if(r.statusCode===401&&ticket===generation)clear();reject(Error('私有图片不可用'));return;}privateFiles.add(r.tempFilePath);resolve(r.tempFilePath);},fail:()=>reject(Error('图片下载未完成'))}));
  }
 };
}
module.exports={createAccountClient};
