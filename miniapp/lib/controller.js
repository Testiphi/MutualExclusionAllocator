'use strict';
const clone = value => JSON.parse(JSON.stringify(value));
function blank(server) {
  return { schema: 1, server, zone: 'zone5', tier: '理论',
    maps: [null, null, null, null, null], cars: [], stars: {}, oc: {}, routes: {} };
}
function createController({ service, storage, media, render }) {
  let draft = blank('cn'), saved = null, model, epoch = 0, mediaEpoch = 0, visible = true;
  let error = '', busy = false, result = null, pending = null, image = null, dirty = false;
  let blocked = false;
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
      mode: service.mode, storageBlocked: blocked });
  }
  function invalidate(preserveMedia = false) {
    if (!preserveMedia) mediaEpoch++;
    epoch++; busy = false; result = null; pending = null; service.cancel();
  }
  function change(fn) {
    invalidate(); error = '';
    fn(); refresh(); dirty = true; publish();
  }
  function load(server) {
    blocked = false; draft = blank(server); saved = null;
    try {
      const value = storage.read(server);
      if (value) { draft = value; saved = clone(value); }
    } catch (e) { blocked = true; error = e.message; }
    refresh(); dirty = saved !== null && JSON.stringify(draft) !== JSON.stringify(saved);
  }
  function save() {
    if (blocked) { error = '本机原记录无法恢复，未覆盖；请先检查存储'; publish(); return false; }
    try { storage.write(draft.server, draft); saved = clone(draft); dirty = false; error = ''; publish(); return true; }
    catch (e) { error = '保存失败，当前选择仍保留；请检查存储空间'; dirty = true; publish(); return false; }
  }
  async function compute() {
    if (busy) return;
    if (!draft.maps.some(x => x && x.small) || !draft.cars.length) { error = '请先选择地图和车辆'; publish(); return; }
    if (draft.maps.some(x => x && !x.small)) { error = '请补全已选地图'; publish(); return; }
    invalidate(); const ticket = epoch; busy = true; error = ''; publish();
    try {
      const value = await service.calculate(clone(draft));
      if (ticket === epoch && visible) result = value;
    } catch (e) { if (ticket === epoch) error = e.message; }
    finally { if (ticket === epoch) { busy = false; publish(); } }
  }
  async function chooseImage() {
    if (draft.server !== 'cn') { error = '国际服暂未开放识图'; publish(); return; }
    invalidate(); const ticket = mediaEpoch; error = ''; publish();
    try {
      const value = await media.choose();
      if (ticket !== mediaEpoch || !value) return;
      image = value; publish();
    } catch (e) { if (ticket === mediaEpoch) { error = e.message; publish(); } }
  }
  async function recognize() {
    if (!image || busy || draft.server !== 'cn') return;
    invalidate(); const ticket = epoch, version = model.version;
    busy = true; error = ''; publish();
    try {
      const value = await service.recognize({ ...image, server: draft.server, version });
      if (ticket !== epoch || !visible) return;
      if (value.server !== draft.server || value.version !== model.version ||
          !Array.isArray(value.slots) || value.slots.length !== 5) throw Error('识别结果目录已变化，请重试');
      // Unknown/ambiguous slots stay empty. Applying still needs explicit confirmation.
      pending = value.slots.map(x => x && model.maps.some(m => m.big === x.big && m.small === x.small) ? x : null);
    } catch (e) { if (ticket === epoch) error = e.message; }
    finally { if (ticket === epoch) { busy = false; publish(); } }
  }
  load('cn'); publish();
  return {
    save, compute, chooseImage, recognize,
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
    setStars(id, stars) { if (model.cars.some(x => x.id === id && x.stars.includes(stars))) change(() => { draft.stars[id] = stars; }); },
    setOc(id, value) { if (model.cars.some(x => x.id === id && x.ocAllowed)) change(() => { draft.oc[id] = value === true; }); },
    setRoute(key, value) {
      const route = (model.routes || []).find(x=>x.key===key);
      if (route && (value==='off' || value==='all' || route.types.includes(value))) change(()=>{draft.routes[key]=value;});
    },
    restore() { invalidate(); error = ''; load(draft.server); publish(); },
    switchServer(server) {
      if (!['cn', 'global'].includes(server) || server === draft.server) return;
      if (!save()) return;
      invalidate(); image = null; error = ''; load(server); publish();
    },
    correctSlot(index, value) {
      if (!pending || index < 0 || index > 4) return;
      pending[index] = value; publish();
    },
    applyRecognition() {
      if (!pending || pending.some(x => !x || !model.maps.some(m => m.big === x.big && m.small === x.small)) || new Set(pending.map(x => x.big)).size !== 5) {
        error = '请补齐五张不同大地图'; publish(); return;
      }
      const maps = clone(pending); change(() => { draft.maps = maps; }); image = null; publish();
    },
    cancelRecognition() { invalidate(); image = null; publish(); },
    hide() { visible = false; invalidate(true); if (dirty) save(); },
    async show() {
      visible = true; const ticket = ++epoch;
      try { await service.resume(); if (ticket === epoch) { refresh(); publish(); } }
      catch (e) { if (ticket === epoch) { error = e.message; publish(); } }
    },
    destroy() { visible = false; invalidate(); image = null; }
  };
}
module.exports = { createController, blank };
