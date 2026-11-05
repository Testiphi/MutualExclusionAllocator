'use strict';
// Official SDK. Never reads form credentials, page-wide data, headers or tokens.
// Final argument: connect (new guest only), accept (inspect user results), or absent (inspect).
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const sdk=require(path.resolve(process.argv[2])),project=path.resolve(process.argv[3]),out=path.resolve(process.argv[4]);
const ports=JSON.parse(fs.readFileSync(path.resolve(process.argv[5]),'utf8').replace(/^\uFEFF/,''));
const generated=require(path.join(project,'generated/config')),local=JSON.parse(fs.readFileSync(path.join(project,'project.config.json'),'utf8'));
assert.equal(generated.plan.readOnly,true);assert.equal(generated.plan.allowCloudWrites,false);assert.equal(local.setting.urlCheck,true);assert.ok(!fs.existsSync(path.join(project,'project.private.config.json')));assert.ok(!fs.existsSync(path.join(out,'result.json')));
fs.mkdirSync(out,{recursive:true});
(async()=>{const app=await sdk.connect({wsEndpoint:'ws://127.0.0.1:'+ports.actualAutoPort}),exceptions=[];app.on('exception',()=>exceptions.push('runtime exception'));
 try{
  let page;for(let i=0;i<60;i++){try{page=await app.currentPage();if(page&&page.path==='pages/account/account'&&await page.data('buildId')===generated.probeId)break;}catch(_){}await new Promise(r=>setTimeout(r,150));}
  assert.equal(await page.data('buildId'),generated.probeId);
  const info=await app.callWxMethod('getAccountInfoSync');assert.equal(info.miniProgram.appId===local.appid,true);
  const sys=await app.systemInfo();
  let r=await app.evaluate(()=>getCurrentPages()[0].probe.report());
  assert.equal(r.readOnly,true);assert.equal(r.allowCloudWrites,false);
  if(process.argv[6]==='connect'){
   assert.equal(r.loginAttempted,false);assert.equal(r.counts.guestSessions,0);
   await app.evaluate(async()=>{await getCurrentPages()[0].connect();return true;});
   r=await app.evaluate(()=>getCurrentPages()[0].probe.report());
  }
  const result={buildId:generated.probeId,actualAutoPort:ports.actualAutoPort,compiled:true,appIdMatches:true,urlCheck:true,privateOverride:false,platform:sys.platform,SDKVersion:sys.SDKVersion,exceptions,report:r,realAccountLogin:r.loggedIn,realDevice:false};
  fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(result,null,2));
  // Screenshot only while no credential action has occurred, before user handoff.
  if(!r.loginAttempted)await app.screenshot({path:path.join(out,'before-credentials.png')});
  assert.equal(exceptions.length,0);
  if(['connect','accept'].includes(process.argv[6])){assert.equal(r.connected,true);assert.equal(r.bindingVerified,true);assert.deepEqual(r.snapshotChecks,{cn:true,global:true});}
  if(process.argv[6]==='accept'){assert.equal(r.loggedIn,true);assert.equal(r.role,'player');assert.equal(r.pendingAuth,false);assert.ok(Object.values(r.sessionValidation||{}).length>=5&&Object.values(r.sessionValidation).every(Boolean));for(const s of ['cn','global']){assert.equal(r.profileChecks[s]?.authenticatedRead,true);assert.equal(r.profiles[s]?.dirty,false);}assert.equal(r.counts.authPosts,1);assert.equal(r.counts.profileWrites,0);assert.equal(r.counts.logouts,0);assert.equal(r.errorCode,null);}
  console.log(JSON.stringify({compiled:true,buildId:generated.probeId,actualAutoPort:ports.actualAutoPort,appIdMatches:true,connected:r.connected,bindingVerified:r.bindingVerified,errorCode:r.errorCode}));
 }finally{await app.disconnect();}
})().catch(()=>{console.error('Readonly SDK check did not pass; inspect sanitized result if written. No account login submitted.');process.exitCode=1;});
