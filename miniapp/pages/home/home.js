'use strict';
const { createController } = require('../../lib/controller');
const { createStorage } = require('../../adapters/storage');
const { createMedia } = require('../../adapters/media');
const { createMock } = require('../../services/mock');
const { createLocalService } = require('../../services/local');
const bundle = require('../../generated/local-bundle');
const core = require('../../shared/selection_core');

Page({
  data: { ready:false, garageOpen: false, query: '', rows: [], cars: [], schemes: [], slotRows: [], schemeIndex:0, activeScheme:null, dropdown:null },
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
    this.closeDropdown();
    this.setData({ ready:true, server: d.server, mode: s.mode, error: s.error, busy: s.busy,
      dirty: s.dirty, image: s.image, hasPending: !!s.pending,
      selectedCount: d.cars.length, zones: m.zones.map(x => x === 'zone4' ? '四区' : '五区'),
      zoneIndex: m.zones.indexOf(d.zone), tiers: m.tiers, tierIndex: m.tiers.indexOf(d.tier),
      rows: d.maps.map(row), cars, routes, slotRows: s.pending ? s.pending.map(row) : [],
      schemes,schemeIndex,schemeOptions:schemes.map(x=>'方案 '+(x.index+1)),activeScheme:schemes[schemeIndex]||null });
  },
  onShow() { if (this.controller) this.controller.show(); },
  onHide() { this.closeDropdown();if (this.controller) this.controller.hide(); },
  onUnload() { this.closeDropdown();if (this.controller) this.controller.destroy(); },
  onPageScroll() { this.closeDropdown(); },
  closeDropdown() { this.dropdownGeneration=(this.dropdownGeneration||0)+1;if(this.data.dropdown)this.setData({dropdown:null}); },
  blockDropdownScroll() {},
  openDropdown(e) {
    const {field,pending}=e.currentTarget.dataset,index=Number(e.currentTarget.dataset.index);
    if(!Number.isInteger(index)||index<0||index>4||!['big','small'].includes(field))return;
    const review=pending===true||pending==='true', target=review?this.state.pending:this.state.draft.maps;
    if(!target || (field==='small'&&!target[index]))return;
    const current=this.data.dropdown;
    if(current&&current.index===index&&current.field===field&&current.pending===review){this.closeDropdown();return;}
    this.closeDropdown();const ticket=this.dropdownGeneration;
    const row=(review?this.data.slotRows:this.data.rows)[index];
    const labels=field==='big'?row.bigs:row.smalls,selected=field==='big'?row.bigIndex:row.smallIndex;
    const options=labels.map((label,value)=>({label,value,selected:value===selected,
      disabled:field==='big'&&value>0&&target.some((m,i)=>i!==index&&m&&m.big===label)}));
    const id=(review?'review-':'')+'map-'+index+'-'+field;
    const info=typeof wx.getWindowInfo==='function'?wx.getWindowInfo():wx.getSystemInfoSync();
    wx.createSelectorQuery().select('#'+id).boundingClientRect(rect=>{
      if(!rect||ticket!==this.dropdownGeneration)return;
      const width=Math.min(Math.max(rect.width,160),info.windowWidth-24);
      const below=info.windowHeight-rect.bottom-12,above=rect.top-12;
      const upwards=below<180&&above>below;
      const maxHeight=Math.min(260,options.length*44,Math.max(44,(upwards?above:below)-10));
      const left=Math.max(12,Math.min(rect.left,info.windowWidth-width-12));
      const top=upwards?Math.max(12,rect.top-maxHeight-14):rect.bottom+4;
      this.setData({dropdown:{index,field,pending:review,options,left,top,width,maxHeight,scrollTo:'dropdown-option-'+selected}});
    }).exec();
  },
  chooseDropdown(e) {
    const menu=this.data.dropdown,value=Number(e.currentTarget.dataset.value);
    if(!menu||!Number.isInteger(value)||!menu.options[value]||menu.options[value].disabled)return;
    this.closeDropdown();
    this.selectMap({currentTarget:{dataset:{index:menu.index,field:menu.field,pending:menu.pending}},detail:{value}});
  },
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
