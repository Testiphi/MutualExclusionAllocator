'use strict';
// Uses the official miniprogram-automator SDK. Never uploads or starts preview.
// Args: absolute SDK package directory, output directory. IDE auto port: 9420.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const automator = require(path.resolve(process.argv[2]));
const output = path.resolve(process.argv[3]); fs.mkdirSync(output,{recursive:true});
const report = {checks:[],exceptions:[],storageRestored:false,realDevice:false,realOCR:false};
const record = name => { report.checks.push(name); console.log('PASS '+name); };
(async()=>{
  const app = await automator.connect({wsEndpoint:'ws://127.0.0.1:9420'});
  app.on('exception',e=>report.exceptions.push(e));
  const keys = ['racepick.mini.local.draft.v1.cn','racepick.mini.local.draft.v1.global'];
  const backup = {};
  try {
    const system = await app.systemInfo();
    report.system = {platform:system.platform,model:system.model,width:system.windowWidth,height:system.windowHeight,SDKVersion:system.SDKVersion};
    const storedKeys = (await app.callWxMethod('getStorageInfoSync')).keys;
    for(const key of keys) backup[key] = {exists:storedKeys.includes(key),value:await app.callWxMethod('getStorageSync',key)};
    fs.writeFileSync(path.join(output,'storage-before.json'),JSON.stringify(backup,null,2));
    let p = await app.reLaunch('/pages/home/home');
    const settle = () => p.waitFor(150);
    assert.equal(await p.data('mode'),'local');assert.equal(await p.data('ready'),true);assert.equal(await p.data('error'),'');
    record('native page compiled and initialized with verified local data');
    // Operate on a blank in-memory draft, preserving durable records in backup.
    await app.evaluate(()=>{const p=getCurrentPages()[0];p.controller.switchServer('cn');for(let i=0;i<5;i++)p.controller.setMap(i,null);for(const id of [...p.state.draft.cars])p.controller.setCar(id,false);});
    const river=await app.evaluate(()=>getCurrentPages()[0].state.model.maps.find(m=>m.small==='河畔漂移'));
    let row=(await p.data('rows'))[0];
    await (await p.$('picker[data-index="0"][data-field="big"]')).trigger('change',{value:String(row.bigs.indexOf(river.big))});
    await settle();
    row=(await p.data('rows'))[0];assert.equal(row.big,river.big);
    await (await p.$('picker[data-index="0"][data-field="small"]')).trigger('change',{value:String(row.smalls.indexOf(river.small))});
    await settle();
    assert.equal((await p.data('rows'))[0].small,'河畔漂移');record('native picker change events select real map');
    const tapText=async text=>{for(const b of await p.$$('button'))if((await b.text()).trim()===text){await b.tap();await settle();return;}throw Error('button not found: '+text);};
    if(!await p.data('garageOpen')){await (await p.$('.card > button')).tap();await settle();}
    await (await p.$('input.search')).input('f5');
    await settle();
    await (await p.$('.car-name[data-id="f5"]')).tap();
    await settle();
    assert.equal(await p.data('selectedCount'),1);record('native input search and car tap update garage');
    const key=river.big+'/'+river.small;
    const setRoute=async value=>{
      let route=(await p.data('routes'))[0];
      if(value==='off') {if(route.enabled){await (await p.$('.route-row button')).tap();await settle();}return;}
      if(!route.enabled){await (await p.$('.route-row button')).tap();await settle();}
      route=(await p.data('routes'))[0];
      await (await p.$('.route-row picker')).trigger('change',{value:String(value==='all'?0:route.options.indexOf(value))});
      await settle();
    };
    const compute=async expected=>{
      await tapText('生成方案');await p.waitFor(async()=>!await p.data('busy'));
      const schemes=await p.data('schemes');assert.equal(schemes[0].rows[0].timeText,expected);
    };
    await setRoute('all');await compute('19.900秒');
    await setRoute('稳定跳图');await compute('23.200秒');
    await setRoute('off');await compute('23.790秒');
    await (await p.$('.route-row button')).tap();await settle();await compute('23.200秒');record('native route picker/toggle produces real shared scores and remembers choice');
    await tapText('保存车库');assert.equal(await p.data('dirty'),false);
    const saved=await app.callWxMethod('getStorageSync',keys[0]);assert.ok(saved.cars.includes('f5'));
    await (await p.$('.toolbar button[data-server="global"]')).tap();
    await settle();
    assert.equal(await p.data('server'),'global');assert.deepEqual(await p.data('zones'),['五区']);assert.deepEqual(await p.data('tiers'),['理论']);
    assert.equal((await p.data('rows')).filter(r=>r.small==='河畔漂移').length,0);
    await (await p.$('input.search')).input('');await settle();
    const oc=await p.$('.oc-toggle');
    assert.ok(oc,'international OC button must exist');
    const ocId=await oc.attribute('data-id');
    const originalOc=await app.evaluate(id=>getCurrentPages()[0].state.draft.oc[id]===true,ocId);
    await oc.tap();await settle();
    assert.equal(await app.evaluate(id=>getCurrentPages()[0].state.draft.oc[id]===true,ocId),!originalOc);
    await oc.tap();await settle();record('compact native OC button toggles separately from owned state');
    await (await p.$('.toolbar button[data-server="cn"]')).tap();await settle();assert.equal(await p.data('selectedCount'),1);
    assert.equal((await p.data('rows'))[0].small,'河畔漂移');record('explicit save and server switch preserve independent local drafts');
    // Duplicate big is rejected by the actual native event pipeline.
    row=(await p.data('rows'))[1];
    await (await p.$('picker[data-index="1"][data-field="big"]')).trigger('change',{value:String(row.bigs.indexOf(river.big))});
    await settle();
    assert.match(await p.data('error'),/重复/);assert.equal((await p.data('rows'))[1].big,'');
    await tapText('保存车库');record('duplicate big map is rejected without deleting garage');
    await (await p.$('.tier-row button[data-index="1"]')).tap();await settle();assert.equal(await p.data('tierIndex'),1);
    await (await p.$('.zone-row button[data-index="1"]')).tap();await settle();assert.equal(await p.data('zoneIndex'),1);
    await (await p.$('.zone-row button[data-index="0"]')).tap();await settle();
    await (await p.$('.tier-row button[data-index="0"]')).tap();await settle();record('website-style tier and zone radio buttons preserve native interaction');
    await compute('23.200秒');
    await app.evaluate(()=>{const p=getCurrentPages()[0],maps=[];for(const m of p.state.model.maps)if(maps.length<5&&!maps.some(x=>x.big===m.big))maps.push(m);maps.forEach((m,i)=>p.controller.setMap(i,m));});
    await tapText('生成方案');
    assert.ok((await p.data('schemes')).length>1);
    await p.waitFor('.results picker');
    await (await p.$('.results picker')).trigger('change',{value:'1'});await settle();assert.equal(await p.data('schemeIndex'),1);
    assert.equal((await p.data('activeScheme')).index,1);record('native scheme picker changes displayed scheme without reordering solutions');
    await app.evaluate(map=>{const p=getCurrentPages()[0];for(let i=0;i<5;i++)p.controller.setMap(i,i===0?map:null);},river);
    await compute('23.200秒');
    await (await p.$('input.search')).input('');await settle();
    await app.pageScrollTo(0);
    const garageTop=(await (await p.$('.garage-heading')).offset()).top;
    await app.pageScrollTo(garageTop);await settle();await app.screenshot({path:path.join(output,'garage.png')});
    if(await p.data('garageOpen')){await (await p.$('.card > button')).tap();await settle();}
    await app.pageScrollTo(0);await app.screenshot({path:path.join(output,'home-selected.png')});
    await app.pageScrollTo(10000);await settle();await app.screenshot({path:path.join(output,'results.png')});
    const bounds=[];
    for(const selector of ['.page','.toolbar','.card','.map-row','.car-row','.route-row','.result-row']) {
      for(const el of await p.$$(selector)) {
        const size=await el.size(),offset=await el.offset();
        assert.ok(offset.left>=-1 && offset.left+size.width<=system.windowWidth+1,selector+' overflows');
        bounds.push({selector,left:offset.left,width:size.width});
      }
    }
    report.bounds=bounds;record('390px simulator layout has no measured horizontal overflow');
    assert.deepEqual(report.exceptions,[]);report.success=true;
  } catch(e) {report.success=false;report.error=e.stack;throw e;}
  finally {
    try {
      // Prevent lifecycle autosave from changing the restored durable records.
      await app.evaluate(()=>getCurrentPages()[0].controller.destroy());
      for(const key of keys) if(backup[key]) {
        if(backup[key].exists)await app.callWxMethod('setStorageSync',key,backup[key].value);
        else await app.callWxMethod('removeStorageSync',key);
      }
      await app.reLaunch('/pages/home/home');
      const storedKeys=(await app.callWxMethod('getStorageInfoSync')).keys;
      for(const key of keys) if(backup[key]) {
        assert.equal(storedKeys.includes(key),backup[key].exists);
        if(backup[key].exists)assert.deepEqual(await app.callWxMethod('getStorageSync',key),backup[key].value);
      }
      report.storageRestored=true;
      await app.screenshot({path:path.join(output,'home-restored.png')});
    } catch(e) {report.restoreError=e.stack;report.success=false;}
    fs.writeFileSync(path.join(output,'simulator-report.json'),JSON.stringify(report,null,2));
    await app.disconnect();
    if(!report.success)process.exitCode=1;
  }
})().catch(e=>{console.error(e.message);process.exitCode=1;});
