'use strict';
// Account A is an independent origin/session. It never borrows the OCR API.
const {createNativeApi}=require('../adapters/native_api');
const {createAccountClient}=require('./account');
const {responseJSON,networkDiagnostic}=require('../adapters/transport');
const {binding,verifyHealth,verifySnapshot,verifyProfile}=require('./account_readonly');
const writableBinding=require('./account_writable_binding');
const {createWriteAcceptance,equal}=require('./account_write_acceptance');
const readbackBinding=require('./account_readback_binding');
const {createConflictAcceptance}=require('./account_conflict_acceptance');
const {validateProductionProfile,verifyProductionHealth}=require('./account_production');
const bindingActions=['wechat-bind','wechat-unbind'];
const registrationActions=['register','resend-verification','verify-email'];
const error=code=>Object.assign(Error(({ACCOUNT_FEATURE_UNAVAILABLE:'当前服务暂未开放此功能',CLOUD_WRITE_DISABLED:'当前账号车库仅供读取，临时修改已保留',ACCOUNT_ACTION_DISABLED:'当前服务仅开放隔离账号登录',ACCOUNT_RETRY_WAIT:'请等待服务要求的时间，再核对原操作'})[code]||code),{code});
function validateAccountProfile(value){
 if(value?.mode==='production-a')return validateProductionProfile(value);
 if(value?.enabled===false&&Object.keys(value).length===1)return {enabled:false};
 if(!value||value.enabled!==true||value.origin!==binding.origin||typeof value.allowCloudWrites!=='boolean'||!/^mini-account-mirror-[a-zA-Z0-9_-]+$/.test(value.planId))throw error('ACCOUNT_CONFIG_INVALID');
 const conflict=value.conflictRole!==undefined;
 if(value.allowCloudWrites&&(!/^mini-account-mirror-write-[a-zA-Z0-9_-]+$/.test(value.planId)||value.writableReceipt!==writableBinding.handoff_sha256))throw error('ACCOUNT_CONFIG_INVALID');
 if(value.readbackReceipt!==undefined&&(value.allowCloudWrites||conflict||!/^mini-account-mirror-readback-[a-zA-Z0-9_-]+$/.test(value.planId)||value.readbackReceipt!==readbackBinding.receipt_sha256))throw error('ACCOUNT_CONFIG_INVALID');
 if(conflict&&(!['a','b'].includes(value.conflictRole)||!new RegExp('^mini-account-mirror-write-w3-'+value.conflictRole+'-[a-zA-Z0-9_-]+$').test(value.planId)||!/^w3-[a-zA-Z0-9_-]{6,80}$/.test(value.conflictGroup)||value.conflictReceipt!==readbackBinding.receipt_sha256))throw error('ACCOUNT_CONFIG_INVALID');
 const registration=value.registrationDelivery!==undefined;
 if(registration&&(value.allowCloudWrites||conflict||value.readbackReceipt!==undefined||!/^mini-account-mirror-registration-[a-zA-Z0-9_-]+$/.test(value.planId)||typeof value.registrationDelivery!=='string'||!/^[a-f0-9]{24}$/.test(value.registrationDelivery)))throw error('ACCOUNT_CONFIG_INVALID');
 const wechatBinding=value.wechatBindingDelivery!==undefined;
 if(wechatBinding&&(registration||value.allowCloudWrites||conflict||value.readbackReceipt!==undefined||!/^mini-account-mirror-wechat-binding-[a-zA-Z0-9_-]+$/.test(value.planId)||typeof value.wechatBindingDelivery!=='string'||!/^[a-f0-9]{24}$/.test(value.wechatBindingDelivery)))throw error('ACCOUNT_CONFIG_INVALID');
 const allowed=['enabled','origin','allowCloudWrites','planId',...(registration?['registrationDelivery']:[]),...(wechatBinding?['wechatBindingDelivery']:[]),...(value.allowCloudWrites?['writableReceipt']:[]),...(value.readbackReceipt!==undefined?['readbackReceipt']:[]),...(conflict?['conflictRole','conflictGroup','conflictReceipt']:[])];
 if(Object.keys(value).some(k=>!allowed.includes(k)))throw error('ACCOUNT_CONFIG_INVALID');
 return {...value};
}
function createAccountConnection(wx,input){
 const profile=validateAccountProfile(input);if(!profile.enabled)throw error('ACCOUNT_CONFIG_DISABLED');
 const formal=profile.mode==='production-a',healthPath=formal?'/api/health':'/_account-test/health';
 const registration=!!profile.registrationDelivery,actions=['login',...(registration?registrationActions:[])];
 const wechatBinding=!!profile.wechatBindingDelivery;
 const conflict=!!profile.conflictRole;
 const readback=!!profile.readbackReceipt,readbackSeen=new Set();let readbackHalted=false;
 const writable=profile.allowCloudWrites===true;let guard=null,guardActor=null;const catalogs={};
 function acceptance(){const id=client.state().actor?.id;if(!id)throw error('ACCOUNT_SESSION_REQUIRED');if(id!==guardActor){guard=conflict?createConflictAcceptance(wx,profile,id):createWriteAcceptance(wx,profile.planId,id);guardActor=id;}return guard;}
 const config={enabled:true,kind:'platform',origin:profile.origin};
 // Some WeChat hosts expose wx APIs as accessors. Keep overrides off that prototype.
 const observed={
  login:options=>wx.login(options),
  getRandomValues:typeof wx.getRandomValues==='function'?options=>wx.getRandomValues(options):undefined,
  getFileSystemManager:()=>wx.getFileSystemManager()
 };
 let authFlight=false,disposed=false,ready=false,readyFlight=null,retryAt=0,healthDiagnostic=null;const counts={health:0,guest:0,snapshot:0,login:0,profile:0,session:0,recovery:0,...(registration?Object.fromEntries(registrationActions.map(a=>[a,0])):{}),...((formal||writable||readback||conflict||registration)?{put:0}: {})};
 observed.request=o=>{
  if(!o.url.startsWith(config.origin+'/'))throw error('ACCOUNT_ROUTE_DENIED');
  const p=o.url.slice(config.origin.length),m=o.method||'GET';let counter;
  if(m==='GET'&&p===healthPath)counter='health';
  else if(m==='POST'&&p==='/api/mini/v1/session')counter='guest';
  else if(m==='GET'&&/^\/api\/mini\/v1\/snapshot\?server=(cn|global)$/.test(p))counter='snapshot';
  else if(m==='POST'&&p==='/api/mini/account/v1/auth/login')counter='login';
  else if(registration&&m==='POST'&&registrationActions.some(a=>p==='/api/mini/account/v1/auth/'+a))counter=p.split('/').pop();
  else if(wechatBinding&&m==='POST'&&bindingActions.some(action=>p==='/api/mini/account/v1/auth/'+action))counter=p.split('/').pop();
  else if(wechatBinding&&m==='GET'&&/^\/api\/mini\/account\/v1\/operations\/[a-zA-Z0-9_-]{16,80}\?action=wechat-(bind|unbind)$/.test(p))counter='recovery';
  else if((m==='GET'||wechatBinding&&m==='DELETE')&&p==='/api/mini/account/v1/session')counter='session';
  else if(m==='GET'&&/^\/api\/mini\/account\/v1\/profile\?server=(cn|global)$/.test(p))counter='profile';
  else if(writable&&m==='PUT'&&/^\/api\/mini\/account\/v1\/profile\?server=(cn|global)$/.test(p))counter='put';
  else if(writable&&m==='GET'&&/^\/api\/mini\/account\/v1\/operations\/[a-zA-Z0-9_-]{16,80}\?action=profile-save&server=(cn|global)$/.test(p))counter='recovery';
  else if(m==='GET'&&/^\/api\/mini\/account\/v1\/operations\/[a-zA-Z0-9_-]{16,80}\?action=login$/.test(p))counter='recovery';
  else if(registration&&m==='GET'&&/^\/api\/mini\/account\/v1\/operations\/[a-zA-Z0-9_-]{16,80}\?action=(register|resend-verification|verify-email)$/.test(p))counter='recovery';
  else throw error('ACCOUNT_ROUTE_DENIED');
  counts[counter]=(counts[counter]||0)+1;return wx.request(o);
 };
 observed.uploadFile=observed.downloadFile=()=>{throw error('ACCOUNT_MEDIA_DISABLED');};
 const guest=createNativeApi(observed,config),client=createAccountClient(observed,{...config,wechatBinding},guest);
 let parent=null;
 guest.session.subscribe(s=>{if(s.identity!==parent){parent=s.identity;ready=false;client.clear();}});
 async function run(fn){if(disposed)throw error('ACCOUNT_CONNECTION_DISPOSED');if(retryAt>Date.now())throw Object.assign(error('ACCOUNT_RETRY_WAIT'),{retryAfterMs:retryAt-Date.now()});try{const value=await fn();if(disposed)throw error('ACCOUNT_CONNECTION_DISPOSED');return value;}catch(e){if(e.retryAfterMs>0)retryAt=Date.now()+e.retryAfterMs;throw e;}}
 async function health(writing=false){
  healthDiagnostic=null;
  const r=await new Promise((resolve,reject)=>observed.request({url:config.origin+healthPath,method:'GET',dataType:'other',responseType:'arraybuffer',timeout:30000,success:resolve,fail:reason=>{healthDiagnostic=networkDiagnostic(reason);reject(error('HEALTH_REQUEST_FAILED'));}}));
  healthDiagnostic={kind:'http',httpStatus:r.statusCode};
  if(r.statusCode!==200){const h=r.header||{},k=Object.keys(h).find(k=>k.toLowerCase()==='retry-after');throw Object.assign(error('HEALTH_REQUEST_FAILED'),{status:r.statusCode,retryAfterMs:Number(h[k])>0?Number(h[k])*1000:0});}
  if(formal)verifyProductionHealth(responseJSON(r),profile.fixedRuntime.snapshot_versions,writing);else verifyHealth(responseJSON(r),writable||readback||conflict,profile.registrationDelivery,profile.wechatBindingDelivery);
 }
 async function ensure(){
  if(ready&&guest.session.current().expiresAt>Date.now())return;
  if(readyFlight)return readyFlight;
  const work=run(async()=>{await health();if(disposed)throw error('ACCOUNT_CONNECTION_DISPOSED');await guest.reconnectSession();const id=guest.identity();for(const s of ['cn','global']){if(disposed)throw error('ACCOUNT_CONNECTION_DISPOSED');catalogs[s]=verifySnapshot(await guest.snapshot(s),s,id,profile.fixedRuntime);}const gate=await guest.accountRequest('/session',{method:'GET'});if(guest.identity()!==id||gate.session_kind!=='wechat_guest'||gate.actor!==null||(registration&&gate.features?.authentication?.isolated_player_registration!==true)||gate.features?.profiles?.cn!=='account'||gate.features?.profiles?.global!=='account')throw error('ACCOUNT_GATE_INVALID');ready=true;});
  readyFlight=work;try{return await work;}finally{if(readyFlight===work)readyFlight=null;}
 }
 const unavailable=()=>Promise.reject(error('ACCOUNT_FEATURE_UNAVAILABLE'));
 const facade={sessionProof:group=>{if(conflict&&group!==profile.conflictGroup)throw error('W3_STOP');return client.sessionProof(group);},confirmConflictPeer:peer=>{if(!conflict)throw error('W3_STOP');return acceptance().attest(client.sessionProof(profile.conflictGroup),peer);},state:client.state,generation:client.generation,subscribe:client.subscribe,clear:client.clear,pendingAuth:client.pendingAuth,
  async auth(action,fields,key){if(!actions.includes(action)||(registration&&action!=='login'&&client.state().actor))throw error('ACCOUNT_ACTION_DISABLED');if(client.pendingAuth()||authFlight)throw error('AUTH_RECOVERY_REQUIRED');authFlight=true;try{return await run(async()=>{await ensure();return client.auth(action,fields,key);});}finally{authFlight=false;}},
  wechatBinding:client.wechatBinding,
  changeWechatBinding:(action,password)=>run(async()=>{if(!wechatBinding)throw error('ACCOUNT_ACTION_DISABLED');await health();return client.changeWechatBinding(action,password);}),
  refresh:()=>run(()=>client.refresh()),
  profile:server=>run(async()=>{if(!['cn','global'].includes(server))throw error('SERVER_INVALID');if(readback){if(readbackHalted||readbackSeen.has(server))throw error('READBACK_STOP');readbackSeen.add(server);}const g=!formal&&(writable||conflict)?acceptance():null;g?.beforeRead(server);try{const value=verifyProfile(await client.profile(server),server);if(readback&&(value.revision!==readbackBinding.profiles[server].revision||!equal(value.profile,readbackBinding.profiles[server].profile)))throw error('READBACK_RECORD_CHANGED');return g?g.read(value,server):value;}catch(e){if(readback)readbackHalted=true;g?.failed(e);throw e;}}),
  recoverAuth:(key,action,server)=>run(async()=>{if(writable&&action==='profile-save'){if(formal)return client.recoverAuth(key,action,server);const g=acceptance();g.recovery(key,server);try{return g.success(await client.recoverAuth(key,action,server),server);}catch(e){if(conflict&&e.status===409&&e.code==='PROFILE_CONFLICT'){try{g.acceptConflict(e,server);}catch(invalid){g.failed(invalid);throw invalid;}}throw e;}}const p=client.pendingAuth();if(!(actions.includes(action)||(wechatBinding&&bindingActions.includes(action)))||!p||p.key!==key||p.action!==action)throw error('NO_PENDING_AUTH');return client.recoverAuth(key,action);}),
  saveProfile:(server,draft,revision,options={})=>run(async()=>{if(!writable)throw error('CLOUD_WRITE_DISABLED');if(!['cn','global'].includes(server))throw error('SERVER_INVALID');verifyProfile({server,storage:'account',remote_supported:true,revision:Math.max(1,revision),profile:draft},server);if(formal&&options.intent!=='save')throw error('ACCOUNT_ACTION_DISABLED');const g=formal?null:acceptance(),generation=client.generation();try{await health(true);}catch(e){g?.failed(e);throw e;}if(client.generation()!==generation)throw error('STALE_ACCOUNT_PROFILE');g?.beforeSave(server,draft,revision,options,conflict?client.sessionProof(profile.conflictGroup):null);try{const result=await client.saveProfile(server,draft,revision,options);if(g)return g.success(result,server);if(result?.server!==server||result.revision!==revision+1)throw Object.assign(Error('保存回执异常，需核对原操作'),{status:200,code:'OPERATION_UNCERTAIN'});return result;}catch(e){e.operationKey=options.key;if(conflict){try{if(!g.acceptConflict(e,server))g.failed(e);}catch(invalid){invalid.operationKey=options.key;g.failed(invalid);throw invalid;}}else g?.failed(e);throw e;}}).catch(e=>{if(!e.operationKey)e.notSent=true;throw e;}),logout:()=>wechatBinding?run(()=>client.logout()):Promise.reject(error('ACCOUNT_ACTION_DISABLED')),
  call:unavailable,contract:unavailable,recover:unavailable,uploadEvidence:unavailable,downloadEvidence:unavailable
 };
 return {client:facade,ensure,dispose(){disposed=true;ready=false;guest.session.invalidate();},origin:config.origin,planId:profile.planId,policy:{restricted:true,allowCloudWrites:writable,writeAcceptance:writable&&!conflict&&!formal,productionAccount:formal,conflictAcceptance:conflict,readbackAcceptance:readback,actions,registration,wechatBinding},
  diagnostics:()=>({ready,healthDiagnostic,counts:{...counts},...(registration?{registration:true}:{}),retryAfterMs:Math.max(0,retryAt-Date.now()),allowCloudWrites:writable,...(readback?{readbackAcceptance:true,readbackHalted}:{}),...(conflict?{conflictAcceptance:guard?.summary()||null,conflictConfigured:true}:writable&&!formal?{writeAcceptance:guard?.summary()||null}: {})})};
}
module.exports={validateAccountProfile,createAccountConnection};
