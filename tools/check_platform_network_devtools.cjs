'use strict';
// Run only after the isolated HTTPS service and server-side real verifier have been coordinated.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const sdk=require(path.resolve(process.argv[2])),project=path.resolve(process.argv[3]),out=path.resolve(process.argv[4]);
const config=require(path.join(project,'generated/native-config.js'));assert.equal(config.enabled,true,'probe is still awaiting configuration');assert.equal(config.kind,'platform');
const port=Number(process.argv[5]||9421);assert.ok(port>0&&port<=65535);fs.mkdirSync(out,{recursive:true});
(async()=>{const app=await sdk.connect({wsEndpoint:'ws://127.0.0.1:'+port});const exceptions=[];app.on('exception',()=>exceptions.push('native runtime exception'));try{
 let page;for(let i=0;i<60&&!page;i++){try{page=await app.currentPage();}catch(_){}if(!page)await new Promise(r=>setTimeout(r,150));}assert.ok(page);assert.equal(page.path,'pages/probe/probe');
 await app.evaluate(()=>getCurrentPages()[0].run());const report=await app.evaluate(()=>getCurrentPages()[0].probe.report());report.runtimeExceptions=exceptions;report.source='real wx APIs; backend verifier configuration requires separate operator evidence';report.realDevice=false;
 fs.writeFileSync(path.join(out,'network-result.json'),JSON.stringify(report,null,2));assert.equal(report.state,'passed');assert.equal(report.fixture,false);assert.equal(report.counts.cn,1);assert.equal(report.counts.global,1);assert.equal(exceptions.length,0);await app.screenshot({path:path.join(out,'network-check.png')});console.log('PASS network session and two byte-verified snapshots; OCR/account/phone not tested');
}finally{await app.disconnect();}})().catch(e=>{console.error(e.message);process.exitCode=1;});
