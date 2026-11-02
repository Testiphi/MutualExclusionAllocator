'use strict';
const { createController } = require('../../lib/controller');
const { createStorage } = require('../../adapters/storage');
const { createMedia } = require('../../adapters/media');
const { createMock } = require('../../services/mock');
const { createLocalService } = require('../../services/local');
const bundle = require('../../generated/local-bundle');
const core = require('../../shared/selection_core');

Page({
  data: { ready:false, garageOpen: false, query: '', rows: [], cars: [], schemes: [], slotRows: [], schemeIndex:0, activeScheme:null },
  onLoad() {
    // Local bundle is byte-verified. This path never logs in or connects a server.
    let service;
    try { service = bundle ? createLocalService(core,bundle) : createMock(); }
    catch (e) { this.setData({error:e.message,ready:false}); return; }
    this.routeMemory = {};
    this.controller = createController({ service, storage: createStorage(wx, service.mode),
      media: createMedia(wx), render: state => { this.state = state; this.updateView(); } });
  },
  updateView() {
    const s = this.state, d = s.draft, m = s.model;
    const bigs = [...new Set(m.maps.map(x => x.big))];
    const row = (map, index) => {
      const big = map && map.big || '', small = map && map.small || '';
      const options = m.maps.filter(x => x.big === big).map(x => x.small);
      return { index, big, small, bigs: ['选择大地图'].concat(bigs),
        bigIndex: bigs.indexOf(big) + 1, smalls: ['选择小地图'].concat(options),
        smallIndex: options.indexOf(small) + 1 };
    };
    const q = (this.data.query || '').trim().toLowerCase();
    const cars = m.cars.filter(x => !q || (x.label + ' ' + x.id).toLowerCase().includes(q))
      .map(x => ({ ...x, selected: d.cars.includes(x.id), starIndex: x.stars.indexOf(x.stars.includes(d.stars[x.id]) ? d.stars[x.id] : x.defaultStar),
        oc: d.oc[x.id] === true }));
    const routes = (m.routes || []).map(x=>{
      const saved = d.routes[x.key], value = saved === 'off' ? 'off' : x.types.includes(saved) ? saved : 'all';
      return {...x, enabled:value!=='off', showTypes:value!=='off'&&x.types.length>1, options:['全部'].concat(x.types), optionIndex:value==='all'||value==='off'?0:x.types.indexOf(value)+1};
    });
    const schemes = s.result ? s.result.schemes.map((scheme,index)=>({
      index,totalText:scheme.total==null?'—':scheme.total.toFixed(3)+'秒',
      rows:scheme.rows.map((r,i)=>({index:i,map:r.map||'未选地图',big:d.maps[i]&&d.maps[i].big||'',
        car:r.car||'未分配',empty:r.car==null,timeText:r.time==null?'—':r.time.toFixed(3)+'秒'}))
    })) : [];
    const schemeIndex=this.lastResult===s.result && this.data.schemeIndex<schemes.length?this.data.schemeIndex:0;
    this.lastResult=s.result;
    this.setData({ ready:true, server: d.server, mode: s.mode, error: s.error, busy: s.busy,
      dirty: s.dirty, image: s.image, hasPending: !!s.pending,
      selectedCount: d.cars.length, zones: m.zones.map(x => x === 'zone4' ? '四区' : '五区'),
      zoneIndex: m.zones.indexOf(d.zone), tiers: m.tiers, tierIndex: m.tiers.indexOf(d.tier),
      rows: d.maps.map(row), cars, routes, slotRows: s.pending ? s.pending.map(row) : [],
      schemes,schemeIndex,schemeOptions:schemes.map(x=>'方案 '+(x.index+1)),activeScheme:schemes[schemeIndex]||null });
  },
  onShow() { if (this.controller) this.controller.show(); },
  onHide() { if (this.controller) this.controller.hide(); },
  onUnload() { if (this.controller) this.controller.destroy(); },
  switchServer(e) { this.controller.switchServer(e.currentTarget.dataset.server); },
  selectZone(e) { const i=e.currentTarget&&e.currentTarget.dataset.index;this.controller.setMode(this.state.model.zones[Number(i==null?e.detail.value:i)],this.state.draft.tier); },
  selectTier(e) { const i=e.currentTarget&&e.currentTarget.dataset.index;this.controller.setMode(this.state.draft.zone,this.state.model.tiers[Number(i==null?e.detail.value:i)]); },
  selectScheme(e) { const index=Number(e.detail.value);if(Number.isInteger(index)&&this.data.schemes[index])this.setData({schemeIndex:index,activeScheme:this.data.schemes[index]}); },
  selectMap(e) {
    const { index, field, pending } = e.currentTarget.dataset;
    const target = pending ? this.state.pending : this.state.draft.maps;
    const previous = target[index];
    let map = null;
    if (field === 'big') {
      const bigs = [...new Set(this.state.model.maps.map(x => x.big))];
      const big = bigs[Number(e.detail.value) - 1];
      // A big selection is kept until its small map is selected.
      if (big) map = { big, small: '' };
    } else if (previous) {
      const options = this.state.model.maps.filter(x => x.big === previous.big);
      map = options[Number(e.detail.value) - 1] || { big: previous.big, small: '' };
    }
    if (pending) this.controller.correctSlot(Number(index), map);
    else this.controller.setMap(Number(index), map);
  },
  toggleGarage() { this.setData({ garageOpen: !this.data.garageOpen }); },
  search(e) { this.setData({ query: e.detail.value }); this.updateView(); },
  toggleCar(e) {
    const id = e.currentTarget.dataset.id;
    this.controller.setCar(id, !this.state.draft.cars.includes(id));
  },
  selectStars(e) {
    const id = e.currentTarget.dataset.id, car = this.state.model.cars.find(x => x.id === id);
    this.controller.setStars(id, car.stars[Number(e.detail.value)]);
  },
  toggleOc(e) { const id=e.currentTarget.dataset.id;this.controller.setOc(id,e.detail&&typeof e.detail.value==='boolean'?e.detail.value:!this.state.draft.oc[id]); },
  toggleRoute(e) {
    const key=e.currentTarget.dataset.key, value=this.state.draft.routes[key];
    const memoryKey=this.state.draft.server+':'+key;
    if(value==='off') {
      const route=this.state.model.routes.find(x=>x.key===key), remembered=this.routeMemory[memoryKey];
      this.controller.setRoute(key,route.types.includes(remembered)?remembered:'all');
    } else {
      this.routeMemory[memoryKey]=value||'all'; this.controller.setRoute(key,'off');
    }
  },
  selectRoute(e) {
    const key=e.currentTarget.dataset.key, route=this.state.model.routes.find(x=>x.key===key);
    this.controller.setRoute(key, Number(e.detail.value)===0?'all':route.types[Number(e.detail.value)-1]);
  },
  save() { this.controller.save(); }, restore() { this.controller.restore(); },
  compute() { this.controller.compute(); }, chooseImage() { this.controller.chooseImage(); },
  recognize() { this.controller.recognize(); }, applyRecognition() { this.controller.applyRecognition(); },
  cancelRecognition() { this.controller.cancelRecognition(); }
});
