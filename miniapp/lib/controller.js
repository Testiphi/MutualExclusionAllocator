'use strict';
const clone = value => JSON.parse(JSON.stringify(value));
function blank(server) {
  return { schema: 1, server, zone: 'zone5', tier: '理论',
    maps: [null, null, null, null, null], cars: [], stars: {}, oc: {}, routes: {} };
}
function createController({ service, storage, media, render, autoCompute=false,schedule=fn=>setTimeout(fn,0) }) {
  let draft = blank('cn'), saved = null, model, epoch = 0, mediaEpoch = 0, visible = true;
  let error = '', busy = false, result = null, pending = null, image = null, dirty = false;
  let blocked = false;
  let workingBlocked=false;
  let profileBase=null;
  const profile=value=>JSON.stringify({cars:[...(value.cars||[])].sort(),stars:Object.entries(value.stars||{}).sort(),oc:Object.entries(value.oc||{}).sort()});
  function updateDirty(){dirty=profile(draft)!==profile(profileBase||draft);}
  function queueCompute(){if(!autoCompute||blocked||workingBlocked)return;const ticket=epoch;schedule(()=>{if(visible&&ticket===epoch)void compute();});}
  function refresh() {
    // Ask the shared service for the current catalogue before submitting a saved
    // draft: removed maps/unsupported old modes must not crash core validation.
    const catalog = service.model(blank(draft.server));
    if (catalog.server !== draft.server) throw Error('目录服别不符');
    if (!catalog.zones.includes(draft.zone)) draft.zone = catalog.zones[0];
    if (!catalog.tiers.includes(draft.tier)) draft.tier = catalog.tiers[0];
    if (catalog.knownCarIds) draft.cars = draft.cars.filter(id => catalog.knownCarIds.includes(id));
    const used = new Set();
    draft.maps = draft.maps.map(map => {
      if (!map || used.has(map.big) || !catalog.maps.some(x => x.big === map.big && (!map.small || x.small === map.small))) return null;
      used.add(map.big); return map;
    });
    model = service.model(clone(draft));
    // Keep saved stars and garage across zones. Shared core clamps effective stars;
    // the page displays a valid value without overwriting the user's other-zone input.
  }
  function publish() {
    render({ draft: clone(draft), model: clone(model), error, busy, result,
      pending: pending && clone(pending), image: image && image.path, dirty,
      mode: service.mode, storageBlocked: blocked,serviceStatus:service.status?service.status():null });
  }
  function invalidate(preserveMedia = false,preserveTask = false,preserveResult = false) {
    if (!preserveMedia) mediaEpoch++;
    epoch++; busy = false;if(!preserveResult)result = null; pending = null;
    if(preserveTask&&service.suspend)service.suspend();else service.cancel();
  }
  function change(fn) {
    invalidate(); error = '';
    fn(); refresh(); updateDirty();publish();queueCompute();
  }
  function load(server,working=true) {
    blocked = false;workingBlocked=false; draft = blank(server); saved = null;
    const defaults=service.defaults?service.defaults(server):{};if(defaults.tier)draft.tier=defaults.tier;
    try {
      const value = storage.read(server);
      if (value) { draft = value; saved = clone(value); }
    } catch (e) { blocked = true; error = e.message; }
    refresh();
    if(!saved&&!blocked&&defaults.selectAllOnFirstLoad){draft.cars=model.cars.map(c=>c.id);refresh();}
    profileBase=saved?clone(saved):clone(draft);
    if(working&&storage.readWorking&&!blocked)try{const value=storage.readWorking(server,saved);if(value){draft=value;refresh();}}catch(e){workingBlocked=true;error=e.message;}
    updateDirty();
  }
  function save() {
    if (blocked) { error = '本机原记录无法恢复，未覆盖；请先检查存储'; publish(); return false; }
    try { storage.write(draft.server, draft,saved); saved = clone(draft);profileBase=clone(draft);workingBlocked=false; dirty = false; error = '';if(storage.clearWorking)try{storage.clearWorking(draft.server);}catch(_){error='车库已保存，但临时草稿未清理';}publish(); return true; }
    catch (e) { error = '保存失败，当前选择仍保留：'+e.message; dirty = true; publish(); return false; }
  }
  function stageWorking() {
    if(blocked||workingBlocked)return false;
    try{if(storage.writeWorking)storage.writeWorking(draft.server,draft,saved);return true;}
    catch(e){error='临时草稿保存失败，当前选择仍保留';publish();return false;}
  }
  async function compute() {
    if (busy) return;
    if (!draft.maps.some(x => x && x.small)) {result=null;error='';publish();return;}
    invalidate(); const ticket = epoch; busy = true; error = ''; publish();
    try {
      const value = await service.calculate(clone(draft));
      if (ticket === epoch && visible) result = value;
    } catch (e) { if (ticket === epoch) error = e.message; }
    finally { if (ticket === epoch) { busy = false; publish(); } }
  }
  async function chooseImage() {
    if (draft.server !== 'cn') { error = '国际服暂未开放识图'; publish(); return; }
    invalidate(false,false,true); const ticket = mediaEpoch; error = ''; publish();
    try {
      const value = await media.choose();
      if (ticket !== mediaEpoch || !value) return;
      image = value; publish();if(service.autoRecognize&&visible)void recognize();
    } catch (e) { if (ticket === mediaEpoch) { error = e.message; publish(); } }
  }
  function acceptRecognition(value) {
    if(value.server!==draft.server||value.version!==model.version||!Array.isArray(value.slots)||value.slots.length!==5)throw Error('识别结果目录已变化，请重试');
    pending=value.slots.map(x=>x&&model.maps.some(m=>m.big===x.big&&m.small===x.small)?x:null);
  }
  async function recognize(retry=false) {
    if (!image || busy || draft.server !== 'cn') return;
    if(retry){epoch++;pending=null;}else invalidate(false,false,true);
    const ticket = epoch, version = model.version;
    busy = true; error = ''; publish();
    try {
      const value = await (retry?service.retryRecognition():service.recognize({ ...image, server: draft.server, version }));
      if (ticket !== epoch || !visible) return;
      acceptRecognition(value);
    } catch (e) { if (ticket === epoch) error = e.message; }
    finally { if (ticket === epoch) { busy = false; publish(); } }
  }
  load('cn'); publish();queueCompute();
  return {
    setProfile(value) {change(()=>{draft.cars=[...(value?.cars||[])];draft.stars={...(value?.stars||{})};draft.oc={...(value?.ocMap||{})};});},
    save, compute, chooseImage, recognize,retryRecognition:()=>recognize(true),
    async reconnect() {if(!service.reconnect)return;invalidate();error='';busy=true;publish();const ticket=epoch;try{await service.reconnect();if(ticket===epoch)refresh();}catch(e){if(ticket===epoch)error=e.message;}finally{if(ticket===epoch){busy=false;publish();}}},
    setMode(zone, tier) { change(() => { draft.zone = zone; draft.tier = tier; }); },
    setMap(index, map) {
      if (!Number.isInteger(index) || index < 0 || index > 4) return;
      if (map && draft.maps.some((x, i) => i !== index && x && x.big === map.big)) {
        error = '大地图不能重复'; publish(); return;
      }
      change(() => { draft.maps[index] = map; });
    },
    setCar(id, selected) { if (model.cars.some(x => x.id === id)) change(() => {
      draft.cars = draft.cars.filter(x => x !== id); if (selected) draft.cars.push(id);
    }); },
    setCars(ids,selected) {const targets=new Set(ids.filter(id=>model.cars.some(c=>c.id===id)));change(()=>{const next=new Set(draft.cars);for(const id of targets)if(selected)next.add(id);else next.delete(id);draft.cars=[...next];});},
    setStars(id, stars) { if (model.cars.some(x => x.id === id && x.stars.includes(stars))) change(() => { draft.stars[id] = stars; }); },
    setOc(id, value) { if (model.cars.some(x => x.id === id && x.ocAllowed)) change(() => { draft.oc[id] = value === true; }); },
    setRoute(key, value) {
      const route = (model.routes || []).find(x=>x.key===key);
      if (route && (value==='off' || value==='all' || route.types.includes(value))) change(()=>{draft.routes[key]=value;});
    },
    restore() {
      const current={maps:clone(draft.maps),zone:draft.zone,tier:draft.tier,routes:clone(draft.routes)};
      try{if(storage.clearWorking)storage.clearWorking(draft.server);}catch(e){error='恢复失败，当前选择仍保留';publish();return;}
      invalidate();error='';load(draft.server,false);Object.assign(draft,current);refresh();
      updateDirty();publish();queueCompute();
    },
    switchServer(server) {
      if (!['cn', 'global'].includes(server) || server === draft.server) return;
      if (!stageWorking()) return;
      invalidate(); image = null; error = ''; load(server); publish();queueCompute();
    },
    correctSlot(index, value) {
      if (!pending || index < 0 || index > 4) return;
      pending[index] = value; publish();
    },
    applyRecognition() {
      if (!pending || pending.some(x => !x || !model.maps.some(m => m.big === x.big && m.small === x.small)) || new Set(pending.map(x => x.big)).size !== 5) {
        error = '请补齐五张不同大地图'; publish(); return;
      }
      const maps = clone(pending),ticket=epoch;
      const apply=()=>{if(ticket!==epoch)return;change(()=>{draft.maps=maps;});image=null;publish();};
      if(service.verifyRecognition){busy=true;publish();return service.verifyRecognition().then(apply).catch(e=>{if(ticket===epoch){error=e.message;busy=false;publish();}});}
      apply();
    },
    cancelRecognition() { invalidate(false,false,true); image = null; publish(); },
    stopRecognition() {invalidate(false,false,true);publish();},
    hide() { visible = false; invalidate(true,true,true); stageWorking(); },
    async show() {
      visible = true; const ticket = ++epoch;
      try { const value=await service.resume(); if (ticket === epoch) { refresh();if(value&&draft.server==='cn')acceptRecognition(value);publish();if(!value)queueCompute(); } }
      catch (e) { if (ticket === epoch) { error = e.message;refresh();publish(); } }
    },
    destroy() { visible = false; invalidate(); image = null; }
  };
}
module.exports = { createController, blank };
