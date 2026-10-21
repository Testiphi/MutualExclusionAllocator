'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync('api.js','utf8')+'\n;globalThis.testApi=api;';
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
