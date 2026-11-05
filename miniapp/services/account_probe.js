'use strict';
const {createNativeApi}=require('../adapters/native_api');
const {createAccountClient}=require('./account');
const {createCloudProfile}=require('./cloud_profile');
const {responseJSON}=require('../adapters/transport');
const readonly=require('./account_readonly');
const fail=(message,code)=>Object.assign(Error(message),{code});
function createAccountProbe(wx,config,plan){
 if(!plan||plan.enabled!==true||!plan.isolatedServiceDeclared||!plan.accountRoutesDeclared||plan.origin!==config.origin||config.kind!=='platform'||!/^mini-account-probe-[a-zA-Z0-9_-]+$/.test(plan.planId))throw fail('账号隔离入口尚未确认','ACCOUNT_NOT_READY');
 const readOnly=plan.readOnly===true;if(readOnly&&(plan.allowCloudWrites!==false||config.origin!==readonly.binding.origin))throw fail('只读交付配置不符','ACCOUNT_NOT_READY');
 let bindingVerified=false,healthVerified=false,loginAttempted=false,retryAt=0,flight=false;const snapshotChecks={},profileChecks={};
 let state='idle',errorCode=null,connected=false,disposed=false;const stores=new Map(),counts={healthReads:0,snapshotReads:0,guestSessions:0,accountReads:0,authPosts:0,profileReads:0,profileWrites:0,recoveries:0,logouts:0};
 const observed=Object.create(wx),storagePrefix='racepick.account.probe.'+plan.planId+'.';
 observed.getStorageSync=k=>wx.getStorageSync(storagePrefix+k);observed.setStorageSync=(k,v)=>wx.setStorageSync(storagePrefix+k,v);observed.removeStorageSync=k=>wx.removeStorageSync(storagePrefix+k);
 observed.request=o=>{
  if(!o.url.startsWith(config.origin+'/api/mini/'))throw fail('拒绝其他入口','ROUTE_DENIED');const p=o.url.slice(config.origin.length),method=o.method||'GET';
  if(readOnly&&!((method==='POST'&&['/api/mini/v1/session','/api/mini/account/v1/auth/login'].includes(p))||(method==='GET'&&(p==='/api/mini/account/v1/session'||/^\/api\/mini\/v1\/snapshot\?server=(cn|global)$/.test(p)||/^\/api\/mini\/account\/v1\/profile\?server=(cn|global)$/.test(p)||/^\/api\/mini\/account\/v1\/operations\/[a-zA-Z0-9_-]{16,80}\?action=login$/.test(p)))))throw fail('本轮仅登录与认证只读','READONLY_ROUTE_DENIED');
  if(/^\/api\/mini\/v1\/snapshot\?server=(cn|global)$/.test(p)&&method==='GET')counts.snapshotReads++;
  else if(p==='/api/mini/v1/session'&&method==='POST')counts.guestSessions++;
  else if(p==='/api/mini/account/v1/session'&&method==='GET')counts.accountReads++;
  else if(p==='/api/mini/account/v1/session'&&method==='DELETE')counts.logouts++;
  else if(['/api/mini/account/v1/auth/login','/api/mini/account/v1/auth/reauth'].includes(p)&&method==='POST')counts.authPosts++;
  else if(/^\/api\/mini\/account\/v1\/profile\?server=(cn|global)$/.test(p)&&['GET','PUT'].includes(method)){if(method==='PUT'){if(!plan.allowCloudWrites)throw fail('本工程云端保存未获准','CLOUD_WRITE_DISABLED');counts.profileWrites++;}else counts.profileReads++;}
  else if(/^\/api\/mini\/account\/v1\/operations\/[a-zA-Z0-9_-]{16,80}\?action=(login|reauth|profile-save)(?:&server=(cn|global))?$/.test(p)&&method==='GET')counts.recoveries++;
  else throw fail('本工程仅开放账号A基础验收路径','ROUTE_DENIED');return wx.request(o);
 };
 observed.uploadFile=()=>{throw fail('账号基础验收不上传图片','MEDIA_DISABLED');};observed.downloadFile=()=>{throw fail('账号基础验收不下载私人图片','MEDIA_DISABLED');};
 const guest=createNativeApi(observed,config),client=createAccountClient(observed,config,guest);
 let parent=null;const unwatch=guest.session.subscribe(s=>{if(s.identity!==parent){parent=s.identity;connected=false;bindingVerified=false;Object.keys(snapshotChecks).forEach(k=>delete snapshotChecks[k]);Object.keys(profileChecks).forEach(k=>delete profileChecks[k]);client.clear();stores.clear();}});client.subscribe(()=>{if(!client.state().actor){stores.clear();Object.keys(profileChecks).forEach(k=>delete profileChecks[k]);}});
 function guard(){if(disposed)throw fail('工程已关闭','DISPOSED');}
 function server(value){if(!['cn','global'].includes(value))throw fail('服别无效','SERVER_INVALID');return value;}
 async function perform(name,fn){guard();if(flight)throw fail('请等待当前操作','PROBE_BUSY');if(retryAt>Date.now())throw fail('遵守服务端等待时间，不自动重发','RETRY_AFTER_WAIT');flight=true;state=name;errorCode=null;try{const r=await fn();state=client.state().actor?'logged_in':'connected';return r;}catch(e){if(e.retryAfterMs>0)retryAt=Date.now()+e.retryAfterMs;state='failed';errorCode=e.code||'ACCOUNT_REQUEST_FAILED';throw e;}finally{flight=false;}}
 function readonlyGuard(){if(readOnly)throw fail('本轮只读，不执行此操作','READONLY_ACTION_DENIED');}
 async function health(){
  counts.healthReads++;const response=await new Promise((resolve,reject)=>wx.request({url:config.origin+'/_account-test/health',method:'GET',dataType:'other',responseType:'arraybuffer',timeout:30000,success:resolve,fail:()=>reject(fail('健康读取未完成','HEALTH_REQUEST_FAILED'))}));
  if(response.statusCode!==200){const e=fail('健康检查未通过','HEALTH_REQUEST_FAILED');e.status=response.statusCode;const h=response.header||{},k=Object.keys(h).find(k=>k.toLowerCase()==='retry-after');if(Number(h[k])>0)e.retryAfterMs=Number(h[k])*1000;throw e;}
  readonly.verifyHealth(responseJSON(response));healthVerified=true;
 }
 function supported(value){if(value?.features?.profiles?.cn!=='account'||value?.features?.profiles?.global!=='account')throw fail('两服云车库组件未齐备','PROFILE_COMPONENT_UNAVAILABLE');}
 async function load(s){server(s);return perform('loading_profile',async()=>{if(!connected||!client.state().actor)throw fail('请先登录隔离账号','LOGIN_REQUIRED');const ticket=client.generation(),id=guest.identity();const source=readOnly?{state:client.state,profile:async server=>readonly.verifyProfile(await client.profile(server),server)}:client;const store=createCloudProfile(observed,source,config.origin,s);await store.init();if(ticket!==client.generation()||id!==guest.identity())throw fail('身份已变化','STALE_SESSION_RESPONSE');stores.set(s,store);if(readOnly){const r=store.remote();profileChecks[s]={revision:r.revision,kind:r.profile===null?'null':r.profile.cars.length===0?'empty':'saved',authenticatedRead:true};}return store.snapshot();});}
 function store(s){server(s);const v=stores.get(s);if(!v)throw fail('先读取该服车库，失败时不覆盖本机','PROFILE_NOT_LOADED');return v;}
 return {report(){const actor=client.state().actor;return {state,errorCode,readOnly,bindingVerified,healthVerified,snapshotChecks:{...snapshotChecks},profileChecks:{...profileChecks},sessionValidation:actor?{tokenKind:true,parentIdentityMatches:true,sessionOnly:true,expiresWithinParent:true,roleMatches:actor.role==='player'}:null,loginAttempted,retryAfterMs:Math.max(0,retryAt-Date.now()),connected,loggedIn:!!actor,role:actor?.role||null,pendingAuth:!!client.pendingAuth(),allowCloudWrites:plan.allowCloudWrites===true,profiles:Object.fromEntries([...stores].map(([s,v])=>[s,{hasProfile:v.snapshot()!==null,dirty:v.state().dirty,status:v.state().status,pendingSave:!!v.pendingKey(),hasConflict:!!v.conflict()}])),counts:{...counts},registration:false,mailActions:false,media:false,batchesBE:false};},
  connect:()=>perform('connecting',async()=>{if(readOnly&&connected)throw fail('本轮父访客已建立','ALREADY_CONNECTED');if(readOnly)await health();await guest.reconnectSession();if(readOnly){const id=guest.identity();for(const s of ['cn','global']){const value=await guest.snapshot(s);readonly.verifySnapshot(value,s,id);if(guest.identity()!==id)throw fail('父访客已变化','STALE_SESSION_RESPONSE');snapshotChecks[s]=true;}bindingVerified=true;}const v=await guest.accountRequest('/session',{method:'GET'});if(v.session_kind!=='wechat_guest'||v.actor!==null)throw fail('账号入口访客状态不符','ACCOUNT_GATE_INVALID');supported(v);connected=true;}),
  login:fields=>perform('logging_in',async()=>{if(!connected||(readOnly&&!bindingVerified))throw fail('请先核对隔离账号入口','ACCOUNT_NOT_READY');if(readOnly&&loginAttempted)throw fail('本轮已提交登录；未知结果仅查询原操作','LOGIN_ALREADY_ATTEMPTED');if(readOnly)loginAttempted=true;await client.auth('login',fields);if(readOnly&&client.state().actor?.role!=='player'){client.clear();throw fail('隔离普通玩家角色不符','ACCOUNT_ROLE_MISMATCH');}try{supported(client.state());}catch(e){client.clear();throw e;}}),
  recoverLogin:()=>perform('recovering_login',async()=>{const p=client.pendingAuth();if(!p||!['login','reauth'].includes(p.action))throw fail('没有可核对的原登录操作','NO_PENDING_AUTH');await client.recoverAuth(p.key,p.action);if(readOnly&&client.state().actor?.role!=='player'){client.clear();throw fail('隔离普通玩家角色不符','ACCOUNT_ROLE_MISMATCH');}supported(client.state());}),
  refresh:()=>perform('refreshing',()=>client.refresh()),load,
  stageEmpty(s){guard();readonlyGuard();const v=store(s);v.importGuest({cars:[],stars:{},...(s==='global'?{ocMap:{}}:{})});},
  save:s=>perform('saving_profile',async()=>{readonlyGuard();if(!plan.allowCloudWrites)throw fail('当前仅本机草稿，云端保存尚未获准','CLOUD_WRITE_DISABLED');await store(s).flush();}),
  recoverSave:s=>perform('recovering_profile',()=>{readonlyGuard();return store(s).recover();}),
  useRemote:s=>perform('loading_remote',()=>{readonlyGuard();return store(s).useRemote();}),
  logout:()=>perform('logging_out',()=>{readonlyGuard();return client.logout();}),
  dispose(){disposed=true;unwatch();client.clear();guest.session.invalidate();stores.clear();}
 };
}
module.exports={createAccountProbe};
