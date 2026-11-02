'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const cp = require('node:child_process');
const vm = require('node:vm');
const core = require('../miniapp/shared/selection_core');
const source = require('../miniapp/shared/source.json').source;
const bundle = require('../miniapp/generated/local-bundle');
const { verifyLocalBundle } = require('../miniapp/adapters/snapshot');
const { createLocalService } = require('../miniapp/services/local');
const { createController } = require('../miniapp/lib/controller');
const { createStorage } = require('../miniapp/adapters/storage');
const { sha256,utf8 } = require('../miniapp/adapters/hash');
if (!bundle) throw Error('Run prepare_miniapp.cjs with --data-receipt for local integration tests');
const snapshots = verifyLocalBundle(bundle);
function readBlob(file) { return cp.execFileSync('git',['show',source+':'+file],{cwd:path.resolve(__dirname,'..'),encoding:'utf8'}); }
// Execute the owning branch's exact tests and frozen web oracle, against the
// SHA-verified 4504/693 bundle and the generated modules from that same commit.
const fixture = {exports:{}};
new Function('module',readBlob('tests/fixtures/selection_page_reference.cjs'))(fixture);
new Function('require','__dirname',readBlob('tests/test_selection_core.js'))(name=>{
  if(name==='../selection_core')return core;
  if(['../allocator','../race_scores','../app_state'].includes(name))return require('../miniapp/shared/'+name.slice(3));
  if(name==='./fixtures/selection_page_reference.cjs')return fixture.exports;
  if(name==='node:fs')return {...fs,readFileSync(file,encoding){const key=path.basename(file);if(bundle.files[key])return encoding?bundle.files[key]:Buffer.from(bundle.files[key]);return fs.readFileSync(file,encoding);}};
  return require(name);
},__dirname);
test('received snapshot byte binding rejects corruption, cross-file metadata and unknown files',()=>{
  assert.equal(snapshots.cn.data.tracks.length,83); assert.equal(snapshots.global.data.tracks.length,44);
  for(const mutate of [b=>{b.files['cars.json']+=' ';},b=>{delete b.files['cars.global.json'];},b=>{b.files['extra.json']='{}';}]) {
    const b=structuredClone(bundle);mutate(b);assert.throws(()=>verifyLocalBundle(b));
  }
  const b=structuredClone(bundle), d=JSON.parse(b.files['cars.global.json']); d._meta.dataset_version='wrong';
  b.files['cars.global.json']=JSON.stringify(d); const raw=utf8(b.files['cars.global.json']);b.hashes['cars.global.json']={bytes:raw.length,sha256:sha256(raw)};
  assert.throws(()=>verifyLocalBundle(b),/原子版本/);
});
function controller() {
  let state; const values=new Map(),wx={getStorageSync:k=>values.get(k),setStorageSync:(k,v)=>values.set(k,structuredClone(v))};
  const service=createLocalService(core,bundle);
  const c=createController({service,storage:createStorage(wx,'local'),media:{choose:async()=>null},render:x=>{state=x;}});
  return {c,values,service,get state(){return state;}};
}
test('changing zones retains all owned cars and saved higher stars while model clamps effective options',()=>{
  const f=controller(), all=f.state.model.cars;
  const four=f.service.model({...f.state.draft,zone:'zone4'}).cars;
  const onlyFive=all.find(x=>!four.some(c=>c.id===x.id)); assert.ok(onlyFive);
  const clamped=all.find(x=>four.some(c=>c.id===x.id&&Math.max(...c.stars)<Math.max(...x.stars)));assert.ok(clamped);
  const stars=Math.max(...clamped.stars); f.c.setCar(onlyFive.id,true);f.c.setCar(clamped.id,true);f.c.setStars(clamped.id,stars);
  f.c.setMode('zone4','高手'); assert.ok(f.state.draft.cars.includes(onlyFive.id)); assert.equal(f.state.draft.stars[clamped.id],stars);
  f.c.save(); f.c.restore(); assert.ok(f.state.draft.cars.includes(onlyFive.id));
  f.c.setMode('zone5','高手'); assert.equal(f.state.draft.stars[clamped.id],stars);
});
test('real shared calculation changes river F5 result for off/all/specific route without changing garage',async()=>{
  const f=controller(),river=f.state.model.maps.find(x=>x.small==='河畔漂移');assert.ok(river);
  f.c.setMap(0,river); f.c.setCar('f5',true);const key=river.big+'/'+river.small;
  f.c.setRoute(key,'all');await f.c.compute();assert.equal(f.state.result.schemes[0].rows[0].time,19.9);
  f.c.setRoute(key,'稳定跳图');await f.c.compute();assert.equal(f.state.result.schemes[0].rows[0].time,23.2);
  f.c.setRoute(key,'off');await f.c.compute();assert.equal(f.state.result.schemes[0].rows[0].time,23.79);
  assert.deepEqual(f.state.draft.cars,['f5']);assert.equal(f.state.result.schemes[0].total,null);
  f.c.setMode('zone5','高手');assert.match(f.state.model.routes[0].label,/稳定跳图/);
});
test('local recognition fails explicitly; it never serves mock OCR for real maps',async()=>{
  const service=createLocalService(core,bundle);assert.equal(service.mode,'local');
  await assert.rejects(service.recognize(),/尚未接入/);
});
test('outdated saved maps and modes recover before shared core validation without overwriting saved data',()=>{
  const f=controller(),d=structuredClone(f.state.draft);
  d.zone='old-zone';d.tier='old-tier';d.maps[0]={big:'removed',small:'removed'};
  f.values.set('racepick.mini.local.draft.v1.cn',d);f.c.restore();
  assert.equal(f.state.draft.zone,'zone5');assert.equal(f.state.draft.tier,'理论');assert.equal(f.state.draft.maps[0],null);
  assert.equal(f.state.dirty,true);assert.equal(f.values.get('racepick.mini.local.draft.v1.cn').zone,'old-zone');
});
test('actual page handlers use real maps, retain route selection and render shared result',async()=>{
  const file=path.resolve(__dirname,'../miniapp/pages/home/home.js');let config;
  const values=new Map(),wx={getStorageSync:k=>values.get(k),setStorageSync:(k,v)=>values.set(k,v)};
  vm.runInNewContext(fs.readFileSync(file,'utf8'),{Page:x=>{config=x;},wx,require:x=>x==='../../generated/native-config'?{enabled:false}:require(path.resolve(path.dirname(file),x))});
  const p={...config,data:structuredClone(config.data),setData(x){Object.assign(this.data,x);}};p.onLoad();
  const river=p.state.model.maps.find(x=>x.small==='河畔漂移');p.controller.setMap(0,river);p.controller.setCar('f5',true);
  const route=p.data.routes[0],key=route.key;p.selectRoute({currentTarget:{dataset:{key}},detail:{value:route.options.indexOf('稳定跳图')}});
  p.toggleRoute({currentTarget:{dataset:{key}}});assert.equal(p.state.draft.routes[key],'off');
  p.toggleRoute({currentTarget:{dataset:{key}}});assert.equal(p.state.draft.routes[key],'稳定跳图');
  await p.controller.compute();assert.equal(p.data.mode,'local');assert.equal(p.data.schemes[0].rows[0].timeText,'23.200秒');
  p.onUnload();
});
test('website-style scheme selection keeps shared order and resets on input edits; mode and OC buttons work',async()=>{
  const file=path.resolve(__dirname,'../miniapp/pages/home/home.js');let config;
  const values=new Map(),wx={getStorageSync:k=>values.get(k),setStorageSync:(k,v)=>values.set(k,v)};
  vm.runInNewContext(fs.readFileSync(file,'utf8'),{Page:x=>{config=x;},wx,require:x=>x==='../../generated/native-config'?{enabled:false}:require(path.resolve(path.dirname(file),x))});
  const p={...config,data:structuredClone(config.data),setData(x){Object.assign(this.data,x);}};p.onLoad();
  const selected=[];
  for(const map of p.state.model.maps)if(selected.length<5&&!selected.some(x=>x.big===map.big))selected.push(map);
  selected.forEach((map,i)=>p.controller.setMap(i,map));p.controller.setCar('f5',true);await p.controller.compute();
  assert.ok(p.data.schemes.length>1);const before=JSON.stringify(p.data.schemes);
  p.selectScheme({detail:{value:1}});assert.equal(p.data.activeScheme.index,1);assert.equal(JSON.stringify(p.data.schemes),before);
  p.save();assert.equal(p.data.activeScheme.index,1);
  p.controller.setStars('f5',5);assert.equal(p.data.activeScheme,null);assert.equal(p.data.schemeIndex,0);
  await p.controller.compute();assert.equal(p.data.activeScheme.index,0);
  p.selectTier({currentTarget:{dataset:{index:1}},detail:{}});assert.equal(p.state.draft.tier,'高手');
  p.selectZone({currentTarget:{dataset:{index:1}},detail:{}});assert.equal(p.state.draft.zone,'zone4');
  p.controller.switchServer('global');const oc=p.state.model.cars.find(c=>c.ocAllowed);assert.ok(oc);
  const event={currentTarget:{dataset:{id:oc.id}}};p.toggleOc(event);assert.equal(p.state.draft.oc[oc.id],true);
  p.toggleOc(event);assert.equal(p.state.draft.oc[oc.id],false);p.onUnload();
});
test('bulk garage actions use visible select/all-zone clear, restore retains maps and effective stars come from core',async()=>{
 const file=path.resolve(__dirname,'../miniapp/pages/home/home.js');let config;
 const values=new Map(),wx={getStorageSync:k=>values.get(k),setStorageSync:(k,v)=>values.set(k,v)};
 vm.runInNewContext(fs.readFileSync(file,'utf8'),{Page:x=>{config=x;},wx,require:x=>x==='../../generated/native-config'?{enabled:false}:require(path.resolve(path.dirname(file),x))});
 const p={...config,data:structuredClone(config.data),setData(x){Object.assign(this.data,x);}};p.onLoad();
 p.search({detail:{value:'f5'}});p.selectAll();assert.deepEqual([...p.state.draft.cars].sort(),['f5','f5r']);p.save();
 p.search({detail:{value:'f5r'}});p.clearAll();assert.equal(p.state.draft.cars.length,0);
 const map=p.state.model.maps[3];p.controller.setMap(0,map);p.restore();assert.equal(p.state.draft.maps[0].small,map.small);assert.ok(p.state.draft.cars.includes('f5'));
 p.controller.setStars('f5',6);p.selectZone({currentTarget:{dataset:{index:1}},detail:{}});p.search({detail:{value:'f5'}});
 const car=p.data.cars.find(c=>c.id==='f5');assert.equal(car.stars[car.starIndex],3);assert.equal(p.state.draft.stars.f5,6);
 p.onUnload();
});
