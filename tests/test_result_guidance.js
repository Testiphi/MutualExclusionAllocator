'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const home=require('../home_presenter');
const maps=[{big:'甲',small:'甲路'},{big:'乙',small:'乙路'}],candidate=(...cars)=>({groups:cars.map(c=>[c])});
const guide=(assignment,candidates,extra={})=>home.resultGuidance({maps,ownedCars:['a'],candidates,scheme:{assignment},...extra});
test('unselected or incomplete maps and empty zone garage never invite a submission',()=>{
 assert.equal(home.resultGuidance({maps:[null,{big:'甲',small:''}],ownedCars:[]}).kind,'select_maps');
 const g=guide([null,null],[candidate(),candidate()],{ownedCars:[]});assert.equal(g.kind,'select_cars');assert.equal(g.canSubmit,false);
});
test('an all-empty solver assignment retains the exact requested conversational invitation',()=>{
 const g=guide([null,null],[candidate('b'),candidate()]);assert.equal(g.kind,'no_records');assert.equal(g.message,'找不到合适的方案？尝试投稿你自己的成绩来帮助我们提升！');assert.equal(g.canSubmit,true);
});
test('missing matches and mutual exclusion have different guidance; full assignments have none',()=>{
 const missing=guide(['a',null],[candidate('a'),candidate('b')]);assert.equal(missing.kind,'partial_missing');assert.equal(missing.missingMaps[0].big,'乙');
 const overlap=guide(['a',null],[candidate('a'),candidate('a')]);assert.equal(overlap.kind,'conflict');assert.equal(overlap.canSubmit,true);assert.equal(overlap.targetMaps[0].big,'乙');assert.equal(overlap.message,home.resultCopy.no_records);
 assert.equal(guide(['a','b'],[candidate('a'),candidate('b')]),null);
});
test('sparse configured slots do not accidentally count a different result row as filled',()=>{
 const g=guide(['a',null,null,null,null],[candidate()],{maps:[{big:'甲',small:'甲路',originalIndex:4}]});assert.equal(g.kind,'no_records');assert.equal(g.missingMaps[0].originalIndex,4);
});
test('unknown candidate input never diagnoses missing data',()=>{
 assert.equal(guide([null,null],[]),null);assert.equal(guide([null,null],[{},candidate()]),null);
});
test('native local presenter uses the exact reviewed source and matches browser guidance on both servers',()=>{
 const manifest=require('../miniapp/shared/source.json');assert.equal((manifest.localPresenterPreview||manifest.mirror.files['home_presenter.js']).sha256,crypto.createHash('sha256').update(fs.readFileSync(path.resolve(__dirname,'../home_presenter.js'))).digest('hex'));
 const {verifyLocalBundle}=require('../miniapp/adapters/snapshot'),snapshots=verifyLocalBundle(require('../miniapp/generated/local-bundle'));
 const {createWebHomeAdapter}=require('../miniapp/lib/home_presenter_adapter');
 for(const server of ['cn','global']){
  const snapshot=snapshots[server],p=home.createHomePresenter(snapshot),adapter=createWebHomeAdapter(snapshot),t=snapshot.data.tracks[0];
  const draft={schema:1,server,zone:'zone5',tier:'理论',maps:[{big:t.大地图,small:t.小地图},null,null,null,null],cars:[],stars:{},oc:{},routes:{}};
  assert.deepEqual(adapter.guidance(draft),p.present(draft).guidance);assert.equal(adapter.guidance(draft).kind,'select_cars');
  draft.maps=[null,null,null,null,null];assert.equal(adapter.guidance(draft).message,'请先选择地图');
 }
});
test('native submit action preserves current server/map and respects busy/error and unavailable transport',()=>{
 const file=path.resolve(__dirname,'../miniapp/pages/home/home.js');let page;const navigations=[],notices=[],app={};
 vm.runInNewContext(fs.readFileSync(file,'utf8'),{require:require('node:module').createRequire(file),Page:p=>page=p,getApp:()=>app,wx:{navigateTo:p=>navigations.push(p.url),showModal:p=>notices.push(p),showActionSheet:p=>p.success({tapIndex:1})},console,setTimeout,clearTimeout});
 const state={draft:{server:'global',zone:'zone5',tier:'理论'},busy:false,error:''};const scope={data:{resultGuidance:guide([null,null],[candidate(),candidate()])},state,account:{}};
 page.contributeResult.call(scope);assert.match(navigations[0],/server=global/);assert.equal(app.submissionMapTarget.big,'乙');assert.equal(app.submissionMapTarget.server,'global');assert.match(navigations[0],/submissions/);
 state.busy=true;page.contributeResult.call(scope);assert.equal(navigations.length,1);state.busy=false;scope.account=null;page.contributeResult.call(scope);assert.equal(notices.length,1);
});

test('native map-only prefill leaves car/stars/time empty and rejects stale catalogue targets',()=>{
 const file=path.resolve(__dirname,'../miniapp/pages/submissions/submissions.js');let page;
 vm.runInNewContext(fs.readFileSync(file,'utf8'),{require:require('node:module').createRequire(file),Page:p=>page=p,console});
 const scope={data:{server:'global'},catalog:{capabilities:{zones:['五区'],tiers:['理论']},tracks:[{big:'甲',small:'甲路'}]}};
 const target={server:'global',big:'甲',small:'甲路',zone:'五区',tier:'理论',car:'a',stars:6,time:'1',notes:'untrusted'};
 const p=page.mapTarget.call(scope,target);assert.equal(p.car,'');assert.equal(p.stars,null);assert.equal(p.time,'');assert.equal(p.notes,'');
 assert.throws(()=>page.mapTarget.call(scope,{...target,server:'cn'}),/地图或档位/);assert.throws(()=>page.mapTarget.call(scope,{...target,tier:'高手'}),/地图或档位/);
});

for(const changedActor of [false,true])test(`native saved draft ${changedActor?'cannot cross an account change during confirmation':'survives cancelling a map-prefill request'}`,async()=>{
 const file=path.resolve(__dirname,'../miniapp/pages/submissions/submissions.js');let page,actor='before',writes=0;
 const saved={schema:1,server:'cn',entries:[{big:'原图',time:'20'}]},app={submissionMapTarget:{server:'cn',big:'甲',small:'甲路',zone:'五区',tier:'高手'}};
 const wx={getStorageSync:()=>saved,setStorageSync:()=>writes++,showModal:p=>{if(changedActor)actor='after';p.success({confirm:changedActor});}};
 vm.runInNewContext(fs.readFileSync(file,'utf8'),{require:require('node:module').createRequire(file),Page:p=>page=p,getApp:()=>app,wx,console});
 const scope={data:{server:'cn',busy:false,entries:[]},client:{state:()=>({actor:{id:actor}}),call:async()=>({tracks:[{big:'甲',small:'甲路'}],reference_label:'fixture'})},draftKey:()=>actor,rows(){},list:async()=>{},setData(v){Object.assign(this.data,v);},mapTarget:page.mapTarget};
 await page.boot.call(scope);assert.equal(writes,0);assert.equal(saved.entries[0].time,'20');
 if(changedActor){assert.match(scope.data.error,/账号已变化/);assert.equal(scope.data.entries.length,0);}else assert.equal(scope.data.entries[0].big,'原图');
});
