'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),crypto=require('node:crypto');
const core=require('../miniapp/shared/selection_core'),bundle=require('../miniapp/generated/local-bundle');
const {createLocalService}=require('../miniapp/services/local'),{createStorage}=require('../miniapp/adapters/storage'),{createController,blank}=require('../miniapp/lib/controller');
function make(values=new Map(),auto=false) {
 let state;const queue=[];
 const wx={getStorageSync:k=>values.get(k),setStorageSync:(k,v)=>values.set(k,structuredClone(v)),removeStorageSync:k=>values.delete(k)};
 const service=createLocalService(core,bundle),storage=createStorage(wx,'local');
 const c=createController({service,storage,media:{choose:async()=>null},render:s=>{state=s;},autoCompute:auto,schedule:fn=>queue.push(fn)});
 return {c,values,service,storage,queue,get state(){return state;},async flush(){while(queue.length)queue.shift()();await Promise.resolve();await Promise.resolve();}};
}
const saved='racepick.mini.local.draft.v1.cn',working='racepick.mini.local.working.v1.cn';
test('first entry uses website CN expert/all cars and global theoretical; saved empty stays empty',()=>{
 const f=make();assert.equal(f.state.draft.tier,'高手');assert.equal(f.state.draft.cars.length,81);assert.equal(f.state.dirty,false);assert.equal(f.values.size,0);
 f.c.switchServer('global');assert.equal(f.state.draft.tier,'理论');assert.equal(f.state.draft.cars.length,47);
 f.c.setCars(f.state.model.cars.map(c=>c.id),false);f.c.save();f.c.switchServer('cn');f.c.switchServer('global');assert.deepEqual(f.state.draft.cars,[]);
 const values=new Map([[saved,{...blank('cn'),cars:[]}]]);const empty=make(values);assert.deepEqual(empty.state.draft.cars,[]);assert.equal(empty.state.draft.tier,'理论','existing tier must not be reset');
});
test('hide/relaunch stages temporary selection without committing; restore retains maps and discards temporary cars',()=>{
 const f=make();f.c.setCars(f.state.model.cars.map(c=>c.id),false);f.c.setCar('f5',true);f.c.save();
 const before=JSON.stringify(f.values.get(saved));f.c.setCar('c2',true);f.c.hide();assert.equal(JSON.stringify(f.values.get(saved)),before);assert.ok(f.values.has(working));
 const resumed=make(f.values);assert.ok(resumed.state.draft.cars.includes('c2'));assert.equal(resumed.state.dirty,true);
 const map=resumed.state.model.maps[0];resumed.c.setMap(0,map);resumed.c.restore();assert.deepEqual(resumed.state.draft.cars,['f5']);assert.deepEqual(resumed.state.draft.maps[0],map);assert.equal(resumed.state.dirty,false);assert.ok(!f.values.has(working));
});
test('another view saved newer garage: stale save and working draft never overwrite it automatically',()=>{
 const f=make();f.c.setCars(f.state.model.cars.map(c=>c.id),false);f.c.setCar('f5',true);f.c.save();
 const other=make(f.values);other.c.setCar('c2',true);other.c.save();const latest=JSON.stringify(f.values.get(saved));
 f.c.setCar('f5r',true);assert.equal(f.c.save(),false);assert.match(f.state.error,/另一窗口/);assert.equal(JSON.stringify(f.values.get(saved)),latest);f.c.hide();
 const old=JSON.stringify(f.values.get(working)),reopen=make(f.values);assert.match(reopen.state.error,/不一致/);reopen.c.hide();assert.equal(JSON.stringify(f.values.get(working)),old);assert.equal(JSON.stringify(f.values.get(saved)),latest);
});
test('failed temporary-draft removal leaves current selection intact on restore',()=>{
 const f=make();f.c.save();f.c.setCars(f.state.model.cars.map(c=>c.id),false);
 const before=structuredClone(f.state.draft),durable=structuredClone(f.values.get(saved));
 f.storage.clearWorking=()=>{throw Error('storage unavailable');};f.c.restore();
 assert.match(f.state.error,/恢复失败/);assert.deepEqual(f.state.draft,before);assert.deepEqual(f.values.get(saved),durable);
});
test('auto calculation ignores partial slots, publishes latest input and keeps legitimate empty garage leaves',async()=>{
 const f=make(undefined,true);f.c.setMode('zone5','理论');f.c.setCars(f.state.model.cars.map(c=>c.id),false);f.c.setCar('f5',true);
 const river=f.state.model.maps.find(m=>m.small==='河畔漂移');f.c.setMap(0,river);f.c.setMap(1,{big:f.state.model.maps.find(m=>m.big!==river.big).big,small:''});await f.flush();
 assert.equal(f.state.result.schemes[0].rows[0].time,19.9);assert.equal(f.state.result.schemes[0].rows[1].car,null);
 f.c.setCars(['f5'],false);await f.flush();assert.ok(f.state.result.schemes[0].rows.every(r=>r.car===null));
});
test('top-three references use owned candidate order without subtracting other map assignments',async()=>{
 const f=make();f.c.setMode('zone5','理论');f.c.setCars(f.state.model.cars.map(c=>c.id),false);f.c.setCar('f5',true);
 const river=f.state.model.maps.find(m=>m.small==='河畔漂移'),data=JSON.parse(bundle.files['gauntlet_data.json']);
 const second=data.tracks.find(t=>t.大地图!==river.big&&(t.五区.理论||[]).some(e=>e.cars[0].name==='f5'));
 f.c.setMap(0,river);f.c.setMap(1,{big:second.大地图,small:second.小地图});
 assert.equal(f.state.model.topCars[0].items[0].car,'f5');assert.equal(f.state.model.topCars[0].items[0].scoreText,'19.90 秒');assert.equal(f.state.model.topCars[1].items[0].car,'f5');
 await f.c.compute();assert.ok(f.state.result.schemes.every(s=>s.assignment.filter(c=>c==='f5').length===1));
});
test('search aliases/subtitle/sort are generated from fixed website functions, not another hand-maintained ruleset',()=>{
 const manifest=require('../miniapp/shared/source.json'),source=cp.execFileSync('git',['show',manifest.source+':index.html'],{cwd:path.resolve(__dirname,'..')});
 const generated=require('../tools/web_home_adapter.cjs').generateWebHomeAdapter(source.toString('utf8')),actual=fs.readFileSync(path.resolve(__dirname,'../miniapp/shared/web_home.js'),'utf8');assert.equal(actual,generated);
 assert.equal(crypto.createHash('sha256').update(actual).digest('hex'),manifest.derived['web_home.js'].sha256);
 const f=make();assert.ok(f.service.garageView(f.state.draft,'第六元素','','alpha').includes('六子'));assert.ok(f.state.model.subtitle.includes('星级'));
 f.c.switchServer('global');assert.match(f.state.model.subtitle,/国际服/);
});
