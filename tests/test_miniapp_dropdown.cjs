'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function page({deferred=false,mock=false,rect={left:250,top:620,bottom:660,width:120,height:40}}={}) {
 const file=path.resolve(__dirname,'../miniapp/pages/home/home.js');let config;const callbacks=[];let mediaOptions;
 const wx={getStorageSync:()=>undefined,setStorageSync(){},getWindowInfo:()=>({windowWidth:390,windowHeight:753}),
  createSelectorQuery(){return {select(){return this;},boundingClientRect(cb){if(deferred)callbacks.push(cb);else cb(rect);return this;},exec(){}};},
  chooseMedia(options){mediaOptions=options;options.success({tempFiles:[{tempFilePath:'tmp/album-screenshot',size:1024}]});}};
 vm.runInNewContext(fs.readFileSync(file,'utf8'),{Page:x=>{config=x;},wx,require:x=>x==='../../generated/native-config'?{enabled:false}:mock&&x==='../../generated/local-bundle'?null:require(path.resolve(path.dirname(file),x))});
 const p={...config,data:structuredClone(config.data),setData(x){Object.assign(this.data,x);}};p.onLoad();
 return {p,callbacks,rect,get mediaOptions(){return mediaOptions;}};
}
const open=(p,index,field,pending=false)=>p.openDropdown({currentTarget:{dataset:{index,field,pending}}});
const choose=(p,value)=>p.chooseDropdown({currentTarget:{dataset:{value}}});
test('custom dropdown is anchored inside viewport, scrollable and highlights current option',()=>{
 const {p}=page();const map=p.state.model.maps[0];p.controller.setMap(0,map);open(p,0,'big');
 const d=p.data.dropdown;assert.ok(d);assert.ok(d.left>=12&&d.left+d.width<=378);
 assert.ok(d.top>=12&&d.top+d.maxHeight+10<=753);assert.ok(d.top<620,'opens upward near screen bottom');
 assert.equal(d.options.filter(x=>x.selected).length,1);assert.equal(d.options.find(x=>x.selected).label,map.big);
 assert.ok(d.maxHeight<=260);p.closeDropdown();assert.equal(p.data.dropdown,null);p.onUnload();
});
test('disabled duplicate big maps cannot be selected; choosing maps or clearing a slot preserves garage',()=>{
 const {p}=page();const first=p.state.model.maps[0];p.controller.setMap(0,first);p.controller.setCar(p.state.model.cars[0].id,true);
 open(p,1,'big');const duplicate=p.data.dropdown.options.find(x=>x.label===first.big);assert.equal(duplicate.disabled,true);
 choose(p,duplicate.value);assert.equal(p.state.draft.maps[1],null);assert.ok(p.data.dropdown);
 const available=p.data.dropdown.options.find(x=>x.value>0&&!x.disabled);choose(p,available.value);
 assert.equal(p.data.dropdown,null);assert.equal(p.state.draft.maps[1].big,available.label);
 open(p,1,'small');choose(p,1);assert.ok(p.state.draft.maps[1].small);assert.equal(p.state.draft.cars.length,1);
 open(p,1,'big');choose(p,0);assert.equal(p.state.draft.maps[1],null);assert.equal(p.state.draft.cars.length,1);p.onUnload();
});
test('small-map list requires a region; late measurements, scroll, hide and state changes cannot reopen closed menu',()=>{
 const {p,callbacks,rect}=page({deferred:true});open(p,0,'small');assert.equal(callbacks.length,0);
 open(p,0,'big');p.closeDropdown();callbacks.shift()(rect);assert.equal(p.data.dropdown,null);
 open(p,0,'big');callbacks.shift()(rect);assert.ok(p.data.dropdown);p.onPageScroll();assert.equal(p.data.dropdown,null);
 open(p,0,'big');p.controller.switchServer('global');callbacks.shift()(rect);assert.equal(p.data.dropdown,null);
 open(p,0,'big');callbacks.shift()(rect);p.onHide();assert.equal(p.data.dropdown,null);p.onUnload();
});
test('recognition review uses same dropdown while manual selections await explicit confirmation',async()=>{
 const {p}=page({mock:true});const original=p.state.model.maps[0];p.controller.setMap(0,original);
 await p.controller.chooseImage();await p.controller.recognize();assert.ok(p.state.pending);
 open(p,0,'big',true);choose(p,6);assert.equal(p.state.pending[0].big,'联调区域6');assert.equal(p.state.draft.maps[0].big,original.big);
 open(p,0,'small',true);choose(p,1);assert.equal(p.state.pending[0].small,'联调赛道6');
 p.controller.applyRecognition();assert.equal(p.state.draft.maps[0].big,'联调区域6');p.onUnload();
});
test('album request has only one original image, no camera choice, and local preview never implies real OCR',async()=>{
 const f=page(),p=f.p,before=JSON.stringify(p.state.draft.maps);await p.controller.chooseImage();
 assert.equal(f.mediaOptions.count,1);assert.deepEqual(Array.from(f.mediaOptions.sourceType),['album']);
 assert.deepEqual(Array.from(f.mediaOptions.mediaType),['image']);assert.deepEqual(Array.from(f.mediaOptions.sizeType),['original']);
 assert.equal(p.data.image,'tmp/album-screenshot');await p.controller.recognize();
 assert.match(p.data.error,/尚未接入/);assert.equal(JSON.stringify(p.state.draft.maps),before);p.onUnload();
});
