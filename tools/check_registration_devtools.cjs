'use strict';
// SDK preflight: no submits, credential inspection, or uploads.
const assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
const [sdk,project,port,output]=process.argv.slice(2);
const build=require(path.join(path.resolve(project),'generated/build-info.js'));
const appConfig=require(path.join(path.resolve(project),'app.json'));
const automator=require(path.resolve(sdk));
(async()=>{
 const app=await automator.connect({wsEndpoint:'ws://127.0.0.1:'+Number(port)});
 let exceptions=0;app.on('exception',()=>exceptions++);
 try{
  assert.equal(appConfig.lazyCodeLoading,'requiredComponents');
  async function launchHome(){
   const home=await app.reLaunch('/pages/home/home');
   for(let i=0;i<50&&!(await home.data('ready'));i++)await home.waitFor(120);
   assert.equal(await home.data('ready'),true);
   return home;
  }
  for(const mode of ['register','login','verify-email','resend-verification']){
   const home=await launchHome();
   console.log(`Checking ${mode}`);
   if(mode==='register'||mode==='login'){
    const selector=`button[data-page="account"][data-mode="${mode}"]`;
    let entry;
    for(let i=0;i<30&&!entry;i++){
     const current=await app.currentPage();
     if(current?.path==='pages/home/home')entry=await current.$(selector);
     if(!entry)await home.waitFor(120);
    }
    assert.ok(entry,`Missing homepage ${mode} entry`);
    await entry.tap();
   }else await app.callWxMethod('navigateTo',{url:'/pages/account/account?mode='+mode});
   let page;
   for(let i=0;i<30;i++){page=await app.currentPage();if(page?.path==='pages/account/account'&&await page.data('mode')===mode)break;await home.waitFor(120);}
   assert.equal(page.path,'pages/account/account');assert.equal(await page.data('mode'),mode);
   assert.equal(await page.data('registration'),true);
   for(const action of ['register','verify-email','resend-verification'])assert.ok(await page.$('button[data-mode="'+action+'"]'));
   for(const action of ['forgot-password','reset-password','redeem-invitation'])assert.equal(await page.$('button[data-mode="'+action+'"]'),null);
   assert.equal(!!(await page.$('input[data-key="passwordConfirm"]')),mode==='register');
   if(mode==='register')assert.equal(await page.$('input[data-key="invite_code"]'),null);
  }
  const report=await app.evaluate(()=>getCurrentPages()[0].acceptanceReport());
  assert.equal(report.buildId,build.buildId);
  assert.equal(report.kind,'racepick-isolated-registration-report-v1');
  assert.ok(Object.values(report.counts).every(v=>v===0));
  assert.equal(exceptions,0);
  fs.writeFileSync(output,JSON.stringify({buildId:build.buildId,compiled:true,forms:4,homeEntries:['register','login'],lazyComponents:true,counts:report.counts,exceptions},null,2),{flag:'wx'});
 }finally{await app.disconnect();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
