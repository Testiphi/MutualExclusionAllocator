'use strict';
const { createController } = require('../../lib/controller');
const { createStorage } = require('../../adapters/storage');
const { createMedia } = require('../../adapters/media');
const { createMock } = require('../../services/mock');
const { createLocalService } = require('../../services/local');
const bundle = require('../../generated/local-bundle');
const core = require('../../shared/selection_core');
const nativeConfig=require('../../generated/native-config');
const accountConfig=require('../../generated/account-config');
const buildInfo=require('../../generated/build-info');
const {createNativeService}=require('../../services/native');
const {createNativeApi}=require('../../adapters/native_api');
const {visibleCars,garageClasses}=require('../../lib/garage_view');
const runtime=require('../../services/runtime');
const {conflictView}=require('../../services/profile_conflict');
const {createAcceptanceReport}=require('../../services/account_acceptance_report');

Page({
  data: { buildId:buildInfo.buildId,planId:buildInfo.planId||'',writeAcceptance:accountConfig.allowCloudWrites===true&&accountConfig.mode!=='production-a',formalWriteCandidate:accountConfig.allowCloudWrites===true&&accountConfig.mode==='production-a',readbackAcceptance:!!accountConfig.readbackReceipt,conflictAcceptance:!!accountConfig.conflictRole,ready:false, garageOpen: true, query: '', rows: [], cars: [], schemes: [], slotRows: [], schemeIndex:0, activeScheme:null, dropdown:null,sortMode:'alpha',carClass:'',classes:['','R','S','A','B','C','D'] },
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
    this.baseService=service;
    this.account=runtime.mount(wx,nativeConfig,service,accountConfig);
    const policy=runtime.policy();
    this.setData({accountAvailable:!!this.account,accountRestricted:policy.restricted,registrationAvailable:!!this.account&&(!policy.restricted||policy.registration===true),allowCloudWrites:policy.allowCloudWrites});
    if(this.account){this.unsubscribeAccount=this.account.subscribe(s=>{const id=s.actor?.id||'',generation=this.account.generation();this.setData({actor:s.actor});if(id!==this.lastAccountActor||generation!==this.lastAccountGeneration){this.lastAccountActor=id;this.lastAccountGeneration=generation;this.setData({schemes:[],activeScheme:null,cars:[],selectedCount:0,cloudConflict:null,cloudEmpty:false,cloudLoaded:false,unreadCounts:{},homeNickname:'',homeHub:null});this.cloudReady=false;this.lastCloudProfile=null;if(this.homeVisible&&this.controller&&!this.refreshingAccount)void this.syncAccount();}});}
    this.mountController(service);
    if(this.account)void runtime.usage()?.visit('home',this.state.draft.server,'open');
  },
  mountController(service,actorId='') {
    if(this.controller){this.controller.hide();this.controller.destroy();}
    this.service=service;this.setData({connectionFailed:false});
    this.controller = createController({ service:actorId?{...service,defaults:s=>({...service.defaults(s),selectAllOnFirstLoad:false})}:service, storage: createStorage(runtime.storageWx(wx,buildInfo.storageScope), service.mode,actorId?runtime.origin()+'|'+actorId:''),autoCompute:true,
      media: createMedia(wx,{confirmUpload:service.mode==='native'}), render: state => { this.state = state; this.updateView(); } });
  },
  async syncAccount(force=false) {
    if(!this.account||!this.controller)return;
    const state=this.account.state(),id=state.actor?.id||'',server=this.state.draft.server;
    this.setData({actor:state.actor});
    if(this.cloudActor===id&&this.cloudServer===server&&this.cloudReady&&force!==true)return;
    const ticket=(this.cloudTicket||0)+1;this.cloudTicket=ticket;this.cloudReady=false;this.cloud=null;
    if(this.cloudActor!==id){const maps=this.state.draft.maps,zone=this.state.draft.zone,tier=this.state.draft.tier;this.mountController(this.baseService,id);if(this.state.draft.server!==server)this.controller.switchServer(server);this.controller.setMode(zone,tier);maps.forEach((m,i)=>this.controller.setMap(i,m));}
    this.cloudActor=id;this.cloudServer=server;
    if(!id){this.setData({cloudStatus:'',cloudConflict:null});return;}
    this.setData({cloudStatus:'正在读取账号车库…',cloudConflict:null,cloudLoaded:false,cloudEmpty:false});
    try {const cloud=runtime.cloudProfile(wx,server,s=>{if(ticket===this.cloudTicket)this.setData({cloudDirty:s.dirty,cloudStatus:s.error||({saved:'账号车库读取完成',unsaved:'账号车库尚未保存',saving:'正在保存…',conflict:'车库冲突，请选择如何处理'})[s.status]||s.status});},{reload:force===true});
     await cloud.init();if(ticket!==this.cloudTicket||this.account.state().actor?.id!==id)return;
     this.cloud=cloud;this.applyingCloud=true;this.controller.setProfile(cloud.snapshot());this.applyingCloud=false;this.lastCloudProfile=JSON.stringify(this.currentProfile());this.cloudReady=true;this.setData({cloudStatus:cloud.state().dirty?'账号临时修改已保留':cloud.remote()?.profile===null?'账号尚未保存此服车库':'已读取账号车库'});
     this.setData({cloudLoaded:true,cloudDirty:cloud.state().dirty,cloudEmpty:cloud.remote()?.profile===null,cloudConflict:conflictView(cloud.conflict())||(cloud.state().status==='conflict'?{local:cloud.snapshot(),remote:cloud.remote()?.profile}:null)});
    }catch(e){if(ticket===this.cloudTicket){if(e.code==='PROFILE_RECOVERY_REQUIRED'&&this.account.state().actor?.id===id){this.cloud=runtime.cloudProfile(wx,server);this.cloudReady=true;this.applyCloud();}this.setData({cloudStatus:e.message});}}
  },
  accountDiagnostics(){return runtime.diagnostics();},
  acceptanceReport(){if(!buildInfo.planId||!runtime.policy().restricted||!runtime.policy().restricted)throw Error('当前不是独立验收工程');let device={};try{device=wx.getSystemInfoSync();}catch(_){}const state=this.account?.state()||{};return createAcceptanceReport({build:buildInfo,device,account:{...state,pendingAuth:!!this.account?.pendingAuth()},diagnostics:runtime.diagnostics(),ocr:buildInfo.ocrBinding?this.service?.diagnostics?.():null,profiles:runtime.profileStates(),view:{server:this.state?.draft.server,selectedCount:this.data.selectedCount,mappedSlots:this.state?.draft.maps.filter(m=>m?.small).length,schemeCount:this.data.schemes?.length,selection:this.state?.draft,maps:this.state?.draft.maps}});},
  copyAcceptanceReport(){try{wx.setClipboardData({data:JSON.stringify(this.acceptanceReport(),null,2)});}catch(_){this.setData({cloudStatus:'验收报告暂不可复制，请保留当前页面'});}},
  currentProfile(){const d=this.state.draft;return {cars:[...d.cars],stars:{...d.stars},...(d.server==='global'?{ocMap:{...d.oc}}:{})};},
  observeCloud(){if(this.cloudReady&&this.cloud&&!this.applyingCloud){const p=this.currentProfile(),key=JSON.stringify(p);if(key!==this.lastCloudProfile){this.lastCloudProfile=key;this.cloud.update(p);}}},
  async connectNative(restart=false) {
    if(this.nativeConnectFlight)return this.nativeConnectFlight;
    const work=(async()=>{this.setData({initializing:true,error:''});
    try{this.nativeApi=this.nativeApi||createNativeApi(wx,nativeConfig);if(restart)await this.nativeApi.reconnectSession();const service=await createNativeService(wx,core,nativeConfig,{api:this.nativeApi,fixedBinding:buildInfo.ocrBinding});if(!this.unloaded)this.mountService(service);else service.cancel();}
    catch(e){if(!this.unloaded)this.setData({error:e.message,nativeDiagnostic:e.nativeReason||'',connectionFailed:true});}
    finally{if(!this.unloaded)this.setData({initializing:false});}})();
    this.nativeConnectFlight=work;try{return await work;}finally{if(this.nativeConnectFlight===work)this.nativeConnectFlight=null;}
  },
  updateView() {
    this.observeCloud();
    const s = this.state, d = s.draft, m = s.model;
    const bigs = [...new Set(m.maps.map(x => x.big))];
    this.topKeys=this.topKeys||{};this.topOpen=this.topOpen||{};
    const row = (map, index,review=false) => {
      const big = map && map.big || '', small = map && map.small || '';
      const options = m.maps.filter(x => x.big === big).map(x => x.small);
      const top=!review&&(m.topCars||[]).find(t=>t.index===index);
      if(!review){const key=d.server+':'+big+'/'+small;if(this.topKeys[index]!==key){this.topKeys[index]=key;this.topOpen[index]=false;}}
      return { index, big, small,top:top||null,topOpen:!review&&this.topOpen[index],bigs: ['选择大地图'].concat(bigs),
        bigIndex: bigs.indexOf(big) + 1, smalls: ['选择小地图'].concat(options),
        smallIndex: options.indexOf(small) + 1 };
    };
    const scope=runtime.scope()||buildInfo.storageScope;
    const viewKey=(scope?scope+'.':'')+'racepick.mini.view.v1.'+s.mode+'.'+d.server;
    const classes=garageClasses(d.server);
    if(this.lastViewKey!==viewKey){this.lastViewKey=viewKey;let saved;try{saved=wx.getStorageSync(viewKey);}catch(_){}this.setData({sortMode:saved&&['alpha','score-desc','score-asc'].includes(saved.sortMode)?saved.sortMode:'alpha',carClass:classes.includes(saved?.carClass)?saved.carClass:'',classes});}
    const sourceCars=this.service.garageView?this.service.garageView(d,(this.data.query||'').trim(),this.data.carClass,this.data.sortMode).map(id=>m.cars.find(c=>c.id===id)).filter(Boolean):visibleCars(m.cars,this.data.query,this.data.carClass,this.data.sortMode);
    const cars = sourceCars
      .map((x,index) => ({ ...x, index,selected: d.cars.includes(x.id), starIndex: x.stars.indexOf(x.effectiveStar|| (x.stars.includes(d.stars[x.id]) ? d.stars[x.id] : x.defaultStar)),
        oc: d.oc[x.id] === true }));
    const routes = (m.routes || []).map(x=>{
      const saved = d.routes[x.key], value = saved === 'off' ? 'off' : x.types.includes(saved) ? saved : 'all';
      return {...x, enabled:value!=='off', showTypes:value!=='off'&&x.types.length>1, options:['全部'].concat(x.types), optionIndex:value==='all'||value==='off'?0:x.types.indexOf(value)+1};
    });
    const schemes = s.result ? s.result.schemes.map((scheme,index)=>({
      index,prioritySum:scheme.prioritySum,totalText:scheme.total==null?'—':scheme.total.toFixed(3)+'秒',
      rows:scheme.rows.map((r,i)=>({index:i,map:r.map||('第'+(i+1)+'位'),big:r.map?(d.maps[i]&&d.maps[i].big||''):'未选地图',
        configured:!!r.map,car:r.car||(r.map?'无可用车':'⛔ 未配置'),empty:r.car==null,oc:d.server==='global'&&d.oc[r.car]===true,
        stars:d.tier==='理论'?null:(m.cars.find(c=>c.id===r.car)||{}).effectiveStar,
        hasTime:r.time!=null,timeValue:r.time==null?'':r.time.toFixed(2),timeText:r.time==null?'':r.time.toFixed(2)+' 秒'}))
    })) : [];
    const schemeIndex=this.lastResult===s.result && this.data.schemeIndex<schemes.length?this.data.schemeIndex:0;
    const hasMaps=d.maps.some(map=>map?.big&&map?.small);
    const guidance=!s.error&&!s.busy&&(s.result||!hasMaps)&&this.service.resultGuidance
      ? this.service.resultGuidance(d,schemeIndex) : null;
    this.lastResult=s.result;
    this.closeDropdown();
    this.setData({ ready:true, server: d.server, mode: s.mode, error: s.error, busy: s.busy,
      dirty: s.dirty, image: s.image, hasPending: !!s.pending,ocrBusy:!!s.image&&s.busy,subtitle:m.subtitle||'帕累托最优 · 擂台选车',zoneHint:d.zone==='zone4',
      selectedCount: m.cars.filter(c=>d.cars.includes(c.id)).length,serviceStatus:s.serviceStatus,sortLabel:({'alpha':'字母','score-desc':'分↓','score-asc':'分↑'})[this.data.sortMode],zones: m.zones.map(x => x === 'zone4' ? '四区' : '五区'),
      zoneIndex: m.zones.indexOf(d.zone), tiers: m.tiers, tierIndex: m.tiers.indexOf(d.tier),
      rows: d.maps.map((m,i)=>row(m,i)), cars, routes, slotRows: s.pending ? s.pending.map((m,i)=>row(m,i,true)) : [],
      emptyResultText:hasMaps?'没有可用方案':'请先选择地图',resultGuidance:guidance,
      schemes,schemeIndex,schemeOptions:s.result?s.result.schemes.map((x,i)=>x.summary||('方案'+(i+1)+' · Σ='+x.prioritySum)):[],activeScheme:schemes[schemeIndex]||null });
  },
  async onShow() {this.homeVisible=true;this.refreshingAccount=true;try{if(this.account)await this.account.refresh();}catch(e){this.setData({cloudStatus:e.message});}finally{this.refreshingAccount=false;}if(this.controller){await this.syncAccount((runtime.policy().writeAcceptance||runtime.policy().readbackAcceptance||runtime.policy().conflictAcceptance)?false:true);this.controller.show();if(this.account){void runtime.usage()?.visit('home',this.state.draft.server,'resume');void this.refreshHomeIdentity();}}},
  onHide() {this.homeVisible=false;this.setData({homeHub:null}); this.closeDropdown();if (this.controller) this.controller.hide(); },
  onUnload() { this.unloaded=true;this.cloudTicket=(this.cloudTicket||0)+1;if(this.unsubscribeAccount)this.unsubscribeAccount();this.closeDropdown();if (this.controller) this.controller.destroy();if(this.nativeApi)this.nativeApi.session.invalidate(); },
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
  canEditGarage(){if(this.account?.state().actor&&!this.cloudReady){this.setData({cloudStatus:'账号车库尚未读取，原草稿已保留，请先重试读取'});return false;}return true;},
  selectAll() {if(this.canEditGarage())this.controller.setCars(this.data.cars.map(c=>c.id),true);},
  clearAll() {if(this.canEditGarage())this.controller.setCars(this.state.model.cars.map(c=>c.id),false);},
  saveView() {try{wx.setStorageSync(this.lastViewKey,{sortMode:this.data.sortMode,carClass:this.data.carClass});}catch(_){}},
  cycleSort() {const cycle=['alpha','score-desc','score-asc'];this.setData({sortMode:cycle[(cycle.indexOf(this.data.sortMode)+1)%3]});this.saveView();this.updateView();},
  filterClass(e) {
    const value=e.currentTarget.dataset.value||'';
    if(!garageClasses(this.state.draft.server).includes(value))return;
    this.setData({carClass:value});this.saveView();this.updateView();
  },
  async switchServer(e) {
    const server=e.currentTarget.dataset.server;
    if(server===this.state.draft.server)return;
    this.cloudReady=false;
    const refreshCloud=runtime.policy().productionAccount===true;
    if(refreshCloud&&this.account?.state().actor)this.setData({cloudLoaded:false,cloudEmpty:false});
    this.controller.switchServer(server);
    await this.syncAccount(refreshCloud);
  },
  selectZone(e) { const i=e.currentTarget&&e.currentTarget.dataset.index;this.controller.setMode(this.state.model.zones[Number(i==null?e.detail.value:i)],this.state.draft.tier); },
  selectTier(e) { const i=e.currentTarget&&e.currentTarget.dataset.index;this.controller.setMode(this.state.draft.zone,this.state.model.tiers[Number(i==null?e.detail.value:i)]); },
  selectScheme(e) {
    const index=Number(e.detail.value);
    if(Number.isInteger(index)&&this.data.schemes[index]){this.setData({schemeIndex:index,activeScheme:this.data.schemes[index]});this.updateView();}
  },
  contributeResult() {
    const guidance=this.data.resultGuidance;
    if(!guidance?.canSubmit||this.state.busy||this.state.error)return;
    if(!this.account||runtime.policy().restricted){
      wx.showModal({title:'投稿入口暂不可用',content:'现在还没连上投稿服务，稍后再来试试吧！',showCancel:false});
      return;
    }
    const draft=this.state.draft,binding=JSON.stringify(draft),result=this.state.result,index=this.data.schemeIndex;
    const generation=this.account.generation(),targets=guidance.targetMaps;
    const open=map=>{
      if(this.unloaded||this.state.busy||this.state.error||this.state.result!==result||this.data.schemeIndex!==index||
         JSON.stringify(this.state.draft)!==binding||this.account.generation()!==generation||runtime.policy().restricted)return;
      const app=getApp();
      app.submissionTarget=null;
      app.openSubmission=null;
      app.submissionMapTarget={server:draft.server,big:map.big,small:map.small,zone:draft.zone==='zone4'?'四区':'五区',tier:draft.tier};
      wx.navigateTo({url:'/pages/submissions/submissions?compose=1&server='+draft.server,fail:()=>{app.submissionMapTarget=null;}});
    };
    if(targets.length===1){open(targets[0]);return;}
    wx.showActionSheet({itemList:targets.map(m=>`第${m.originalIndex+1}图 · ${m.big} / ${m.small}`),success:r=>{
      if(Number.isInteger(r.tapIndex)&&targets[r.tapIndex])open(targets[r.tapIndex]);
    }});
  },
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
  toggleTop(e) {const i=Number(e.currentTarget.dataset.index);this.topOpen[i]=!this.topOpen[i];this.updateView();},
  search(e) { this.setData({ query: e.detail.value }); this.updateView(); },
  toggleCar(e) {
    if(!this.canEditGarage())return;
    const id = e.currentTarget.dataset.id;
    this.controller.setCar(id, !this.state.draft.cars.includes(id));
  },
  selectStars(e) {
    if(!this.canEditGarage())return;
    const id = e.currentTarget.dataset.id, car = this.state.model.cars.find(x => x.id === id);
    this.controller.setStars(id, car.stars[Number(e.detail.value)]);
  },
  toggleOc(e) {if(!this.canEditGarage())return;const id=e.currentTarget.dataset.id;if(this.state.draft.cars.includes(id))this.controller.setOc(id,e.detail&&typeof e.detail.value==='boolean'?e.detail.value:!this.state.draft.oc[id]); },
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
  async save() {if(!this.account?.state().actor)return this.controller.save();if(runtime.policy().allowCloudWrites===false){this.setData({cloudStatus:'当前账号车库仅供读取，临时修改已保留'});return;}if(!this.canEditGarage())return;const cloud=this.cloud,ticket=this.cloudTicket;if((runtime.policy().writeAcceptance||runtime.policy().conflictAcceptance)&&!cloud.state().dirty)cloud.update(this.currentProfile());if(runtime.policy().writeAcceptance||runtime.policy().conflictAcceptance)this.setData({cloudSaving:true});try{await cloud.flush();if(ticket===this.cloudTicket&&cloud===this.cloud)this.setData({cloudEmpty:false,cloudConflict:null});}catch(e){if(ticket===this.cloudTicket&&cloud===this.cloud)this.setData({cloudStatus:e.message,cloudConflict:conflictView(cloud.conflict())});}finally{if((runtime.policy().writeAcceptance||runtime.policy().conflictAcceptance)&&ticket===this.cloudTicket&&cloud===this.cloud)this.setData({cloudSaving:false});}},
  async reloadCloud(){if(!(runtime.policy().writeAcceptance||runtime.policy().conflictAcceptance)||!this.cloud||this.data.cloudSaving)return;const cloud=this.cloud,ticket=this.cloudTicket;try{await cloud.reload();if(ticket!==this.cloudTicket||cloud!==this.cloud)return;this.applyCloud();this.setData({cloudEmpty:cloud.remote()?.profile===null,cloudStatus:'已认证重载；请核对验收报告中的 revision 和完整车库'});}catch(e){if(ticket===this.cloudTicket&&cloud===this.cloud)this.setData({cloudStatus:e.message});}},
  restore() {
    if(this.account?.state().actor){if(runtime.policy().writeAcceptance||runtime.policy().readbackAcceptance||runtime.policy().conflictAcceptance){this.setData({cloudStatus:'写验收请使用认证GET重载；原草稿保留'});return;}if(!this.canEditGarage())return;this.confirmCloud('恢复账号车库','放弃本账号的临时车辆、星级及OC修改，加载云端车库？当前地图保留。',cloud=>cloud.useRemote());return;}
    if(this.state.dirty&&typeof wx.showModal==='function')wx.showModal({title:'恢复已保存车库',content:'放弃当前临时车辆和星级，恢复已保存车库？当前地图不会改变。',success:r=>{if(r.confirm)this.controller.restore();}});
    else this.controller.restore();
  },
  applyCloud(){this.applyingCloud=true;this.controller.setProfile(this.cloud.snapshot());this.applyingCloud=false;this.lastCloudProfile=JSON.stringify(this.currentProfile());this.setData({cloudConflict:null});},
  confirmCloud(title,content,action){const cloud=this.cloud,ticket=this.cloudTicket;if(!cloud)return;wx.showModal({title,content,success:async r=>{if(!r.confirm||ticket!==this.cloudTicket||cloud!==this.cloud)return;try{await action(cloud);if(ticket===this.cloudTicket&&cloud===this.cloud)this.applyCloud();}catch(e){if(ticket===this.cloudTicket)this.setData({cloudStatus:e.message});}}});},
  importGarage(){if(runtime.policy().writeAcceptance||runtime.policy().readbackAcceptance||runtime.policy().conflictAcceptance){this.setData({cloudStatus:'游客导入另行验收，本轮保留原游客记录'});return;}if(!this.canEditGarage())return;const server=this.state.draft.server;this.confirmCloud('导入本机游客车库','导入到本账号的临时车库。只有点击保存车库后才会上传；游客记录保留。',cloud=>{const storage=createStorage(runtime.storageWx(wx),this.service.mode),saved=storage.read(server),draft=storage.readWorking(server,saved)||saved;if(!draft)throw Error('本机没有已保存的游客车库');cloud.importGuest({cars:draft.cars,stars:draft.stars,...(server==='global'?{ocMap:draft.oc}:{})});});},
  overwriteCloud(){if(runtime.policy().writeAcceptance||runtime.policy().conflictAcceptance){this.setData({cloudStatus:'冲突两份已保留，本轮停止，不覆盖'});return;}if(runtime.policy().allowCloudWrites===false){this.setData({cloudStatus:'当前服务尚未开放云端保存'});return;}this.confirmCloud('保存本地版本','保留本地车库，以当前最新云端版本为基线再次保存？',cloud=>cloud.overwrite());},
  async recoverCloud(){if(!this.cloud){this.setData({cloudStatus:'请先重试读取账号车库'});return;}const cloud=this.cloud,ticket=this.cloudTicket;try{await cloud.recover();if(ticket===this.cloudTicket)this.setData({cloudStatus:'原保存已确认；后续修改保留。请先核对报告，不继续写；未知结果专项另行核对。'});}catch(e){if(ticket===this.cloudTicket)this.setData({cloudStatus:e.message});}},
  openHub(e){this.closeDropdown();this.setData({homeHub:e.currentTarget.dataset.hub});},
  closeHub(){this.setData({homeHub:null});},
  async refreshHomeIdentity(){if(runtime.policy().restricted||!this.account?.state().actor)return;const ticket=this.account.generation();const values=await Promise.allSettled([this.account.call('/notifications'),this.account.call('/contributions/me?period=month')]);if(ticket!==this.account.generation())return;this.setData({unreadCounts:values[0].status==='fulfilled'?values[0].value.counts:{},homeNickname:values[1].status==='fulfilled'?values[1].value.preference.nickname:''});},
  navigate(e){const {page,mode,tab,compose}=e.currentTarget.dataset;const policy=runtime.policy();if(policy.restricted&&(page!=='account'||mode&&mode!=='login'&&!(mode==='register'&&policy.registration===true&&!this.data.actor))){this.setData({cloudStatus:'当前服务暂未开放此功能'});return;}if(!['account','coverage','submissions','community','workbench'].includes(page))return;this.setData({homeHub:null});wx.navigateTo({url:'/pages/'+page+'/'+page+'?server='+this.state.draft.server+(mode?'&mode='+encodeURIComponent(mode):'')+(tab?'&tab='+encodeURIComponent(tab):'')+(compose?'&compose=1':'')});},
  compute() { this.controller.compute(); }, chooseImage() { this.controller.chooseImage(); },
  reconnect() {return this.controller?this.controller.reconnect():this.connectNative(true);},
  retryRecognition() {return this.controller.retryRecognition();},
  recognize() { this.controller.recognize(); }, applyRecognition() { this.controller.applyRecognition(); },
  cancelRecognition() { this.controller.cancelRecognition(); },
  stopRecognition() {this.controller.stopRecognition();}
});
