'use strict';
const { createController } = require('../../lib/controller');
const { createStorage } = require('../../adapters/storage');
const { createMedia } = require('../../adapters/media');
const { createMock } = require('../../services/mock');
const { createLocalService } = require('../../services/local');
const bundle = require('../../generated/local-bundle');
const core = require('../../shared/selection_core');
const nativeConfig=require('../../generated/native-config');
const {createNativeService}=require('../../services/native');
const {visibleCars}=require('../../lib/garage_view');

Page({
  data: { ready:false, garageOpen: false, query: '', rows: [], cars: [], schemes: [], slotRows: [], schemeIndex:0, activeScheme:null, dropdown:null,sortMode:'alpha',carClass:'',classes:['','R','S','A','B','C','D'] },
  onLoad() {
    this.unloaded=false;this.routeMemory={};
    if(nativeConfig.enabled){this.connectNative();return;}
    // Local bundle is byte-verified. This path never logs in or connects a server.
    let service;
    try { service = bundle ? createLocalService(core,bundle) : createMock(); }
    catch (e) { this.setData({error:e.message,ready:false}); return; }
    this.mountService(service);
  },
  mountService(service) {
    this.service=service;this.setData({connectionFailed:false});
    this.controller = createController({ service, storage: createStorage(wx, service.mode),
      media: createMedia(wx), render: state => { this.state = state; this.updateView(); } });
  },
  async connectNative() {
    this.setData({initializing:true,error:''});
    try{const service=await createNativeService(wx,core,nativeConfig);if(!this.unloaded)this.mountService(service);else service.cancel();}
    catch(e){if(!this.unloaded)this.setData({error:e.message,nativeDiagnostic:e.nativeReason||'',connectionFailed:true});}
    finally{if(!this.unloaded)this.setData({initializing:false});}
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
    const viewKey='racepick.mini.view.v1.'+s.mode+'.'+d.server;
    if(this.lastViewKey!==viewKey){this.lastViewKey=viewKey;let saved;try{saved=wx.getStorageSync(viewKey);}catch(_){}this.setData({sortMode:saved&&['alpha','score-desc','score-asc'].includes(saved.sortMode)?saved.sortMode:'alpha',carClass:saved&&this.data.classes.includes(saved.carClass)?saved.carClass:''});}
    const cars = visibleCars(m.cars,this.data.query,this.data.carClass,this.data.sortMode)
      .map((x,index) => ({ ...x, index,selected: d.cars.includes(x.id), starIndex: x.stars.indexOf(x.effectiveStar|| (x.stars.includes(d.stars[x.id]) ? d.stars[x.id] : x.defaultStar)),
        oc: d.oc[x.id] === true }));
    const routes = (m.routes || []).map(x=>{
      const saved = d.routes[x.key], value = saved === 'off' ? 'off' : x.types.includes(saved) ? saved : 'all';
      return {...x, enabled:value!=='off', showTypes:value!=='off'&&x.types.length>1, options:['全部'].concat(x.types), optionIndex:value==='all'||value==='off'?0:x.types.indexOf(value)+1};
    });
    const schemes = s.result ? s.result.schemes.map((scheme,index)=>({
      index,prioritySum:scheme.prioritySum,totalText:scheme.total==null?'—':scheme.total.toFixed(3)+'秒',
      rows:scheme.rows.map((r,i)=>({index:i,map:r.map||'未选地图',big:d.maps[i]&&d.maps[i].big||'',
        car:r.car||'未分配',empty:r.car==null,timeText:r.time==null?'—':r.time.toFixed(3)+'秒'}))
    })) : [];
    const schemeIndex=this.lastResult===s.result && this.data.schemeIndex<schemes.length?this.data.schemeIndex:0;
    this.lastResult=s.result;
    this.closeDropdown();
    this.setData({ ready:true, server: d.server, mode: s.mode, error: s.error, busy: s.busy,
      dirty: s.dirty, image: s.image, hasPending: !!s.pending,
      selectedCount: m.cars.filter(c=>d.cars.includes(c.id)).length,serviceStatus:s.serviceStatus,sortLabel:({'alpha':'字母','score-desc':'分↓','score-asc':'分↑'})[this.data.sortMode],zones: m.zones.map(x => x === 'zone4' ? '四区' : '五区'),
      zoneIndex: m.zones.indexOf(d.zone), tiers: m.tiers, tierIndex: m.tiers.indexOf(d.tier),
      rows: d.maps.map(row), cars, routes, slotRows: s.pending ? s.pending.map(row) : [],
      schemes,schemeIndex,schemeOptions:schemes.map(x=>'方案'+(x.index+1)+' · '+x.rows.map((r,i)=>r.big?(i+1)+':'+(r.empty?'空':r.car):'').filter(Boolean).join(' ')+' · Σ='+(x.prioritySum==null?'—':x.prioritySum)),activeScheme:schemes[schemeIndex]||null });
  },
  onShow() { if (this.controller) this.controller.show(); },
  onHide() { this.closeDropdown();if (this.controller) this.controller.hide(); },
  onUnload() { this.unloaded=true;this.closeDropdown();if (this.controller) this.controller.destroy(); },
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
    const row=(review?this.data.slotRows:this.data.rows)[index];
    const labels=field==='big'?row.bigs:row.smalls,selected=field==='big'?row.bigIndex:row.smallIndex;
    const options=labels.map((label,value)=>({label,value,selected:value===selected,
      disabled:field==='big'&&value>0&&target.some((m,i)=>i!==index&&m&&m.big===label)}));
    const id=(review?'review-':'')+'map-'+index+'-'+field;
    this.presentMenu({index,field,pending:review,options},id);
  },
  presentMenu(menu,id) {
    this.closeDropdown();const ticket=this.dropdownGeneration,options=menu.options;
    const info=typeof wx.getWindowInfo==='function'?wx.getWindowInfo():wx.getSystemInfoSync();
    wx.createSelectorQuery().select('#'+id).boundingClientRect(rect=>{
      if(!rect||ticket!==this.dropdownGeneration)return;
      const width=Math.min(Math.max(rect.width,160),info.windowWidth-24);
      const below=info.windowHeight-rect.bottom-12,above=rect.top-12;
      const upwards=below<180&&above>below;
      const maxHeight=Math.min(260,options.length*44,Math.max(44,(upwards?above:below)-10));
      const left=Math.max(12,Math.min(rect.left,info.windowWidth-width-12));
      const top=upwards?Math.max(12,rect.top-maxHeight-14):rect.bottom+4;
      this.setData({dropdown:{...menu,left,top,width,maxHeight,scrollTo:'dropdown-option-'+Math.max(0,options.findIndex(x=>x.selected))}});
    }).exec();
  },
  chooseDropdown(e) {
    const menu=this.data.dropdown,value=Number(e.currentTarget.dataset.value);
    if(!menu||!Number.isInteger(value)||!menu.options[value]||menu.options[value].disabled)return;
    this.closeDropdown();
    if(menu.field==='stars'){this.selectStars({currentTarget:{dataset:{id:menu.carId}},detail:{value}});return;}
    if(menu.field==='scheme'){this.selectScheme({detail:{value}});return;}
    if(menu.field==='route'){this.selectRoute({currentTarget:{dataset:{key:menu.routeKey}},detail:{value}});return;}
    this.selectMap({currentTarget:{dataset:{index:menu.index,field:menu.field,pending:menu.pending}},detail:{value}});
  },
  openStars(e) {const car=this.data.cars.find(c=>c.id===e.currentTarget.dataset.id);if(car)this.presentMenu({field:'stars',carId:car.id,options:car.stars.map((n,i)=>({label:'★'+n,value:i,selected:i===car.starIndex}))},'star-'+e.currentTarget.dataset.anchor);},
  openScheme() {this.presentMenu({field:'scheme',options:this.data.schemeOptions.map((label,i)=>({label,value:i,selected:i===this.data.schemeIndex}))},'scheme-trigger');},
  openRoute(e) {const route=this.data.routes[e.currentTarget.dataset.index];if(route)this.presentMenu({field:'route',routeKey:route.key,options:route.options.map((label,i)=>({label,value:i,selected:i===route.optionIndex}))},'route-'+e.currentTarget.dataset.index);},
  selectAll() {this.controller.setCars(this.data.cars.map(c=>c.id),true);},
  clearAll() {this.controller.setCars(this.state.model.cars.map(c=>c.id),false);},
  saveView() {try{wx.setStorageSync(this.lastViewKey,{sortMode:this.data.sortMode,carClass:this.data.carClass});}catch(_){}},
  cycleSort() {const cycle=['alpha','score-desc','score-asc'];this.setData({sortMode:cycle[(cycle.indexOf(this.data.sortMode)+1)%3]});this.saveView();this.updateView();},
  filterClass(e) {this.setData({carClass:e.currentTarget.dataset.value||''});this.saveView();this.updateView();},
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
  save() { this.controller.save(); }, restore() {
    if(this.state.dirty&&typeof wx.showModal==='function')wx.showModal({title:'恢复已保存车库',content:'放弃当前临时车辆和星级，恢复已保存车库？当前地图不会改变。',success:r=>{if(r.confirm)this.controller.restore();}});
    else this.controller.restore();
  },
  compute() { this.controller.compute(); }, chooseImage() { this.controller.chooseImage(); },
  reconnect() {return this.controller?this.controller.reconnect():this.connectNative();},
  retryRecognition() {return this.controller.retryRecognition();},
  recognize() { this.controller.recognize(); }, applyRecognition() { this.controller.applyRecognition(); },
  cancelRecognition() { this.controller.cancelRecognition(); }
});
