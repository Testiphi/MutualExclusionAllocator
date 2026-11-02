'use strict';
// Official automator: fixture identity + owned screenshot; real wx HTTP/uploadFile/CPU OCR.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const automator=require(path.resolve(process.argv[2])),out=path.resolve(process.argv[3]),sample=path.resolve(process.argv[4]);fs.mkdirSync(out,{recursive:true});
const bytes=fs.readFileSync(sample),sampleHash=crypto.createHash('sha256').update(bytes).digest('hex');
assert.equal(sampleHash,'4eee6ddf88543d96f826b0258f09668d2e09a4f3f8b493787c0ffe5c4efc1cd7','only approved attack06 fixture');
const report={fixtureAuth:true,realWechatAuth:false,imageSelectionFixture:true,realWxUploadFile:false,realCpuOCR:false,realDevice:false,checks:[],exceptions:[],storageRestored:false,sampleHash};
const keys=['cn','global'].flatMap(s=>['racepick.mini.native-fixture.draft.v1.'+s,'racepick.mini.view.v1.native-fixture.'+s]),backup={};
(async()=>{
 const app=await automator.connect({wsEndpoint:'ws://127.0.0.1:9420'});app.on('exception',e=>report.exceptions.push(e));let ownedPath,mediaMocked=false,p;
 const check=name=>{report.checks.push(name);console.log('PASS '+name);};
 try {
  for(let i=0;i<30&&!p;i++){try{p=await app.currentPage();}catch(_){}if(!p)await new Promise(r=>setTimeout(r,200));}
  assert.ok(p,'project did not finish reload');const settle=()=>p.waitFor(180);
  const until=async fn=>{for(let i=0;i<160;i++){if(await fn())return;const e=await p.data('error');if(e)throw Error(e);await p.waitFor(300);}throw Error('bounded simulator wait exceeded');};
  await until(async()=>await p.data('ready'));assert.equal(await p.data('mode'),'native-fixture');assert.equal((await p.data('serviceStatus')).online,true);
  const sys=await app.systemInfo();report.system={SDKVersion:sys.SDKVersion,platform:sys.platform,width:sys.windowWidth,height:sys.windowHeight};
  const stored=(await app.callWxMethod('getStorageInfoSync')).keys;for(const k of keys)backup[k]={exists:stored.includes(k),value:await app.callWxMethod('getStorageSync',k)};
  fs.writeFileSync(path.join(out,'storage-before.json'),JSON.stringify(backup,null,2));check('wx.request session and both SHA-verified native snapshots initialized');
  const tap=async selector=>{const e=await p.$(selector);assert.ok(e,selector);await e.tap();await settle();};
  const tapText=async text=>{for(const e of await p.$$('button'))if((await e.text()).trim()===text){await e.tap();await settle();return;}throw Error('missing '+text);};
  await tap('.toolbar button[data-server="cn"]');if(!await p.data('garageOpen'))await tap('.garage-heading');
  await tap('.class-filter button');await tap('[data-action="clear-all"]');
  await (await p.$('input.search')).input('f5');await settle();await tap('[data-action="select-all"]');assert.ok((await p.data('cars')).every(c=>c.selected));
  await tap('[data-action="clear-all"]');assert.equal(await p.data('selectedCount'),0);await tap('.car-name[data-id="f5"]');
  await app.pageScrollTo(0);await settle();const starTop=(await (await p.$('.garage-heading')).offset()).top;await app.pageScrollTo(starTop);await settle();
  let car=(await p.data('cars')).find(c=>c.id==='f5');await tap('.star-picker[data-id="f5"]');assert.equal((await p.data('dropdown')).field,'stars');
  await p.waitFor('.dropdown-option');
  await app.screenshot({path:path.join(out,'stars-dropdown.png')});await tap('.dropdown-option[data-value="0"]');
  assert.equal(await app.evaluate(()=>getCurrentPages()[0].state.draft.stars.f5),car.stars[0]);
  await tap('.star-picker[data-id="f5"]');await tap('.dropdown-option[data-value="'+(car.stars.length-1)+'"]');
  await tap('[data-action="sort"]');assert.equal(await p.data('sortMode'),'score-desc');await tap('[data-action="sort"]');assert.equal(await p.data('sortMode'),'score-asc');await tap('[data-action="sort"]');assert.equal(await p.data('sortMode'),'alpha');
  const sizes=[];for(const e of await p.$$('.car-row'))sizes.push((await e.size()).width);assert.ok(new Set(sizes.map(Math.round)).size>1,'car chips must follow label width');
  check('filtered select-all, clear-all, score sorting, irregular chips and in-page stars work');
  await app.pageScrollTo(0);const y=(await (await p.$('.garage-heading')).offset()).top;await app.pageScrollTo(y);await app.screenshot({path:path.join(out,'garage.png')});
  await app.evaluate(()=>{const p=getCurrentPages()[0],m=p.state.model.maps[0];for(let i=0;i<5;i++)p.controller.setMap(i,i===0?m:null);});
  const baseline=await p.data('rows');
  ownedPath=await app.evaluate((data,name)=>new Promise((resolve,reject)=>{const file=wx.env.USER_DATA_PATH+'/'+name;wx.getFileSystemManager().writeFile({filePath:file,data:wx.base64ToArrayBuffer(data),success:()=>resolve(file),fail:()=>reject(Error('owned fixture write failed'))});}),bytes.toString('base64'),'racepick-owned-ocr-'+Date.now()+'.png');
  await app.mockWxMethod('chooseMedia',{tempFiles:[{tempFilePath:ownedPath,size:bytes.length,fileType:'image'}],type:'image'});mediaMocked=true;
  await tap('.recognition-entry button');assert.ok(await p.data('image'));await tapText('开始识别');
  await until(async()=>['polling','finished'].includes((await app.evaluate(()=>getCurrentPages()[0].service.diagnostics())).task.phase));
  report.started=await app.evaluate(()=>getCurrentPages()[0].service.diagnostics());
  report.realWxUploadFile=report.started.network.uploads===1;
  await app.evaluate(()=>{getCurrentPages()[0].onHide();getCurrentPages()[0].onShow();});
  await until(async()=>await p.data('hasPending'));assert.deepEqual(await p.data('rows'),baseline);
  const expected=[['明珠港口','触摸天空'],['冰火岛','地心之外'],['海港博物馆','飞越城市'],['沙漠迷雾','国王的复兴'],['摩登城市','富豪之旅']];
  const pending=await app.evaluate(()=>getCurrentPages()[0].state.pending);assert.deepEqual(pending.map(m=>[m.big,m.small]),expected);
  report.finished=await app.evaluate(()=>getCurrentPages()[0].service.diagnostics());assert.equal(report.finished.network.uploads,1);assert.equal(report.finished.task.id,report.started.task.id);
  report.realWxUploadFile=true;report.realCpuOCR=true;
  check('real wx.uploadFile to same CPU worker yields five correct slots; simulated hide/show reuses same job without upload');
  await app.pageScrollTo(0);await app.screenshot({path:path.join(out,'ocr-pending.png')});
  await tapText('应用选图');await until(async()=>!(await p.data('hasPending')));
  assert.deepEqual((await p.data('rows')).map(m=>[m.big,m.small]),expected);check('apply revalidates native identity/catalog and only then fills manual maps');
  await tapText('生成方案');await until(async()=>!await p.data('busy'));assert.ok((await p.data('schemes')).length>0);
  if((await p.data('schemes')).length>1){await tap('#scheme-trigger');await tap('.dropdown-option[data-value="1"]');assert.equal(await p.data('schemeIndex'),1);}
  check('recognized lineup feeds shared allocator and in-page scheme selector');
  for(const k of (await app.callWxMethod('getStorageInfoSync')).keys.filter(k=>k.startsWith('racepick.mini.'))){const v=await app.callWxMethod('getStorageSync',k);assert.ok(!/"token"\s*:/.test(JSON.stringify(v)),'tokens must not be persisted');}
  assert.deepEqual(report.exceptions,[]);report.success=true;
 }catch(e){report.success=false;report.error=e.stack;throw e;}
 finally {
  try {
   if(p)await app.evaluate(()=>{const p=getCurrentPages()[0];if(p.controller)p.controller.destroy();});
   if(mediaMocked)await app.restoreWxMethod('chooseMedia');
   if(ownedPath)await app.evaluate(file=>new Promise(resolve=>{if(!file.includes('/racepick-owned-ocr-'))throw Error('not owned');wx.getFileSystemManager().unlink({filePath:file,complete:resolve});}),ownedPath);
   for(const k of keys)if(backup[k]){if(backup[k].exists)await app.callWxMethod('setStorageSync',k,backup[k].value);else await app.callWxMethod('removeStorageSync',k);}
   p=await app.reLaunch('/pages/home/home');const stored=(await app.callWxMethod('getStorageInfoSync')).keys;
   for(const k of keys)if(backup[k]){assert.equal(stored.includes(k),backup[k].exists);if(backup[k].exists)assert.deepEqual(await app.callWxMethod('getStorageSync',k),backup[k].value);}
   report.storageRestored=true;await app.screenshot({path:path.join(out,'home-restored.png')});
  }catch(e){report.restoreError=e.stack;report.success=false;}
  fs.writeFileSync(path.join(out,'native-ocr-report.json'),JSON.stringify(report,null,2));await app.disconnect();if(!report.success)process.exitCode=1;
 }
})().catch(e=>{console.error(e.message);process.exitCode=1;});
