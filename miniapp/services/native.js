'use strict';
const {createNativeApi}=require('../adapters/native_api');
const {verifyNativeSnapshot}=require('../adapters/snapshot');
const {verifySnapshot}=require('./account_readonly');
const {createRecognitionJobs}=require('./recognition_jobs');
const {requestId}=require('../adapters/id');
const {enrichModel}=require('../lib/garage_view');
const {utf8,sha256}=require('../adapters/hash');
const {createWebHomeAdapter}=require('../lib/home_presenter_adapter');
async function createNativeService(wx,core,config,options={}) {
  const api=options.api||createNativeApi(wx,config);if(api.origin!==config.origin||api.fixture!==(config.kind==='fixture'))throw Error('服务与原生连接配置不一致');let contexts={},snapshots={},known={},home={},online=false,message='',generation=0,lastBinding=null;
  const cacheKey=s=>'racepick.mini.snapshot.v1.'+sha256(utf8(config.origin)).slice(0,16)+'.'+s;
  function checkSnapshot(value,server,identity) {
    if(!options.fixedBinding)return verifyNativeSnapshot(value,server,identity);
    const checked=verifySnapshot(value,server,identity,options.fixedBinding);
    const catalog=server==='cn'?options.fixedBinding.cn_catalog_version:null;
    if(checked.catalogVersion!==catalog||checked.capabilities.map_recognition!==(server==='cn')){
      throw Error('截图提取服务目录与验收版本不一致');
    }
    return checked;
  }
  function commit(checked) {
    const next={},ids={},presenters={};
    for(const server of ['cn','global']){
      const ctx=core.createSelectionContext(checked[server]),base={schema:1,server,zone:'zone5',tier:'理论',maps:[null,null,null,null,null],cars:[],stars:{},oc:{},routes:{}};
      next[server]=ctx;const model=ctx.getModel(base);ids[server]=[...new Set(model.zones.flatMap(zone=>ctx.getModel({...base,zone}).cars.map(c=>c.id)))];
      presenters[server]=createWebHomeAdapter(checked[server],core);
    }
    snapshots=checked;contexts=next;known=ids;home=presenters;
  }
  async function refresh() {
    try {
    await api.session.ensure();const identity=api.identity();
    const values=await Promise.all(['cn','global'].map(async s=>checkSnapshot(await api.snapshot(s),s,identity)));
    if(api.identity()!==identity)throw Error('会话已变化');
    commit({cn:values[0],global:values[1]});online=true;message='';
    for(const v of values)try{wx.setStorageSync(cacheKey(v.server),v.envelope);}catch(_){message='快照缓存未保存，当前仍可计算';}
    }catch(e){online=false;message='连接未完成，已保留原地图与车库';throw e;}
  }
  const binding=()=>({server:'cn',identity:api.identity(),version:snapshots.cn.catalogVersion,catalog:contexts.cn.getModel({schema:1,server:'cn',zone:'zone5',tier:'理论',maps:[null,null,null,null,null],cars:[],stars:{},oc:{},routes:{}}).maps});
  const recognitionEnabled=()=>online&&snapshots.cn.capabilities.map_recognition===true&&/^[a-f0-9]{64}$/.test(snapshots.cn.catalogVersion);
  async function catalog(requireReady=false) {
    if(!online)throw Error('当前离线，识图需要重新连接');
    if(!recognitionEnabled())throw Object.assign(Error('当前服务尚未开放地图识别，仍可手动选图'),{code:'RECOGNITION_DISABLED'});
    const b=binding(),c=await api.catalog();
    if(c.identity!==b.identity||c.server!=='cn'||c.version!==b.version||c.catalog_version!==b.version||JSON.stringify(c.maps)!==JSON.stringify(b.catalog))throw Object.assign(Error('活动目录已变化，请重新连接后识别'),{status:409});
    if(requireReady&&c.worker!=='ready')throw Error('识别服务尚未就绪，仍可手动选图');
    return b;
  }
  const jobs=createRecognitionJobs({api:api.jobs,currentBinding:binding,createKey:()=>requestId(wx)});
  function wrap(value){return {...value,version:snapshots.cn.version,catalog_version:value.version};}
  try{await refresh();}catch(e){
    const cached={};for(const s of ['cn','global'])try{const value=wx.getStorageSync(cacheKey(s));cached[s]=checkSnapshot(value,s,value.identity);}catch(_){}
    if(!cached.cn||!cached.global)throw e;
    commit(cached);online=false;message='离线使用已验证缓存；识图需重新连接';
  }
  return {
    api,mode:api.fixture?'native-fixture':'native',get autoRecognize(){return recognitionEnabled();},diagnostics:()=>({task:jobs.state(),network:api.metrics(),versions:{cn:snapshots.cn.version,global:snapshots.global.version}}),
    defaults:server=>home[server].defaults(),
    garageView:(d,query,cls,sort)=>home[d.server].visible(d,query,cls,sort),
    model:d=>({...enrichModel(contexts[d.server].getModel(d),snapshots[d.server],d,core),knownCarIds:known[d.server],topCars:home[d.server].tops(d),subtitle:home[d.server].subtitle(d)}),
    calculate:d=>home[d.server].calculate(d),
    resultGuidance:(d,index)=>home[d.server].guidance(d,index),
    async recognize(image){const ticket=++generation;lastBinding=await catalog(true);if(ticket!==generation)throw Error('本次识别已停止');return wrap(await jobs.start(image));},
    async retryRecognition(){const b=await catalog();if(!lastBinding||b.identity!==lastBinding.identity||b.version!==lastBinding.version)throw Error('原任务目录已变化');return wrap(await jobs.resume());},
    async verifyRecognition(){const b=await catalog();if(!lastBinding||b.identity!==lastBinding.identity||b.version!==lastBinding.version)throw Error('识别结果已失效，请重新识别');},
    cancel(){generation++;jobs.cancel();lastBinding=null;},
    suspend(){generation++;jobs.suspend();},
    async resume(){await refresh();if(jobs.state().request_key&&['paused','recoverable','finished'].includes(jobs.state().phase)){await catalog();return wrap(await jobs.resume());}},
    async reconnect(){const ticket=++generation,oldIdentity=api.session.current().identity;jobs.suspend();await api.reconnectSession();if(ticket!==generation)throw Error('本次连接已停止');if(oldIdentity&&api.session.current().identity!==oldIdentity){jobs.cancel();lastBinding=null;}await refresh();if(ticket!==generation)throw Error('本次连接已停止');if(jobs.state().request_key){await catalog();return wrap(await jobs.resume());}},
    status(){const state=api.session.current();if((!state.identity||state.expiresAt<=Date.now())&&online){online=false;message='访客会话已失效，请重新连接';}return {online,fixture:api.fixture,message,recognitionEnabled:recognitionEnabled(),canRetry:['paused','recoverable'].includes(jobs.state().phase),task:jobs.state().phase};}
  };
}
module.exports={createNativeService};
