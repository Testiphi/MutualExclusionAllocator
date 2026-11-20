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
 const manifest=require('../miniapp/shared/source.json'),checkout=fs.readFileSync(path.resolve(__dirname,'../home_presenter.js'));
 const reviewed=manifest.localPresenterPreview?checkout:require('node:child_process').execFileSync('git',['show',manifest.mirror.source+':home_presenter.js'],{cwd:path.resolve(__dirname,'..')});
 assert.equal((manifest.localPresenterPreview||manifest.mirror.files['home_presenter.js']).sha256,crypto.createHash('sha256').update(reviewed).digest('hex'));
 assert.deepEqual(fs.readFileSync(path.resolve(__dirname,'../miniapp/shared/home_presenter.js')),reviewed);
 assert.equal(checkout.toString('utf8').replace(/\r\n/g,'\n'),reviewed.toString('utf8').replace(/\r\n/g,'\n'));
 const {verifyLocalBundle}=require('../miniapp/adapters/snapshot'),snapshots=verifyLocalBundle(require('../miniapp/generated/local-bundle'));
 const {createWebHomeAdapter}=require('../miniapp/lib/home_presenter_adapter');
 for(const server of ['cn','global']){
  const snapshot=snapshots[server],p=home.createHomePresenter(snapshot),adapter=createWebHomeAdapter(snapshot),t=snapshot.data.tracks[0];
  const draft={schema:1,server,zone:'zone5',tier:'理论',maps:[{big:t.大地图,small:t.小地图},null,null,null,null],cars:[],stars:{},oc:{},routes:{}};
  assert.deepEqual(adapter.guidance(draft),p.present(draft).guidance);assert.equal(adapter.guidance(draft).kind,'select_cars');
  draft.maps=[null,null,null,null,null];assert.equal(adapter.guidance(draft).message,'请先选择地图');
 }
});
