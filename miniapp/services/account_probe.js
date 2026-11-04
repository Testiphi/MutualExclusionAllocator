'use strict';
const {createNativeApi}=require('../adapters/native_api');
const {createAccountClient}=require('./account');
const {createCloudProfile}=require('./cloud_profile');
const fail=(message,code)=>Object.assign(Error(message),{code});
function createAccountProbe(wx,config,plan){
 if(!plan||plan.enabled!==true||!plan.isolatedServiceDeclared||!plan.accountRoutesDeclared||plan.origin!==config.origin||config.kind!=='platform'||!/^mini-account-probe-[a-zA-Z0-9_-]+$/.test(plan.planId))throw fail('账号隔离入口尚未确认','ACCOUNT_NOT_READY');
 let state='idle',errorCode=null,connected=false,disposed=false;const stores=new Map(),counts={guestSessions:0,accountReads:0,authPosts:0,profileReads:0,profileWrites:0,recoveries:0,logouts:0};
 const observed=Object.create(wx),storagePrefix='racepick.account.probe.'+plan.planId+'.';
 observed.getStorageSync=k=>wx.getStorageSync(storagePrefix+k);observed.setStorageSync=(k,v)=>wx.setStorageSync(storagePrefix+k,v);observed.removeStorageSync=k=>wx.removeStorageSync(storagePrefix+k);
 observed.request=o=>{
  if(!o.url.startsWith(config.origin+'/api/mini/'))throw fail('拒绝其他入口','ROUTE_DENIED');const p=o.url.slice(config.origin.length),method=o.method||'GET';
  if(p==='/api/mini/v1/session'&&method==='POST')counts.guestSessions++;
  else if(p==='/api/mini/account/v1/session'&&method==='GET')counts.accountReads++;
  else if(p==='/api/mini/account/v1/session'&&method==='DELETE')counts.logouts++;
  else if(['/api/mini/account/v1/auth/login','/api/mini/account/v1/auth/reauth'].includes(p)&&method==='POST')counts.authPosts++;
  else if(/^\/api\/mini\/account\/v1\/profile\?server=(cn|global)$/.test(p)&&['GET','PUT'].includes(method)){if(method==='PUT'){if(!plan.allowCloudWrites)throw fail('本工程云端保存未获准','CLOUD_WRITE_DISABLED');counts.profileWrites++;}else counts.profileReads++;}
  else if(/^\/api\/mini\/account\/v1\/operations\/[a-zA-Z0-9_-]{16,80}\?action=(login|reauth|profile-save)(?:&server=(cn|global))?$/.test(p)&&method==='GET')counts.recoveries++;
  else throw fail('本工程仅开放账号A基础验收路径','ROUTE_DENIED');return wx.request(o);
 };
 observed.uploadFile=()=>{throw fail('账号基础验收不上传图片','MEDIA_DISABLED');};observed.downloadFile=()=>{throw fail('账号基础验收不下载私人图片','MEDIA_DISABLED');};
 const guest=createNativeApi(observed,config),client=createAccountClient(observed,config,guest);
 let parent=null;const unwatch=guest.session.subscribe(s=>{if(s.identity!==parent){parent=s.identity;client.clear();stores.clear();}});client.subscribe(()=>{if(!client.state().actor)stores.clear();});
 function guard(){if(disposed)throw fail('工程已关闭','DISPOSED');}
 function server(value){if(!['cn','global'].includes(value))throw fail('服别无效','SERVER_INVALID');return value;}
 async function perform(name,fn){guard();state=name;errorCode=null;try{const r=await fn();state=client.state().actor?'logged_in':'connected';return r;}catch(e){state='failed';errorCode=e.code||'ACCOUNT_REQUEST_FAILED';throw e;}}
 function supported(value){if(value?.features?.profiles?.cn!=='account'||value?.features?.profiles?.global!=='account')throw fail('两服云车库组件未齐备','PROFILE_COMPONENT_UNAVAILABLE');}
 async function load(s){server(s);return perform('loading_profile',async()=>{if(!connected||!client.state().actor)throw fail('请先登录隔离账号','LOGIN_REQUIRED');const store=createCloudProfile(observed,client,config.origin,s);await store.init();stores.set(s,store);return store.snapshot();});}
 function store(s){server(s);const v=stores.get(s);if(!v)throw fail('先读取该服车库，失败时不覆盖本机','PROFILE_NOT_LOADED');return v;}
 return {report(){const actor=client.state().actor;return {state,errorCode,connected,loggedIn:!!actor,role:actor?.role||null,pendingAuth:!!client.pendingAuth(),allowCloudWrites:plan.allowCloudWrites===true,profiles:Object.fromEntries([...stores].map(([s,v])=>[s,{hasProfile:v.snapshot()!==null,dirty:v.state().dirty,status:v.state().status,pendingSave:!!v.pendingKey(),hasConflict:!!v.conflict()}])),counts:{...counts},registration:false,mailActions:false,media:false,batchesBE:false};},
  connect:()=>perform('connecting',async()=>{await guest.reconnectSession();const v=await guest.accountRequest('/session',{method:'GET'});if(v.session_kind!=='wechat_guest'||v.actor!==null)throw fail('账号入口访客状态不符','ACCOUNT_GATE_INVALID');supported(v);connected=true;}),
  login:fields=>perform('logging_in',async()=>{if(!connected)throw fail('请先核对隔离账号入口','ACCOUNT_NOT_READY');await client.auth('login',fields);try{supported(client.state());}catch(e){client.clear();throw e;}}),
  recoverLogin:()=>perform('recovering_login',async()=>{const p=client.pendingAuth();if(!p||!['login','reauth'].includes(p.action))throw fail('没有可核对的原登录操作','NO_PENDING_AUTH');await client.recoverAuth(p.key,p.action);supported(client.state());}),
  refresh:()=>perform('refreshing',()=>client.refresh()),load,
  stageEmpty(s){guard();const v=store(s);v.importGuest({cars:[],stars:{},...(s==='global'?{ocMap:{}}:{})});},
  save:s=>perform('saving_profile',async()=>{if(!plan.allowCloudWrites)throw fail('当前仅本机草稿，云端保存尚未获准','CLOUD_WRITE_DISABLED');await store(s).flush();}),
  recoverSave:s=>perform('recovering_profile',()=>store(s).recover()),
  useRemote:s=>perform('loading_remote',()=>store(s).useRemote()),
  logout:()=>perform('logging_out',()=>client.logout()),
  dispose(){disposed=true;unwatch();client.clear();guest.session.invalidate();stores.clear();}
 };
}
module.exports={createAccountProbe};
