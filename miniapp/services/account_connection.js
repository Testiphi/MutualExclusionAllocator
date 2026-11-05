'use strict';
// Account A is an independent origin/session. It never borrows the OCR API.
const {createNativeApi}=require('../adapters/native_api');
const {createAccountClient}=require('./account');
const {responseJSON,networkDiagnostic}=require('../adapters/transport');
const {binding,verifyHealth,verifySnapshot,verifyProfile}=require('./account_readonly');
const error=code=>Object.assign(Error(({ACCOUNT_FEATURE_UNAVAILABLE:'当前服务暂未开放此功能',CLOUD_WRITE_DISABLED:'当前账号车库仅供读取，临时修改已保留',ACCOUNT_ACTION_DISABLED:'当前服务仅开放隔离账号登录',ACCOUNT_RETRY_WAIT:'请等待服务要求的时间，再核对原操作'})[code]||code),{code});
function validateAccountProfile(value){
 if(value?.enabled===false&&Object.keys(value).length===1)return {enabled:false};
 if(!value||value.enabled!==true||value.origin!==binding.origin||value.allowCloudWrites!==false||
    !/^mini-account-mirror-[a-zA-Z0-9_-]+$/.test(value.planId)||
    Object.keys(value).some(k=>!['enabled','origin','allowCloudWrites','planId'].includes(k)))throw error('ACCOUNT_CONFIG_INVALID');
 return {...value};
}
function createAccountConnection(wx,input){
 const profile=validateAccountProfile(input);if(!profile.enabled)throw error('ACCOUNT_CONFIG_DISABLED');
 const config={enabled:true,kind:'platform',origin:profile.origin},observed=Object.create(wx);
 let disposed=false,ready=false,readyFlight=null,retryAt=0,healthDiagnostic=null;const counts={health:0,guest:0,snapshot:0,login:0,profile:0,session:0,recovery:0};
 observed.request=o=>{
  if(!o.url.startsWith(config.origin+'/'))throw error('ACCOUNT_ROUTE_DENIED');
  const p=o.url.slice(config.origin.length),m=o.method||'GET';let counter;
  if(m==='GET'&&p==='/_account-test/health')counter='health';
  else if(m==='POST'&&p==='/api/mini/v1/session')counter='guest';
  else if(m==='GET'&&/^\/api\/mini\/v1\/snapshot\?server=(cn|global)$/.test(p))counter='snapshot';
  else if(m==='POST'&&p==='/api/mini/account/v1/auth/login')counter='login';
  else if(m==='GET'&&p==='/api/mini/account/v1/session')counter='session';
  else if(m==='GET'&&/^\/api\/mini\/account\/v1\/profile\?server=(cn|global)$/.test(p))counter='profile';
  else if(m==='GET'&&/^\/api\/mini\/account\/v1\/operations\/[a-zA-Z0-9_-]{16,80}\?action=login$/.test(p))counter='recovery';
  else throw error('ACCOUNT_ROUTE_DENIED');
  counts[counter]++;return wx.request(o);
 };
 observed.uploadFile=observed.downloadFile=()=>{throw error('ACCOUNT_MEDIA_DISABLED');};
 const guest=createNativeApi(observed,config),client=createAccountClient(observed,config,guest);
 let parent=null;
 guest.session.subscribe(s=>{if(s.identity!==parent){parent=s.identity;ready=false;client.clear();}});
 async function run(fn){if(disposed)throw error('ACCOUNT_CONNECTION_DISPOSED');if(retryAt>Date.now())throw Object.assign(error('ACCOUNT_RETRY_WAIT'),{retryAfterMs:retryAt-Date.now()});try{const value=await fn();if(disposed)throw error('ACCOUNT_CONNECTION_DISPOSED');return value;}catch(e){if(e.retryAfterMs>0)retryAt=Date.now()+e.retryAfterMs;throw e;}}
 async function health(){
  healthDiagnostic=null;
  const r=await new Promise((resolve,reject)=>observed.request({url:config.origin+'/_account-test/health',method:'GET',dataType:'other',responseType:'arraybuffer',timeout:30000,success:resolve,fail:reason=>{healthDiagnostic=networkDiagnostic(reason);reject(error('HEALTH_REQUEST_FAILED'));}}));
  healthDiagnostic={kind:'http',httpStatus:r.statusCode};
  if(r.statusCode!==200){const h=r.header||{},k=Object.keys(h).find(k=>k.toLowerCase()==='retry-after');throw Object.assign(error('HEALTH_REQUEST_FAILED'),{status:r.statusCode,retryAfterMs:Number(h[k])>0?Number(h[k])*1000:0});}
  verifyHealth(responseJSON(r));
 }
 async function ensure(){
  if(ready&&guest.session.current().expiresAt>Date.now())return;
  if(readyFlight)return readyFlight;
  const work=run(async()=>{await health();if(disposed)throw error('ACCOUNT_CONNECTION_DISPOSED');await guest.reconnectSession();const id=guest.identity();for(const s of ['cn','global']){if(disposed)throw error('ACCOUNT_CONNECTION_DISPOSED');verifySnapshot(await guest.snapshot(s),s,id);}const gate=await guest.accountRequest('/session',{method:'GET'});if(guest.identity()!==id||gate.session_kind!=='wechat_guest'||gate.actor!==null||gate.features?.profiles?.cn!=='account'||gate.features?.profiles?.global!=='account')throw error('ACCOUNT_GATE_INVALID');ready=true;});
  readyFlight=work;try{return await work;}finally{if(readyFlight===work)readyFlight=null;}
 }
 const unavailable=()=>Promise.reject(error('ACCOUNT_FEATURE_UNAVAILABLE'));
 const facade={state:client.state,generation:client.generation,subscribe:client.subscribe,clear:client.clear,pendingAuth:client.pendingAuth,
  async auth(action,fields,key){if(action!=='login')throw error('ACCOUNT_ACTION_DISABLED');if(client.pendingAuth())throw error('AUTH_RECOVERY_REQUIRED');return run(async()=>{await ensure();return client.auth(action,fields,key);});},
  refresh:()=>run(()=>client.refresh()),
  profile:server=>run(async()=>{if(!['cn','global'].includes(server))throw error('SERVER_INVALID');return verifyProfile(await client.profile(server),server);}),
  recoverAuth:(key,action)=>run(()=>{const p=client.pendingAuth();if(action!=='login'||!p||p.key!==key||p.action!==action)throw error('NO_PENDING_AUTH');return client.recoverAuth(key,action);}),
  saveProfile:()=>Promise.reject(error('CLOUD_WRITE_DISABLED')),logout:()=>Promise.reject(error('ACCOUNT_ACTION_DISABLED')),
  call:unavailable,contract:unavailable,recover:unavailable,uploadEvidence:unavailable,downloadEvidence:unavailable
 };
 return {client:facade,ensure,dispose(){disposed=true;ready=false;guest.session.invalidate();},origin:config.origin,planId:profile.planId,policy:{restricted:true,allowCloudWrites:false,actions:['login']},
  diagnostics:()=>({ready,healthDiagnostic,counts:{...counts},retryAfterMs:Math.max(0,retryAt-Date.now()),allowCloudWrites:false})};
}
module.exports={validateAccountProfile,createAccountConnection};
