'use strict';
const {createTransport,responseJSON}=require('../adapters/transport');
const {requestId}=require('../adapters/id');
const contract=require('../shared/feature_contract');
const prefix='/api/mini/account/v1';
const copy=x=>JSON.parse(JSON.stringify(x));
function createAccountClient(wx,config,guest) {
 const transport=createTransport(wx,{enabled:true,baseURL:config.origin,allowLocal:config.kind==='fixture',namespace:'account'});
 const anonymousTransport=createTransport(wx,{enabled:true,baseURL:config.origin,allowLocal:config.kind==='fixture',namespace:'account'});
 let current=null,generation=0,availability=null,contractFlight=null;const listeners=new Set(),operations=new Map(),pendingWrites=new Map(),privateFiles=new Set();
 function emit(){for(const fn of listeners)fn(state());}
 function state(){return current?copy({actor:current.actor,features:current.features,expires_at:current.expires_at,authenticated_at:current.authenticated_at}):{actor:null,features:null};}
 function clear(){generation++;current=null;transport.clearSession();operations.clear();pendingWrites.clear();for(const f of privateFiles)wx.getFileSystemManager().unlink({filePath:f,complete:()=>{}});privateFiles.clear();emit();}
 function actor(){if(!current||current.expires_at*1000<=Date.now()){if(current)clear();throw Object.assign(Error('请先登录RacePick账号'),{status:401});}return current.actor;}
 function install(value){if(value.session_kind!=='racepick_account'||!/^rpa1\./.test(value.token)||!value.actor||!value.actor.id)throw Error('账号会话响应无效');clear();current=value;transport.setToken(value.token);emit();return state();}
 const uncertain=e=>!e.status||e.status>=500||e.code==='OPERATION_UNCERTAIN';
 function sameActor(ticket){if(ticket!==generation)throw Error('账号已变化，已取消旧操作');}
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
  if(!availability&&current){if(!contractFlight)contractFlight=direct('/contract',{account:true}).then(r=>{availability=r;}).finally(()=>{contractFlight=null;});await contractFlight;}
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
  state,clear,subscribe:fn=>{listeners.add(fn);return()=>listeners.delete(fn);},generation:()=>generation,
  async refresh(){if(!current)return state();const value=await direct('/session');current={...current,...value};emit();return state();},
  async auth(action,fields,key){if(!['register','login','resend-verification','forgot-password','verify-email','reset-password','redeem-invitation','reauth'].includes(action))throw Error('无效账号操作');
   const ticket=generation;key=key||await requestId(wx);sameActor(ticket);const account=['reauth','redeem-invitation'].includes(action),data={schema:1,request_key:key,...fields};
   try{const value=await direct('/auth/'+action,{method:'POST',data,account});if(['login','reauth'].includes(action))return install(value);if(action==='redeem-invitation')clear();return value;}
   catch(e){if(e.status===401&&ticket===generation)clear();e.operationKey=key;throw e;}
  },
  async recoverAuth(key,action,server){const account=['profile-save','redeem-invitation'].includes(action);const value=await direct('/operations/'+encodeURIComponent(key)+'?action='+action+(server?'&server='+server:''),{account});if(['login','reauth'].includes(action))return install(value);return value;},
  async logout(){const ticket=generation;try{await direct('/session',{method:'DELETE'});}catch(e){if(e.status!==401)throw e;}finally{if(ticket===generation)clear();}},
  async contract(){availability=await direct('/contract',{account:true});return availability;},call,
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
