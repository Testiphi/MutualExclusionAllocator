'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {createAcceptanceReport}=require('../miniapp/services/account_acceptance_report');
const runtime=require('../miniapp/services/runtime');
const now=Date.UTC(2026,10,7),build={buildId:'a'.repeat(20),planId:'mini-account-mirror-report-test'};
test('acceptance report whitelists fields and excludes identity, credentials, raw headers and diagnostic text',()=>{
 const r=createAcceptanceReport({build,now,device:{model:'test phone',system:'test OS',OpenID:'private-openid'},
  account:{actor:{id:'private-actor',email:'private@example.test',role:'player'},token:'rpa1.private-token',password:'private-password',pendingAuth:true,expires_at:now/1000+3000},
  diagnostics:{ready:true,allowCloudWrites:false,token:'private-diagnostic-token',healthDiagnostic:{kind:'domain_rejected',nativeCode:600002,errno:-1,errMsg:'private-native-text'},counts:{health:1,guest:1,snapshot:2,login:1,profile:2,session:2,recovery:0,email:'private-counter'}},
  profiles:{cn:{loaded:true,remote:{revision:0,kind:'null',storage:'account',remoteSupported:true,token:'private-remote-token'},draft:{cars:['f5'],stars:{f5:5},password:'private-draft-password'},dirty:true}},view:{server:'cn',selectedCount:1,mappedSlots:1,schemeCount:1}});
 const encoded=JSON.stringify(r);for(const secret of ['private-openid','private-actor','private@example.test','rpa1.private-token','private-password','private-diagnostic-token','private-native-text','private-counter','private-remote-token','private-draft-password'])assert.ok(!encoded.includes(secret));
 assert.equal(r.session.role,'player');assert.equal(r.session.expiresInSeconds,3000);assert.equal(r.session.pendingAuth,true);assert.equal(r.health.nativeCode,600002);assert.equal(r.health.errno,-1);assert.equal(r.profiles.cn.remote.kind,'null');assert.equal(r.profiles.cn.dirty,true);
});
test('null remote and saved-empty remain distinct and Global OC retains strict booleans',()=>{
 const r=createAcceptanceReport({build,now,profiles:{cn:{loaded:true,remote:{revision:0,kind:'null',storage:'account',remoteSupported:true},draft:null},global:{loaded:true,remote:{revision:1,kind:'empty',storage:'account',remoteSupported:true},draft:{cars:[],stars:{},ocMap:{f5:true,ssc:false,bad:1}}}}});
 assert.equal(r.profiles.cn.remote.kind,'null');assert.equal(r.profiles.cn.draft,null);assert.equal(r.profiles.global.remote.kind,'empty');assert.deepEqual(r.profiles.global.draft,{cars:[],stars:{},ocMap:{f5:true,ssc:false}});
});
test('unread profiles remain unread; an expired session is not reported as positive lifetime',()=>{
 const r=createAcceptanceReport({build,now,account:{actor:{role:'player'},expires_at:now/1000-1},profiles:{cn:null,global:null}});
 assert.deepEqual(r.profiles,{cn:null,global:null});assert.equal(r.session.expiresInSeconds,-1);assert.equal(r.connectionReady,false);assert.equal(r.counts.login,null);
});
test('runtime profile-state export is a local read and does not initialize a connection or request',()=>{
 let requests=0;runtime.mount({request(){requests++;}},{kind:'fixture'},{},{enabled:false});assert.deepEqual(runtime.profileStates(),{cn:null,global:null});assert.equal(requests,0);
});
