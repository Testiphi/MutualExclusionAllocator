'use strict';
// Read-only live state intake. Never reads credentials, tokens, IDs or headers.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const sdk=require(path.resolve(process.argv[2])),portFile=path.resolve(process.argv[3]),out=path.resolve(process.argv[4]),stage=process.argv[5];
assert.match(stage,/^[a-z0-9-]+$/);assert.ok(!fs.existsSync(out));
const port=JSON.parse(fs.readFileSync(portFile,'utf8').replace(/^\uFEFF/,'')).actualAutoPort;
(async()=>{const app=await sdk.connect({wsEndpoint:'ws://127.0.0.1:'+port});try{
 const result=await app.evaluate(()=>{
  const pages=getCurrentPages(),top=pages[pages.length-1],home=pages.find(p=>p.route==='pages/home/home');
  if(!home)return {homePresent:false,path:top?.route};
  const account=home.account?.state(),cloud=home.cloud,remote=cloud?.remote(),d=home.state?.draft;
  const prefix='racepick.mirror.acceptance.mini-account-mirror-20261106-04.';
  const guest=wx.getStorageSync(prefix+'racepick.mini.local.draft.v1.cn');
  return {homePresent:true,path:top.route,buildId:home.data.buildId,planId:home.data.planId,
   loggedIn:!!account?.actor,role:account?.actor?.role||null,
   expiresInSeconds:account?.expires_at?Math.floor(account.expires_at-Date.now()/1000):null,
   profilesCapability:account?.features?.profiles||null,pendingAuth:!!home.account?.pendingAuth(),
   diagnostics:home.accountDiagnostics(),
   home:{server:d?.server,cars:d?.cars,stars:d?.stars,oc:d?.oc,maps:d?.maps,
    selectedCount:home.data.selectedCount,cloudReady:!!home.cloudReady,
    cloudLoaded:!!home.data.cloudLoaded,cloudEmpty:!!home.data.cloudEmpty,
    dirty:home.data.dirty,cloudDirty:cloud?.state().dirty||false,
    cloudStatus:home.data.cloudStatus||null,resultSchemes:home.data.schemes?.length||0,
    pendingSave:!!cloud?.pendingKey(),hasConflict:!!cloud?.conflict(),
    remote:remote?{server:remote.server,revision:remote.revision,storage:remote.storage,
     remoteSupported:remote.remote_supported,kind:remote.profile===null?'null':remote.profile.cars.length?'saved':'empty'}:null},
   guestSamplePreserved:!!guest&&guest.cars?.length===1&&guest.cars[0]==='f5',
   accountPage:top.route==='pages/account/account'?{actorPresent:!!top.data.actor,errorPresent:!!top.data.error,busy:!!top.data.busy,recoverable:!!top.data.recoverable}:null};
 });
 assert.equal(result.homePresent,true);assert.equal(result.buildId,'e08f90fc815de4813731');
 const receipt={observedAtUtc:new Date().toISOString(),stage,actualAutoPort:port,...result};
 fs.writeFileSync(out,JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({stage,path:result.path,loggedIn:result.loggedIn,role:result.role,
  server:result.home.server,selectedCount:result.home.selectedCount,cloudReady:result.home.cloudReady,
  remote:result.home.remote,guestSamplePreserved:result.guestSamplePreserved,counts:result.diagnostics.counts}));
 }finally{await app.disconnect();}
})().catch(()=>{console.error('Safe mirror state intake did not pass; no action or credential read performed.');process.exitCode=1;});
