'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const cp = require('node:child_process');
const { createController, blank } = require('../miniapp/lib/controller');
const { createMock } = require('../miniapp/services/mock');
const { createStorage } = require('../miniapp/adapters/storage');
const { createMedia } = require('../miniapp/adapters/media');
const { createTransport } = require('../miniapp/adapters/transport');
const { sha256, utf8 } = require('../miniapp/adapters/hash');
const { requestId } = require('../miniapp/adapters/id');
const { createSession } = require('../miniapp/adapters/session');
function deferred() { let resolve, reject; const promise = new Promise((a,b) => { resolve=a; reject=b; }); return { promise, resolve, reject }; }
function fixture(overrides = {}) {
  const values = new Map(); let state; let full = false;
  const wx = { getStorageSync: key => values.get(key), setStorageSync(key, value) { if (full) throw Error('quota'); values.set(key, structuredClone(value)); } };
  const service = Object.assign(createMock(), overrides);
  const c = createController({ service, storage: createStorage(wx, 'mock'), media: { choose: async () => ({path:'tmp/image',size:32}) }, render: x => { state = x; } });
  return { c, wx, service, values, get state() { return state; }, setFull: value => { full = value; } };
}
function select(f) { f.c.setMap(0, f.state.model.maps[0]); f.c.setCar(f.state.model.cars[0].id, true); }
test('five slots, partial big map survives until small selected; duplicate big is refused without clearing garage', () => {
  const f=fixture(); select(f); const map=f.state.model.maps[1];
  f.c.setMap(1,{big:map.big,small:''}); assert.equal(f.state.draft.maps[1].big,map.big);
  f.c.setMap(1,map); f.c.setMap(2,map); assert.equal(f.state.draft.maps[2],null);
  assert.match(f.state.error,/重复/); assert.equal(f.state.draft.cars.length,1);
});
test('CN/global persist independently; no browser or account state is read', () => {
  const f=fixture(); select(f); f.c.save(); f.c.switchServer('global');
  assert.equal(f.state.draft.cars.length,0); assert.deepEqual(f.state.model.zones,['zone5']);
  assert.deepEqual(f.state.model.tiers,['理论']); f.c.setCar('联调车B',true); f.c.setOc('联调车B',true);
  f.c.switchServer('cn'); assert.deepEqual(f.state.draft.cars,['联调车A']);
  f.c.switchServer('global'); assert.equal(f.state.draft.oc['联调车B'],true);
  assert.equal(f.values.size,2); for (const key of f.values.keys()) assert.match(key,/^racepick\.mini\.mock\.draft\.v1\./);
});
test('quota failure refuses server switch and leaves old durable draft intact', () => {
  const f=fixture(); select(f); f.c.save(); const old=JSON.stringify([...f.values]);
  f.c.setCar('联调车B',true); f.setFull(true); f.c.switchServer('global');
  assert.equal(f.state.draft.server,'cn'); assert.equal(JSON.stringify([...f.values]),old);
  assert.equal(f.state.draft.cars.length,2); assert.equal(f.state.dirty,true); assert.match(f.state.error,/保存失败/);
});
test('corrupt and unsupported drafts cannot be overwritten by explicit save or background autosave', () => {
  for (const value of [{schema:99}, {...blank('cn'),maps:[null]}, {...blank('cn'),oc:{a:'true'}}, {...blank('cn'),stars:{a:1.5}}]) {
    const f=fixture(); f.values.set('racepick.mini.mock.draft.v1.cn',value); f.c.restore(); select(f);
    f.c.save(); f.c.hide(); assert.deepEqual(f.values.get('racepick.mini.mock.draft.v1.cn'),value);
    assert.equal(f.state.storageBlocked,true);
  }
});
test('unknown restored cars and maps are filtered by supplied model without adding owned vehicles', () => {
  const f=fixture(); const d=blank('cn'); d.cars=['removed']; d.maps[0]={big:'removed',small:'removed'};
  f.values.set('racepick.mini.mock.draft.v1.cn',d); f.c.restore();
  assert.deepEqual(f.state.draft.cars,[]); assert.equal(f.state.draft.maps[0],null); assert.equal(f.state.dirty,true);
});
test('late calculation cannot overwrite edited input or a different server', async () => {
  const d=deferred(), f=fixture({calculate:()=>d.promise}); select(f); const p=f.c.compute();
  f.c.setCar('联调车B',true); d.resolve({schemes:[]}); await p; assert.equal(f.state.result,null);
  assert.equal(f.state.busy,false);
});
test('repeated generate only invokes one pending computation; errors retain input', async () => {
  const d=deferred(); let calls=0; const f=fixture({calculate:()=>{calls++;return d.promise;}}); select(f);
  const p=f.c.compute(); await f.c.compute(); assert.equal(calls,1); d.reject(Error('offline')); await p;
  assert.match(f.state.error,/offline/); assert.equal(f.state.draft.cars.length,1); assert.equal(f.state.busy,false);
});
test('background cancels publication and saves dirty draft; foreground refreshes without uploading', async () => {
  const d=deferred(); let resumed=0; const f=fixture({calculate:()=>d.promise,resume:async()=>{resumed++;}}); select(f);
  const p=f.c.compute(); f.c.hide(); d.resolve({schemes:[]}); await p; await f.c.show();
  assert.equal(f.state.result,null); assert.equal(f.state.dirty,false); assert.equal(resumed,1);
});
test('OCR keeps manual maps until explicit confirmation; cancellation preserves original choices', async () => {
  const f=fixture(); select(f); const before=structuredClone(f.state.draft.maps);
  await f.c.chooseImage(); await f.c.recognize(); assert.deepEqual(f.state.draft.maps,before);
  assert.equal(f.state.pending.length,5); f.c.cancelRecognition(); assert.deepEqual(f.state.draft.maps,before);
  await f.c.chooseImage(); await f.c.recognize(); f.c.applyRecognition();
  assert.equal(f.state.draft.maps.filter(Boolean).length,5); assert.equal(f.state.pending,null);
});
test('OCR partial/duplicate/unknown slots cannot be confirmed', async () => {
  const f=fixture(); await f.c.chooseImage(); await f.c.recognize(); f.c.correctSlot(1,null); f.c.applyRecognition();
  assert.equal(f.state.draft.maps[0],null); f.c.correctSlot(1,f.state.pending[0]); f.c.applyRecognition();
  assert.equal(f.state.draft.maps[0],null); f.c.correctSlot(1,{big:'unknown',small:'unknown'}); f.c.applyRecognition();
  assert.equal(f.state.draft.maps[0],null);
});
test('OCR stale server/version and late callbacks fail closed', async () => {
  const f=fixture({recognize:async()=>({server:'cn',version:'old',slots:[]})});
  await f.c.chooseImage(); await f.c.recognize(); assert.equal(f.state.pending,null); assert.match(f.state.error,/目录/);
  const d=deferred(), g=fixture({recognize:()=>d.promise}); await g.c.chooseImage(); const p=g.c.recognize();
  g.c.switchServer('global'); d.resolve({server:'cn',version:'mock-v1-cn',slots:[]}); await p;
  assert.equal(g.state.pending,null); assert.equal(g.state.draft.server,'global');
});
test('international recognition is unavailable and media adapter only opens album', async () => {
  const f=fixture(); f.c.switchServer('global'); await f.c.chooseImage(); assert.equal(f.state.image,null);
  let args; const p=createMedia({chooseMedia:x=>{args=x;x.success({tempFiles:[{tempFilePath:'tmp/a',size:8}]});}}).choose();
  assert.deepEqual(args.sourceType,['album']); assert.deepEqual(args.mediaType,['image']); assert.equal((await p).path,'tmp/a');
  await assert.rejects(createMedia({chooseMedia:x=>x.success({tempFiles:[{tempFilePath:'x',size:8388609}]})}).choose(),/8MiB/);
  assert.equal(await createMedia({chooseMedia:x=>x.fail({errMsg:'chooseMedia:fail cancel'})}).choose(),null);
});
test('album return survives expected background/foreground transition; later edits cancel old selection', async () => {
  const d=deferred(); let state;
  const c=createController({service:createMock(),storage:{read:()=>null,write(){}},media:{choose:()=>d.promise},render:s=>{state=s;}});
  const p=c.chooseImage(); c.hide(); await c.show(); d.resolve({path:'tmp/selected',size:32}); await p;
  assert.equal(state.image,'tmp/selected');
  const e=deferred(); const g=createController({service:createMock(),storage:{read:()=>null,write(){}},media:{choose:()=>e.promise},render:s=>{state=s;}});
  const q=g.chooseImage(); g.setCar('联调车A',true); e.resolve({path:'tmp/stale',size:32}); await q;
  assert.equal(state.image,null);
});
test('SHA-256 agrees with Node for standard vectors, Chinese/emoji, invalid surrogate, binary and offset views', () => {
  for (const str of ['', 'abc', '中文\r\n地图🏎️', '\ud800X\udfff', 'a'.repeat(1000000)]) {
    assert.deepEqual(Buffer.from(utf8(str)),Buffer.from(str));
    assert.equal(sha256(utf8(str)),crypto.createHash('sha256').update(str).digest('hex'));
  }
  const data=crypto.randomBytes(8193).subarray(3,8191);
  assert.equal(sha256(data),crypto.createHash('sha256').update(data).digest('hex'));
  assert.throws(()=>sha256('{}'),/原始字节/);
});
test('raw data hash detects whitespace changes; all received runtime bytes match receipt', t => {
  const source=path.resolve(__dirname,'../../offline-evaluation/miniprogram-v1-20261102-01');
  if (!fs.existsSync(source)) { t.skip('external local receipt not present'); return; }
  const receipt=JSON.parse(fs.readFileSync(path.join(source,'runtime-source.json'),'utf8'));
  for (const [file,meta] of Object.entries(receipt.runtime)) {
    const bytes=fs.readFileSync(path.join(source,'runtime',file));
    assert.equal(bytes.length,meta.bytes); assert.equal(sha256(bytes),meta.sha256);
    const serialized = utf8(JSON.stringify(JSON.parse(bytes.toString('utf8'))));
    assert.notEqual(sha256(serialized),meta.sha256);
  }
});
test('request IDs require secure random bytes and never silently use Math.random', async () => {
  assert.equal(await requestId({getRandomValues:o=>o.success({randomValues:new Uint8Array(16).fill(17).buffer})}),'11'.repeat(16));
  await assert.rejects(requestId({}),/随机数/);
});
test('visitor session exchange is single-flight, memory-only and renews before expiry', async () => {
  let time=1000, logins=0, exchanges=0, token=null;
  const wx={getRandomValues:o=>o.success({randomValues:new Uint8Array(16).buffer}),login:o=>{logins++;o.success({code:'wx-temporary'});}};
  const session=createSession(wx,{now:()=>time,setToken:x=>{token=x;},clearToken:()=>{token=null;},exchange:async input=>{
    exchanges++; assert.equal(input.code,'wx-temporary'); assert.equal(input.request_key.length,32);
    return {token:'guest-only',expiresAt:time+60000};
  }});
  await Promise.all([session.ensure(),session.ensure()]); assert.equal(exchanges,1); assert.equal(logins,1);
  await session.ensure(); assert.equal(logins,1); time+=31000; await session.ensure(); assert.equal(logins,2);
  session.invalidate(); assert.equal(token,null);
});
test('invalidated visitor exchange cannot install a late token; expired response fails closed', async () => {
  const d=deferred(); let token=null;
  const wx={getRandomValues:o=>o.success({randomValues:new Uint8Array(16).buffer}),login:o=>o.success({code:'temp'})};
  const session=createSession(wx,{now:()=>1000,setToken:x=>{token=x;},clearToken:()=>{token=null;},exchange:()=>d.promise});
  const p=session.ensure(); await new Promise(resolve=>setImmediate(resolve)); session.invalidate();
  d.resolve({token:'late',expiresAt:100000}); await assert.rejects(p,/失效/); assert.equal(token,null);
  const bad=createSession(wx,{now:()=>1000,setToken(){throw Error('must not install');},clearToken(){},exchange:async()=>({token:'bad',expiresAt:2000})});
  await assert.rejects(bad.ensure(),/过期/);
});
test('transport is off by default, forbids website routes and cookie/session overrides', async () => {
  assert.throws(()=>createTransport({},{}).request('/api/mini/v1/session'),/尚未配置/);
  const client=createTransport({}, {enabled:true,baseURL:'https://local.invalid'});
  assert.throws(()=>client.request('/api/scores/snapshot'),/非原生/);
  assert.throws(()=>client.request('/api/mini/v1/../../scores/snapshot'),/非原生/);
  assert.throws(()=>client.request('/api/mini/v1/%2e%2e/snapshot'),/非原生/);
  assert.throws(()=>client.request('/api/mini/v1/session',{header:{Cookie:'x'}}),/覆盖/);
  await assert.rejects(client.upload('/api/mini/v1/jobs',{header:{'Content-Type':'x'}}).promise,/微信生成/);
});
test('transport keeps token in memory, sends raw response bytes, clears 401, does not retry POST', async () => {
  const calls=[]; let aborted=0;
  const wx={request:o=>{calls.push(o);return {abort(){aborted++;}};}};
  const c=createTransport(wx,{enabled:true,baseURL:'http://127.0.0.1:8044',allowLocal:true}); c.setToken('secret');
  const p=c.request('/api/mini/v1/session',{method:'POST',data:{code:'temporary'}});
  assert.equal(calls[0].header.Authorization,'Bearer secret'); assert.equal(calls[0].responseType,'arraybuffer');
  calls[0].success({statusCode:401}); await assert.rejects(p.promise,/401/); assert.equal(calls.length,1);
  const q=c.request('/api/mini/v1/snapshot?server=cn'); assert.equal(calls[1].header.Authorization,undefined);
  q.abort(); assert.equal(aborted,1); calls[1].fail(); await assert.rejects(q.promise,/未完成/);
});
test('generated shared modules remain identical to owning sources', () => {
  const manifest=require('../miniapp/shared/source.json');
  for(const [file,meta] of Object.entries(manifest.files)) {
    const source=cp.execFileSync('git',['show',manifest.source+':'+file],{cwd:path.resolve(__dirname,'..')});
    assert.deepEqual(fs.readFileSync(path.resolve(__dirname,'../miniapp/shared',file)),source);
    assert.equal(sha256(source),meta.sha256);
  }
});
test('actual native page JS handlers drive five manual maps and garage, then render mock results', async () => {
  const file=path.resolve(__dirname,'../miniapp/pages/home/home.js'); let config;
  const values=new Map(); const wx={getStorageSync:k=>values.get(k),setStorageSync:(k,v)=>values.set(k,v)};
  vm.runInNewContext(fs.readFileSync(file,'utf8'),{Page:x=>{config=x;},wx,
    require:x=>x==='../../generated/native-config'?{enabled:false}:x==='../../generated/local-bundle'?null:require(path.resolve(path.dirname(file),x))},{filename:file});
  const page={...config,data:structuredClone(config.data),setData(x){Object.assign(this.data,x);}}; page.onLoad();
  const event=(index,field,value)=>({currentTarget:{dataset:{index,field}},detail:{value}});
  for(let i=0;i<5;i++){page.selectMap(event(i,'big',i+1));page.selectMap(event(i,'small',1));}
  page.toggleCar({currentTarget:{dataset:{id:'联调车A'}}}); await page.controller.compute();
  assert.equal(page.data.rows.filter(x=>x.small).length,5); assert.equal(page.data.schemes.length,1);
  assert.equal(page.data.schemes[0].totalText,'—'); assert.equal(page.data.mode,'mock');
  page.onUnload();
});
