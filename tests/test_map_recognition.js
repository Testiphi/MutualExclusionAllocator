'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {validMaps,compatible,fileError,imageType}=require('../map_recognition.js');
const maps=Array.from({length:5},(_,i)=>({big:'区域'+i,small:'地图'+i}));
test('confirmation requires all five catalog-bound distinct regions',()=>{
 assert(validMaps(maps,maps));assert(!validMaps(maps.slice(1),maps));
 assert(!validMaps([{big:'未知',small:'地图0'},...maps.slice(1)],maps));
 assert(!validMaps([maps[0],maps[0],...maps.slice(2)],maps));
 assert(!validMaps([{big:'区域0',small:''},...maps.slice(1)],maps));
});
test('account/session, server and catalog version changes invalidate previous result',()=>{
 const start={identity:'guest-session-A',server:'cn',version:'one'};
 assert(compatible(start,{...start}));
 for(const change of [{identity:'guest-session-B'},{server:'global'},{version:'two'}])assert(!compatible(start,{...start,...change}));
});
test('browse and drag share one-file type and size validation',()=>{
 const png={name:'截图.png',type:'image/png',size:100};
 assert.equal(fileError([png]),'');assert.match(fileError([]),/一张/);
 assert.match(fileError([png,png]),/一张/);assert.match(fileError([{...png,size:9*1024*1024}]),/太大/);
 assert.match(fileError([{name:'x.txt',type:'text/plain',size:3}]),/不支持/);
 assert.equal(imageType({name:'照片.JPEG',type:''}),'image/jpeg');
 assert.equal(fileError([{name:'照片.JPEG',type:'',size:100}]),'');
});
