'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');

test('homepage account entries open the requested form within the active account policy',()=>{
 const readPage=(relative,runtime,wx)=>{
  const file=path.resolve(__dirname,relative),load=require('node:module').createRequire(file);
  let definition;
  new Function('Page','require','wx',fs.readFileSync(file,'utf8'))(
   page=>definition=page,name=>name==='../../services/runtime'?runtime:load(name),wx);
  return {...definition,data:{...definition.data},setData(fields){Object.assign(this.data,fields);}};
 };
 const routes=[];
 const client={state:()=>({actor:null}),subscribe:()=>()=>{}};
 let registration=true;
 const service={policy:()=>({restricted:true,registration,actions:registration?['login','register']:['login']}),account:()=>client};
 const home=readPage('../miniapp/pages/home/home.js',service,{navigateTo:({url})=>routes.push(url)});
 home.state={draft:{server:'global'}};
 for(const mode of ['register','login']){
  home.navigate({currentTarget:{dataset:{page:'account',mode}}});
  const url=new URL(routes.at(-1),'https://fixture.test');
  assert.equal(url.pathname,'/pages/account/account');
  assert.equal(url.searchParams.get('server'),'global');
  const account=readPage('../miniapp/pages/account/account.js',service);
  account.onLoad(Object.fromEntries(url.searchParams));
  assert.equal(account.data.mode,mode);
 }
 registration=false;
 home.navigate({currentTarget:{dataset:{page:'account',mode:'register'}}});
 assert.equal(routes.length,2);
});
const {createAccountConnection,validateAccountProfile}=require('../miniapp/services/account_connection');
const {binding}=require('../miniapp/services/account_readonly');
const runtime=require('../miniapp/services/runtime');
const profile={enabled:true,origin:binding.origin,allowCloudWrites:false,planId:'mini-account-mirror-unattended-tests'};
function lab(){
 const calls=[],storage=new Map([['old-ocr-record','keep']]);let hook=()=>null;
 const features={profiles:{cn:'account',global:'account'},native_batches:{A:'ready',B:'pending',C:'pending',D:'pending',E:'pending'}};
 const account=()=>({schema_version:1,session_kind:'racepick_account',token_type:'Bearer',token:'rpa1.fixture.account',actor:{id:'fixture-actor',role:'player',verified:true},expires_at:Math.floor(Date.now()/1000)+3000,association:{kind:'session_only',persistent_binding:false,guest_identity:'new-origin-parent'},features});
 function snapshot(server){const names=server==='cn'?['cars.json','gauntlet_data.json']:['cars.global.json','gauntlet_data.global.json','global-data-manifest.json'];return {schema_version:1,server,identity:'new-origin-parent',version:binding.fixed_runtime.snapshot_versions[server],catalog_version:null,capabilities:server==='cn'?{zones:['zone5','zone4'],tiers:['理论','高手','普通','自动'],map_recognition:false}:{zones:['zone5'],tiers:['理论'],map_recognition:false},files:Object.fromEntries(names.map(n=>[n,{text:fs.readFileSync(path.resolve(__dirname,'../../offline-evaluation/mini-account-isolation-20261105-01/candidate-04/snapshot',n),'utf8'),...binding.fixed_runtime.files[n]}]))};}
 const wx={getStorageSync:k=>storage.get(k)||'',setStorageSync:(k,v)=>storage.set(k,v),removeStorageSync:k=>storage.delete(k),getRandomValues:o=>{const b=crypto.randomBytes(o.length);o.success({randomValues:b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength)});},login:o=>{calls.push({kind:'wx.login'});o.success({code:'fixture-code-memory'});},getFileSystemManager:()=>({unlink(){}}),request(o){calls.push({kind:'request',...o});queueMicrotask(()=>{const u=new URL(o.url),r=hook(o,u);if(r?.lost){o.fail({errMsg:'network lost'});return;}let body=r?.body;if(body===undefined){if(u.pathname.endsWith('/health'))body=binding.health;else if(u.pathname==='/api/mini/v1/session')body={schema_version:1,token_type:'Bearer',token:'new-guest-memory',identity:'new-origin-parent',expires_at:Math.floor(Date.now()/1000)+3500};else if(u.pathname.endsWith('/snapshot'))body=snapshot(u.searchParams.get('server'));else if(u.pathname.endsWith('/auth/login')||u.pathname.includes('/operations/'))body=account();else if(u.pathname.endsWith('/profile'))body={server:u.searchParams.get('server'),storage:'account',remote_supported:true,revision:0,profile:null};else body={session_kind:'wechat_guest',actor:null,features};}o.success({statusCode:r?.status||200,data:JSON.stringify(body),header:r?.header||{}});});return {abort(){}};}};
 return {wx,calls,storage,account,setHook:f=>hook=f};
}
const auth=c=>c.auth('login',{email:'fixture@example.test',password:'fixture-private-only'});
test('isolated registration requires its fixed delivery and recovers the original operation without another POST',async()=>{
 const f=lab(),registrationDelivery='1234567890abcdef12345678',p={...profile,registrationDelivery,planId:'mini-account-mirror-registration-fixture'};
 const c=createAccountConnection(f.wx,p),fields={email:'fixture@example.test',password:'fixture-private-only'};
 await assert.rejects(c.client.auth('register',fields),e=>e.code==='ACCOUNT_DELIVERY_MISMATCH');
 let recoveryStatus=404;
 f.setHook((o,u)=>{
  if(u.pathname.endsWith('/health'))return {body:{...binding.health,delivery_id:registrationDelivery,registration:true}};
  if(u.pathname==='/api/mini/account/v1/session')return {body:{session_kind:'wechat_guest',actor:null,features:{...f.account().features,authentication:{isolated_player_registration:true}}}};
  if(u.pathname.endsWith('/auth/register'))return {lost:true};
  if(u.pathname.includes('/operations/'))return recoveryStatus===404?{status:404,body:{code:'OPERATION_NOT_FOUND'}}:{body:{message:'done'}};
 });
 await assert.rejects(c.client.auth('register',fields));
 const {key,action}=c.client.pendingAuth();
 assert.equal(action,'register');
 await assert.rejects(c.client.auth('resend-verification',{email:fields.email}));
 await assert.rejects(c.client.recoverAuth('other-operation-key',action));
 await assert.rejects(c.client.recoverAuth(key,action));
 assert.deepEqual(c.client.pendingAuth(),{key,action});
 recoveryStatus=200;
 assert.equal((await c.client.recoverAuth(key,action)).message,'done');
 assert.equal(c.client.pendingAuth(),null);
 assert.equal(c.diagnostics().counts.register,1);
 assert.equal(c.diagnostics().counts.recovery,2);
 assert.equal(c.diagnostics().counts['resend-verification'],0);
 assert.ok([...f.storage.values()].every(v=>!JSON.stringify(v).includes(fields.password)));
});
test('formal account requires server readiness and performs ordinary saves outside W stage budgets',async()=>{
 const f=lab();let enabled=false,writes=false;
 const {snapshot_versions,files,global_dataset}=binding.fixed_runtime;
 const c=createAccountConnection(f.wx,{enabled:true,mode:'production-a',origin:'https://racepick.cn',planId:'racepick-production-a-v1',allowCloudWrites:true,fixedRuntime:{snapshot_versions,files,global_dataset}});
 f.setHook((o,u)=>{
  if(u.pathname==='/api/health')return {body:{status:'ok',mode:'production',global_profile_schema:1,score_version:snapshot_versions.cn,global_score_version:snapshot_versions.global,...(enabled?{mini_account:{mode:'formal-a',enabled:true,cloud_writes:writes}}:{})}};
  if(o.method==='PUT')return {body:{server:'cn',revision:o.data.revision+1}};
  return null;
 });
 await assert.rejects(auth(c.client));assert.equal(c.diagnostics().counts.login,0);
 enabled=true;await auth(c.client);
 const draft={cars:['f5'],stars:{f5:5}},options={intent:'save',key:'formal-fixture-key-001'};
 await assert.rejects(c.client.saveProfile('cn',draft,0,options),e=>e.notSent===true);
 assert.equal(c.diagnostics().counts.put,0);
 writes=true;assert.deepEqual(await c.client.saveProfile('cn',draft,0,options),{server:'cn',revision:1});
 assert.equal(c.policy.writeAcceptance,false);assert.equal(c.policy.productionAccount,true);assert.equal(c.diagnostics().counts.put,1);
 await assert.rejects(c.client.saveProfile('cn',draft,1,{...options,intent:'import_guest'}));
 assert.equal(c.diagnostics().counts.put,1);
});
test('account connection is lazy; only explicit login establishes new-origin guest and fixed snapshots',async()=>{const f=lab(),c=createAccountConnection(f.wx,profile);assert.equal(f.calls.length,0);await auth(c.client);assert.equal(f.calls.filter(x=>x.kind==='wx.login').length,1);assert.ok(f.calls.filter(x=>x.kind==='request').every(x=>x.url.startsWith(binding.origin+'/')));await c.client.profile('cn');await c.client.profile('global');assert.deepEqual(c.diagnostics().counts,{health:1,guest:1,snapshot:2,login:1,profile:2,session:1,recovery:0});assert.equal(f.storage.size,1);});
test('closed operations fail before network; profile config rejects unsafe origins, writes and secrets',async()=>{const f=lab(),c=createAccountConnection(f.wx,profile);for(const fn of [()=>c.client.auth('register',{}),()=>c.client.saveProfile(),()=>c.client.logout(),()=>c.client.call('/usage/session'),()=>c.client.call('/notifications'),()=>c.client.uploadEvidence()])await assert.rejects(fn());assert.equal(f.calls.length,0);for(const patch of [{allowCloudWrites:true},{origin:'https://mini-test.racepick.cn'},{password:'forbidden'}])assert.throws(()=>validateAccountProfile({...profile,...patch}));});
test('health/snapshot binding failure prevents credential POST and guest is never borrowed from old OCR',async()=>{const f=lab();f.setHook((o,u)=>u.pathname.endsWith('/snapshot')?{body:{}}:null);const c=createAccountConnection(f.wx,profile);await assert.rejects(auth(c.client));assert.equal(c.client.state().actor,null);assert.equal(f.calls.filter(o=>o.url?.endsWith('/auth/login')).length,0);assert.equal(f.storage.get('old-ocr-record'),'keep');});
test('unknown login remains recoverable only by original operation, including after recovery404',async()=>{const f=lab(),c=createAccountConnection(f.wx,profile);f.setHook((o,u)=>u.pathname.endsWith('/auth/login')?{lost:true}:u.pathname.includes('/operations/')?{status:404,body:{code:'OPERATION_NOT_FOUND'}}:null);await assert.rejects(auth(c.client));const pending=c.client.pendingAuth();assert.ok(pending);await assert.rejects(auth(c.client));await assert.rejects(c.client.recoverAuth(pending.key,pending.action));assert.deepEqual(c.client.pendingAuth(),pending);assert.equal(f.calls.filter(o=>o.url?.endsWith('/auth/login')).length,1);});
test('429 blocks further actions during Retry-After without automatically repeating credentials',async()=>{const f=lab(),c=createAccountConnection(f.wx,profile);f.setHook((o,u)=>u.pathname.endsWith('/auth/login')?{status:429,body:{code:'ACCOUNT_RATE_LIMITED'},header:{'Retry-After':'60'}}:null);await assert.rejects(auth(c.client));await assert.rejects(auth(c.client),e=>e.code==='ACCOUNT_RETRY_WAIT');assert.equal(f.calls.filter(o=>o.url?.endsWith('/auth/login')).length,1);});
test('runtime uses separate account origin and isolated drafts, disables metrics, retains same-session store on switch/reentry',async()=>{const f=lab(),c=runtime.mount(f.wx,{kind:'platform',origin:'https://mini-test.racepick.cn'},{api:{identity:'old-ocr-do-not-use'}},profile);assert.equal(f.calls.length,0);assert.equal(runtime.usage(),null);await auth(c);const s=runtime.cloudProfile(f.wx,'global',()=>{});await s.init();s.update({cars:[],stars:{},ocMap:{}});assert.equal(runtime.cloudProfile(f.wx,'global',()=>{}),s);await s.init();assert.equal(f.calls.filter(o=>o.url?.endsWith('/profile?server=global')).length,1);assert.ok([...f.storage.keys()].filter(k=>k!=='old-ocr-record').every(k=>k.startsWith('racepick.mirror.acceptance.'+profile.planId+'.')));await assert.rejects(s.flush(),e=>e.code==='CLOUD_WRITE_DISABLED');assert.equal(f.calls.filter(o=>o.method==='PUT').length,0);const old=s;c.clear();await auth(c);assert.notEqual(runtime.cloudProfile(f.wx,'global'),old);assert.throws(()=>old.update({cars:[],stars:{},ocMap:{}}),e=>e.code==='STALE_ACCOUNT_PROFILE');runtime.mount(f.wx,{kind:'fixture'},{},{enabled:false});});
test('disabled account profile on a platform OCR service never enables its account namespace',()=>{const f=lab();assert.equal(runtime.mount(f.wx,{kind:'platform',origin:'https://mini-test.racepick.cn'},{api:{}},{enabled:false}),null);assert.equal(runtime.usage(),null);assert.equal(f.calls.length,0);});
test('account page unloading discards late UI updates while client operation continues in memory',async()=>{const file=path.resolve(__dirname,'../miniapp/pages/account/account.js');let def;new Function('Page','require',fs.readFileSync(file,'utf8'))(x=>def=x,require('node:module').createRequire(file));let done;const c={auth:()=>new Promise(r=>done=r),state:()=>({actor:{id:'fixture'}}),pendingAuth:()=>null};const page={...def,data:{...def.data,mode:'login',email:'fixture@example.test',password:'fixture-memory'},client:c,setData(v){Object.assign(this.data,v);this.updates=(this.updates||0)+1;}};const work=page.submit();page.onHide();page.onUnload();const before=page.updates;done({});await work;assert.equal(page.updates,before);assert.equal(page.data.password,'');});

test('disposing the independent parent clears its account and old stores locally, never logs out or touches old garage',async()=>{const f=lab(),c=createAccountConnection(f.wx,profile);await auth(c.client);c.dispose();assert.equal(c.client.state().actor,null);await assert.rejects(c.client.profile('cn'),e=>e.code==='ACCOUNT_CONNECTION_DISPOSED');assert.equal(f.storage.get('old-ocr-record'),'keep');assert.equal(f.calls.filter(o=>o.method==='DELETE').length,0);});

test('refresh rejects a different actor, invalid parent association or excessive lifetime and clears stale authority',async()=>{for(const mutate of [v=>{v.actor.id='other-fixture-actor';},v=>{v.association.guest_identity='other-parent';},v=>{v.expires_at=Math.floor(Date.now()/1000)+3620;}]){const f=lab(),c=createAccountConnection(f.wx,profile);await auth(c.client);const v=f.account();mutate(v);f.setHook((o,u)=>u.pathname==='/api/mini/account/v1/session'?{body:v}:null);await assert.rejects(c.client.refresh(),e=>e.code==='ACCOUNT_SESSION_RESPONSE_INVALID');assert.equal(c.client.state().actor,null);assert.equal(f.storage.get('old-ocr-record'),'keep');}});
test('mirror resume reload preserves local draft and detects a newer remote revision instead of silently replacing it',async()=>{const f=lab(),c=runtime.mount(f.wx,{kind:'platform'},{},profile);await auth(c);const s=runtime.cloudProfile(f.wx,'global');await s.init();s.update({cars:['fixture-local'],stars:{},ocMap:{}});f.setHook((o,u)=>u.pathname.endsWith('/profile')?{body:{server:'global',storage:'account',remote_supported:true,revision:2,profile:{cars:[],stars:{},ocMap:{}}}}:null);const resumed=runtime.cloudProfile(f.wx,'global',()=>{},{reload:true});await resumed.init();assert.deepEqual(resumed.snapshot().cars,['fixture-local']);assert.equal(resumed.state().dirty,true);assert.equal(resumed.state().status,'conflict');assert.equal(resumed.remote().revision,2);assert.equal(f.calls.filter(o=>o.method==='PUT').length,0);runtime.mount(f.wx,{kind:'fixture'},{},{enabled:false});});
test('same-session runtime retains unknown save key across server switches and forbids resume reload until original recovery',async()=>{const f=lab(),guest={accountRequest:async()=>f.account()},c=runtime.mount(f.wx,{kind:'fixture',origin:'http://127.0.0.1:8052'},{api:guest});await auth(c);c.saveProfile=async()=>{throw Object.assign(Error('fixture response lost'),{operationKey:'fixture-save-original-key-01'});};const s=runtime.cloudProfile(f.wx,'cn');await s.init();s.update({cars:[],stars:{}});await assert.rejects(s.flush());assert.equal(runtime.cloudProfile(f.wx,'cn'),s);assert.equal(s.pendingKey(),'fixture-save-original-key-01');assert.throws(()=>runtime.cloudProfile(f.wx,'cn',()=>{},{reload:true}),e=>e.code==='PROFILE_RECOVERY_REQUIRED');runtime.cloudProfile(f.wx,'global');assert.equal(runtime.cloudProfile(f.wx,'cn').pendingKey(),'fixture-save-original-key-01');assert.equal(f.calls.filter(o=>o.method==='PUT').length,0);runtime.mount(f.wx,{kind:'fixture'},{},{enabled:false});});
test('mirror main save handler rejects read-only before invoking shared store or sending PUT',()=>{const f=lab();runtime.mount(f.wx,{kind:'platform'},{},profile);const file=path.resolve(__dirname,'../miniapp/pages/home/home.js');let def;new Function('Page','require',fs.readFileSync(file,'utf8'))(x=>def=x,require('node:module').createRequire(file));let flushes=0;const page={...def,account:{state:()=>({actor:{id:'fixture'}})},cloud:{flush:()=>flushes++},data:{},setData(v){Object.assign(this.data,v);}};page.save();assert.equal(flushes,0);assert.ok(page.data.cloudStatus.includes('仅供读取'));assert.equal(f.calls.length,0);runtime.mount(f.wx,{kind:'fixture'},{},{enabled:false});});

test('full mirror fixture login preserves guest garage, keeps drafts per server and reloads once on reentry without PUT',async()=>{const f=lab(),oldWx=global.wx;global.wx=f.wx;const file=path.resolve(__dirname,'../miniapp/pages/home/home.js'),req=require('node:module').createRequire(file),bundle={kind:'local-unfrozen',hashes:binding.fixed_runtime.files,files:Object.fromEntries(Object.keys(binding.fixed_runtime.files).map(n=>[n,fs.readFileSync(path.resolve(__dirname,'../../offline-evaluation/mini-account-isolation-20261105-01/candidate-04/snapshot',n),'utf8')]))};let def;new Function('Page','require',fs.readFileSync(file,'utf8'))(x=>def=x,n=>n==='../../generated/account-config'?profile:n==='../../generated/native-config'?{enabled:false}:n==='../../generated/local-bundle'?bundle:req(n));const make=()=>({...def,data:structuredClone(def.data),setData(v){Object.assign(this.data,v);}});const page=make();let second;try{page.onLoad();const car=page.state.model.cars[0].id;page.controller.setCars([car],true);const guestCars=[...page.state.draft.cars];await auth(runtime.account());page.homeVisible=true;await page.syncAccount();assert.deepEqual(page.state.draft.cars,[]);assert.equal(page.data.cloudEmpty,true);const saved=require('../miniapp/adapters/storage').createStorage(runtime.storageWx(f.wx),'local');assert.deepEqual(saved.readWorking('cn',saved.read('cn')).cars,guestCars);page.controller.setCar(car,true);assert.equal(page.cloud.state().dirty,true);await page.switchServer({currentTarget:{dataset:{server:'global'}}});assert.deepEqual(page.state.draft.cars,[]);await page.switchServer({currentTarget:{dataset:{server:'cn'}}});assert.ok(page.state.draft.cars.includes(car));await page.save();assert.ok(page.data.cloudStatus.includes('仅供读取'));page.onHide();page.onUnload();f.setHook((o,u)=>u.pathname==='/api/mini/account/v1/session'&&o.header.Authorization?.startsWith('Bearer rpa1.')?{body:f.account()}:null);second=make();second.onLoad();const reads=f.calls.filter(o=>o.url?.endsWith('/profile?server=cn')).length;await second.onShow();assert.equal(f.calls.filter(o=>o.url?.endsWith('/profile?server=cn')).length-reads,1);assert.ok(second.state.draft.cars.includes(car));assert.equal(f.calls.filter(o=>o.method==='PUT').length,0);assert.equal(f.storage.get('old-ocr-record'),'keep');}finally{if(!page.unloaded)page.onUnload();if(second)second.onUnload();runtime.mount(f.wx,{kind:'fixture'},{},{enabled:false});global.wx=oldWx;}});

test('account instrumentation and scoped storage do not overwrite host wx accessors',async()=>{
 const f=lab(),originals={};
 for(const name of ['request','getStorageSync','setStorageSync','removeStorageSync']){
  let implementation=originals[name]=f.wx[name];
  Object.defineProperty(f.wx,name,{get:()=>implementation,set:value=>{implementation=value;}});
 }
 const c=createAccountConnection(f.wx,profile);
 const scoped=runtime.storageWx(f.wx,'accessor-regression');
 scoped.setStorageSync('garage','draft');
 assert.equal(scoped.getStorageSync('garage'),'draft');
 assert.equal(f.wx.getStorageSync('garage'),'');
 scoped.removeStorageSync('garage');
 for(const [name,implementation] of Object.entries(originals))assert.equal(f.wx[name],implementation);
 await auth(c.client);
 assert.equal(c.diagnostics().counts.health,1);
 assert.equal(f.calls.filter(call=>call.url?.endsWith('/health')).length,1);
});

test('formal account server switch rereads another device save before editing',async()=>{
 const f=lab(),oldWx=global.wx;global.wx=f.wx;
 const fixedRuntime=Object.fromEntries(['snapshot_versions','files','global_dataset'].map(k=>[k,binding.fixed_runtime[k]]));
 const config={enabled:true,mode:'production-a',origin:'https://racepick.cn',planId:'racepick-production-a-v1',allowCloudWrites:true,fixedRuntime};
 const bundle={kind:'local-unfrozen',hashes:fixedRuntime.files,files:Object.fromEntries(Object.keys(fixedRuntime.files).map(n=>[n,fs.readFileSync(path.resolve(__dirname,'../../offline-evaluation/mini-account-isolation-20261105-01/candidate-04/snapshot',n),'utf8')]))};
 const file=path.resolve(__dirname,'../miniapp/pages/home/home.js'),req=require('node:module').createRequire(file);
 let def;
 new Function('Page','require',fs.readFileSync(file,'utf8'))(x=>def=x,n=>n==='../../generated/account-config'?config:n==='../../generated/native-config'?{enabled:false}:n==='../../generated/local-bundle'?bundle:req(n));
 const page={...def,data:structuredClone(def.data),setData(v){Object.assign(this.data,v);}};
 let globalSaved=false;
 f.setHook((o,u)=>{
  if(u.pathname==='/api/health')return {body:{status:'ok',mode:'production',global_profile_schema:1,score_version:fixedRuntime.snapshot_versions.cn,global_score_version:fixedRuntime.snapshot_versions.global,mini_account:{mode:'formal-a',enabled:true,cloud_writes:false}}};
  if(globalSaved&&u.pathname.endsWith('/profile')&&u.searchParams.get('server')==='global')return {body:{server:'global',storage:'account',remote_supported:true,revision:1,profile:{cars:['ssc'],stars:{},ocMap:{}}}};
  return null;
 });
 const select=server=>page.switchServer({currentTarget:{dataset:{server}}});
 try{
  page.onLoad();await auth(runtime.account());await page.syncAccount();
  await select('global');assert.equal(page.cloud.remote().revision,0);
  await select('cn');globalSaved=true;
  await select('global');
  assert.equal(page.cloud.remote().revision,1);
  assert.deepEqual(page.state.draft.cars,['ssc']);
  assert.equal(page.data.cloudLoaded,true);
  assert.equal(f.calls.filter(o=>o.url?.endsWith('/profile?server=global')).length,2);
  assert.equal(f.calls.filter(o=>o.method==='PUT').length,0);
 }finally{page.onUnload();runtime.mount(f.wx,{kind:'fixture'},{},{enabled:false});global.wx=oldWx;}
});

test('platform login accepts small device clock skew only within the parent expiry',async()=>{
 const f=lab(),issued=Math.floor(Date.now()/1000)+5;
 const account={...f.account(),authenticated_at:issued,expires_at:issued+3600};
 f.setHook((o,u)=>{
  if(u.pathname==='/api/mini/v1/session')return {body:{schema_version:1,token_type:'Bearer',token:'fixture-parent',identity:'new-origin-parent',expires_at:issued+3600}};
  if(u.pathname.endsWith('/auth/login'))return {body:account};
  return null;
 });
 const c=createAccountConnection(f.wx,profile);
 await auth(c.client);
 assert.equal(c.client.state().actor.role,'player');
 assert.equal(c.client.pendingAuth(),null);
 assert.equal(c.diagnostics().counts.login,1);
 assert.equal(c.diagnostics().counts.recovery,0);
});

test('binding acceptance connects only to its fixed isolated delivery and leaves profile writes closed',async()=>{
 const f=lab(),wechatBindingDelivery='1234567890abcdef12345678';
 const p={...profile,wechatBindingDelivery,planId:'mini-account-mirror-wechat-binding-fixture'};
 const c=createAccountConnection(f.wx,p);
 await assert.rejects(auth(c.client),e=>e.code==='ACCOUNT_DELIVERY_MISMATCH');
 assert.equal(f.calls.filter(x=>x.kind==='wx.login').length,0);
 f.setHook((request,url)=>{
  if(url.pathname.endsWith('/health'))return {body:{...binding.health,delivery_id:wechatBindingDelivery,wechat_binding:true}};
  if(url.pathname.endsWith('/auth/login')){const session=f.account();session.features.wechat_binding_v1={enabled:true,bound:false};return {body:session};}
  if(url.pathname.endsWith('/auth/wechat-bind'))return {body:{actor_id:'fixture-actor',bound:true}};
 });
 await auth(c.client);
 assert.deepEqual(c.client.wechatBinding(),{bound:false});
 assert.deepEqual(await c.client.changeWechatBinding('wechat-bind','fixture-private-only'),{bound:true});
 await assert.rejects(c.client.saveProfile('cn',{},0),e=>e.code==='CLOUD_WRITE_DISABLED');
 const change=f.calls.find(x=>x.url?.endsWith('/auth/wechat-bind'));
 assert.equal(change.header['X-Account-ID'],'fixture-actor');
 assert.equal(f.calls.filter(x=>x.kind==='wx.login').length,2);
 assert.equal(f.calls.filter(x=>x.method==='PUT').length,0);
 await c.client.logout();
 assert.equal(c.client.wechatBinding(),null);
});
