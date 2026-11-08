'use strict';
// New independent project only. No credentials, login or backend request.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const sdk=require(path.resolve(process.argv[2])),project=path.resolve(process.argv[3]),out=path.resolve(process.argv[4]),port=Number(process.argv[5]);
const build=require(path.join(project,'generated/build-info')),config=require(path.join(project,'generated/account-config'));
const armed=process.argv[6]==='--armed-candidate';assert.equal(config.allowCloudWrites,armed);if(armed)assert.ok(config.conflictRole);assert.ok(config.conflictRole||config.readbackReceipt);assert.ok(!fs.existsSync(out));fs.mkdirSync(out,{recursive:true});
(async()=>{const app=await sdk.connect({wsEndpoint:'ws://127.0.0.1:'+port}),exceptions=[];app.on('exception',()=>exceptions.push('runtime exception'));try{
 let p;for(let i=0;i<50;i++){try{p=await app.currentPage();if(p?.path==='pages/home/home'&&await p.data('buildId')===build.buildId&&await p.data('ready'))break;}catch(_){}await new Promise(r=>setTimeout(r,100));}
 assert.equal(await p.data('buildId'),build.buildId);assert.equal(await p.data('allowCloudWrites'),armed);assert.equal(await p.data('accountRestricted'),true);
 const initial=await app.evaluate(()=>getCurrentPages().slice(-1)[0].acceptanceReport());assert.equal(initial.session.loggedIn,false);assert.ok(Object.values(initial.counts).every(n=>n===0));
 await (await p.$('[data-server="global"]')).tap();await (await p.$('[data-server="cn"]')).tap();
 const report=await app.evaluate(()=>getCurrentPages().slice(-1)[0].acceptanceReport());assert.ok(Object.values(report.counts).every(n=>n===0));
 const main=JSON.parse(fs.readFileSync(path.join(project,'project.config.json'),'utf8')),privatePath=path.join(project,'project.private.config.json'),priv=fs.existsSync(privatePath)?JSON.parse(fs.readFileSync(privatePath,'utf8')):{};
 assert.equal(priv.setting?.urlCheck??main.setting.urlCheck,true);assert.ok(!priv.appid||priv.appid===main.appid);const info=await app.callWxMethod('getAccountInfoSync');assert.equal(info.miniProgram.appId===main.appid,true);
 const sys=await app.systemInfo();assert.equal(exceptions.length,0);await app.screenshot({path:path.join(out,'home.png')});
 fs.writeFileSync(path.join(out,'preflight.json'),JSON.stringify({buildId:build.buildId,planId:build.planId,port,compiled:true,allowCloudWrites:armed,configuredRole:config.conflictRole||null,appIdMatches:true,effectiveUrlCheck:true,SDKVersion:sys.SDKVersion,exceptions,report,realLogin:false,realDevice:false},null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({compiled:true,buildId:build.buildId,planId:build.planId,zeroRequests:true,allowCloudWrites:armed}));
 }finally{await app.disconnect();}})().catch(e=>{console.error('Stage preflight failed: '+e.message);process.exitCode=1;});
