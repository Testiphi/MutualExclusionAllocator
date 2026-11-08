'use strict';
// Official SDK local compilation/navigation only. Never submits credentials.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const sdk=require(path.resolve(process.argv[2])),project=path.resolve(process.argv[3]),output=path.resolve(process.argv[4]);
const ports=JSON.parse(fs.readFileSync(path.resolve(process.argv[5]),'utf8').replace(/^\uFEFF/,''));
const build=require(path.join(project,'generated/build-info')),config=require(path.join(project,'generated/account-config')),local=require(path.join(project,'project.config.json'));
const privateFile=path.join(project,'project.private.config.json'),privateConfig=fs.existsSync(privateFile)?JSON.parse(fs.readFileSync(privateFile,'utf8')):{};assert.equal(config.allowCloudWrites,false);assert.equal(local.setting.urlCheck,true);assert.equal(privateConfig.setting?.urlCheck??local.setting.urlCheck,true);assert.ok(!privateConfig.appid||privateConfig.appid===local.appid);assert.ok(!fs.existsSync(output));fs.mkdirSync(output,{recursive:true});
(async()=>{const app=await sdk.connect({wsEndpoint:'ws://127.0.0.1:'+ports.actualAutoPort}),exceptions=[];app.on('exception',()=>exceptions.push('runtime exception'));
 const report={buildId:build.buildId,planId:build.planId,actualAutoPort:ports.actualAutoPort,exceptions,realLogin:false,realDevice:false,requestsExpected:0};
 try{
  let p;try{p=await app.currentPage();}catch(_){}if(p?.path==='pages/account/account')await app.reLaunch('/pages/home/home');for(let i=0;i<60;i++){try{p=await app.currentPage();if(p?.path==='pages/home/home'&&await p.data('buildId')===build.buildId&&await p.data('ready'))break;}catch(_){}await new Promise(r=>setTimeout(r,150));}
  assert.equal(await p.data('buildId'),build.buildId);assert.equal(await p.data('ready'),true);assert.equal(await p.data('accountRestricted'),true);assert.equal(await p.data('allowCloudWrites'),false);
  const info=await app.callWxMethod('getAccountInfoSync');assert.equal(info.miniProgram.appId===local.appid,true);report.appIdMatches=true;
  report.initial=await app.evaluate(()=>getCurrentPages()[0].accountDiagnostics());assert.ok(Object.values(report.initial.counts).every(n=>n===0));
  await app.screenshot({path:path.join(output,'home.png')});
  await app.evaluate(()=>getCurrentPages()[0].controller.switchServer('global'));
  await app.evaluate(()=>getCurrentPages()[0].controller.switchServer('cn'));
  await app.reLaunch('/pages/account/account');
  const account=await app.currentPage();assert.equal(await account.data('restricted'),true);assert.equal(await app.evaluate(()=>getCurrentPages()[0].data.actor===null),true);
  await app.evaluate(()=>{const p=getCurrentPages()[0];p.changeMode({detail:{value:'register'}});return true;});
  assert.equal(await account.data('mode'),'login');
  await app.evaluate(()=>getCurrentPages()[0].changeMode({detail:{value:'login'}}));
  await app.screenshot({path:path.join(output,'account.png')});
  await app.reLaunch('/pages/home/home');
  p=await app.currentPage();assert.equal(await p.data('buildId'),build.buildId);
  report.final=await app.evaluate(()=>getCurrentPages()[0].accountDiagnostics());
  const exported=await app.evaluate(()=>{const p=getCurrentPages().slice(-1)[0];return typeof p.acceptanceReport==='function'?p.acceptanceReport():null;});if(exported){assert.equal(exported.buildId,build.buildId);assert.equal(exported.allowCloudWrites,false);assert.ok(Object.values(exported.counts).every(n=>n===0));report.acceptanceExportVerified=true;}assert.ok(Object.values(report.final.counts).every(n=>n===0));
  const sys=await app.systemInfo();report.SDKVersion=sys.SDKVersion;report.platform=sys.platform;report.compiled=true;report.noLoginOrNetwork=true;assert.equal(exceptions.length,0);
  console.log(JSON.stringify({compiled:true,buildId:build.buildId,actualAutoPort:ports.actualAutoPort,noLoginOrNetwork:true,appIdMatches:true}));
 }finally{fs.writeFileSync(path.join(output,'preflight.json'),JSON.stringify(report,null,2)+'\n');await app.disconnect();}
})().catch(()=>{console.error('Mirror preflight did not pass; inspect sanitized receipt. No credential operation requested.');process.exitCode=1;});
