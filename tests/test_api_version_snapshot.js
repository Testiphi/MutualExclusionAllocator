'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync(require('node:path').join(__dirname,'..','api.js'),'utf8')+'\n;globalThis.testApi=api;';
test('versioned page pins cars and scores to one snapshot even across a publication',async()=>{
 let active={version:'before',cars:{cars:['original']},data:{time:20}},calls=0;
 const context=vm.createContext({APP_CONFIG:{dataSource:'static'},RACEPICK_VERSIONED_SCORES:true,fetch:async()=>{calls++;const captured=active;return {ok:true,json:async()=>captured};}});
 vm.runInContext(source,context);
 const cars=await context.testApi.getCars();active={version:'after',cars:{cars:['new']},data:{time:18}};
 const scores=await context.testApi.getRaceData();assert.equal(calls,1);assert.equal(cars.cars[0],'original');assert.equal(scores.time,20);
});
test('static and production default pages retain the existing JSON loading paths',async()=>{
 const paths=[];const context=vm.createContext({APP_CONFIG:{dataSource:'static',staticPaths:{carsJson:'cars.json',dataJson:'gauntlet_data.json'}},fetch:async path=>{paths.push(path);return {ok:true,json:async()=>({})};}});
 vm.runInContext(source,context);await context.testApi.getCars();await context.testApi.getRaceData();assert.deepEqual(paths,['cars.json','gauntlet_data.json']);
});

test('international versioned pages use one atomic verified three-file snapshot',async()=>{
 const path=require('node:path'),root=path.resolve(__dirname,'..'),names=['cars.global.json','gauntlet_data.global.json','global-data-manifest.json'];
 const files=Object.fromEntries(names.map(n=>[n,fs.readFileSync(path.join(root,n),'utf8')]));const calls=[];
 const context=vm.createContext({APP_CONFIG:{server:'global',dataSource:'static',staticPaths:{carsJson:names[0],dataJson:names[1],manifestJson:names[2]}},RACEPICK_VERSIONED_GLOBAL_SCORES:true,crypto:require('node:crypto').webcrypto,TextEncoder,TextDecoder,setTimeout,clearTimeout,fetch:async url=>{calls.push(url);return {ok:true,json:async()=>({version:'bound',files})};}});
 vm.runInContext(source,context);const cars=await context.testApi.getCars(),data=await context.testApi.getRaceData();assert.equal(cars.cars.length,46);assert.equal(data.tracks.length,44);assert.deepEqual(calls,['/api/scores/global-snapshot']);assert.equal(cars._meta.dataset_version,data._meta.dataset_version);
});

test('international atomic snapshots reject altered bytes without falling back to bundled or CN data',async()=>{
 const path=require('node:path'),root=path.resolve(__dirname,'..'),names=['cars.global.json','gauntlet_data.global.json','global-data-manifest.json'];
 const files=Object.fromEntries(names.map(n=>[n,fs.readFileSync(path.join(root,n),'utf8')]));files[names[1]]+=' ';const calls=[];
 const context=vm.createContext({APP_CONFIG:{server:'global',dataSource:'static',staticPaths:{carsJson:names[0],dataJson:names[1],manifestJson:names[2]}},RACEPICK_VERSIONED_GLOBAL_SCORES:true,crypto:require('node:crypto').webcrypto,TextEncoder,TextDecoder,setTimeout,clearTimeout,fetch:async url=>{calls.push(url);return {ok:true,json:async()=>({files})};}});
 vm.runInContext(source,context);await assert.rejects(()=>context.testApi.getCars(),/完整性/);assert.deepEqual(calls,['/api/scores/global-snapshot']);
});
