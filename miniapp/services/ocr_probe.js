'use strict';
const {createNativeApi}=require('../adapters/native_api');
const {verifyNativeSnapshot}=require('../adapters/snapshot');
const {utf8,sha256}=require('../adapters/hash');
const {requestId}=require('../adapters/id');
const {createMedia}=require('../adapters/media');
const {createRecognitionJobs}=require('./recognition_jobs');
const fail=(message,code)=>Object.assign(Error(message),{code});
function verifyOcrBinding(cn,global,catalog,expected,identity){
 for(const snapshot of [cn,global]){
  if(snapshot.identity!==identity||snapshot.version!==expected.snapshot_versions[snapshot.server])throw fail('快照身份或固定版本不符','PIN_MISMATCH');
  for(const [name,f] of Object.entries(snapshot.envelope.files)){const p=expected.files[name];if(!p||p.bytes!==f.bytes||p.sha256!==f.sha256)throw fail('原文件与固定交付不符','PIN_MISMATCH');}
 }
 if(!cn.capabilities.map_recognition||cn.catalogVersion!==expected.cn_catalog_version||global.capabilities.map_recognition!==false||global.catalogVersion!==null||global.cars._meta.dataset_version!==expected.global_dataset)throw fail('OCR能力或数据集不符','PIN_MISMATCH');
 const maps=cn.data.tracks.map(t=>({big:t.大地图,small:t.小地图}));
 // Website maps_sha256 uses Python json.dumps(sort_keys=True), including spaces.
 const canonical='['+maps.map(m=>'{"big": '+JSON.stringify(m.big)+', "small": '+JSON.stringify(m.small)+'}').join(', ')+']';
 if(sha256(utf8(cn.version+':'+cn.envelope.files['gauntlet_data.json'].text))!==expected.cn_catalog_version||sha256(utf8(canonical))!==expected.maps_sha256||JSON.stringify(maps)!==JSON.stringify(expected.maps))throw fail('原字节派生目录不符','CATALOG_MISMATCH');
 if(!catalog||catalog.server!=='cn'||catalog.identity!==identity||catalog.version!==expected.cn_catalog_version||catalog.catalog_version!==expected.cn_catalog_version||JSON.stringify(catalog.maps)!==JSON.stringify(maps)||catalog.content_safety!==expected.content_safety||catalog.content_safety!=='required_approval'||catalog.max_bytes!==8388608||catalog.max_pixels!==16000000||catalog.max_envelope_bytes!==8454144||catalog.retention_seconds!==3600)throw fail('目录、安全门禁或限制不符','CATALOG_MISMATCH');
 return {server:'cn',identity,version:catalog.version,catalog:maps};
}
function createOcrProbe(wx,config,expected,permission={maxUploads:0,uploadDomainDeclared:false},jobOptions={}){
 if(config.kind!=='platform'||config.origin!==expected.origin||!Number.isInteger(permission.maxUploads)||permission.maxUploads<0||permission.maxUploads>10)throw fail('检查工程配置无效','CONFIG_INVALID');
 let binding=null,snapshots=null,catalog=null,selection=null,pending=null,consent=false,disposed=false,visible=true,epoch=0,mediaEpoch=0,busy=false,connection=null;
 const applied=[null,null,null,null,null],counts={session:0,cn:0,global:0,catalog:0,uploads:0,queries:0,recoveries:0,cancels:0};let state='idle',errorCode=null,diagnostic=null,httpStatus=null,lastUpload=null;
 function captureFailure(e){httpStatus=Number.isInteger(e.status)?e.status:null;diagnostic=null;const d=e.diagnostic;if(!d)return;const kinds=['response_decode','domain_rejected','tls_or_certificate','dns','timeout','cancelled','file_access','invalid_argument','connection','unknown'];if(!kinds.includes(d.kind))return;diagnostic={kind:d.kind};if(['text','view','arraybuffer','unsupported'].includes(d.responseKind))diagnostic.responseKind=d.responseKind;if(Number.isInteger(d.bytes)&&d.bytes>=0)diagnostic.bytes=d.bytes;if(Number.isInteger(d.nativeCode))diagnostic.nativeCode=d.nativeCode;if(Number.isInteger(d.errno))diagnostic.errno=d.errno;if(lastUpload&&lastUpload.outcome==='native_failure')lastUpload.diagnostic={...diagnostic};}
 const observed=Object.create(wx);
 observed.request=options=>{
  const url=options.url.slice(config.origin.length),method=options.method||'GET';if(!options.url.startsWith(config.origin+'/api/mini/v1/'))throw fail('拒绝非原生入口','ROUTE_DENIED');
  if(url==='/api/mini/v1/session'&&method==='POST')counts.session++;
  else if(method==='GET'&&url==='/api/mini/v1/snapshot?server=cn')counts.cn++;
  else if(method==='GET'&&url==='/api/mini/v1/snapshot?server=global')counts.global++;
  else if(method==='GET'&&url==='/api/mini/v1/map-recognition/catalog?server=cn')counts.catalog++;
  else if(method==='GET'&&new RegExp('^/api/mini/v1/map-recognition/jobs/by-request\\?server=cn&catalog_version='+expected.cn_catalog_version+'&request_key=[a-zA-Z0-9_-]{16,80}$').test(url))counts.recoveries++;
  else if(['GET','DELETE'].includes(method)&&new RegExp('^/api/mini/v1/map-recognition/jobs/[a-f0-9]{32}\\?server=cn&catalog_version='+expected.cn_catalog_version+'$').test(url)){if(method==='GET')counts.queries++;else counts.cancels++;}
  else throw fail('拒绝账号、业务或非固定OCR路径','ROUTE_DENIED');
  return wx.request(options);
 };
 observed.uploadFile=options=>{
  if(!permission.uploadDomainDeclared||!consent||counts.uploads>=permission.maxUploads)throw fail('当前未获准上传，或本轮额度已用完','UPLOAD_NOT_AUTHORIZED');
  if(!visible||disposed||!binding||api.identity()!==binding.identity||!options.url.startsWith(config.origin+'/api/mini/v1/')||!new RegExp('^/api/mini/v1/map-recognition/jobs\\?server=cn&catalog_version='+expected.cn_catalog_version+'&request_key=[a-zA-Z0-9_-]{16,80}$').test(options.url.slice(config.origin.length))||options.name!=='image'||Object.keys(options.formData||{}).length)throw fail('上传绑定已失效','UPLOAD_BINDING_INVALID');
  counts.uploads++;const event={startedAtUtc:new Date().toISOString(),endedAtUtc:null,outcome:'pending',httpStatus:null,diagnostic:null};lastUpload=event;
  const finish=(outcome,status)=>{event.endedAtUtc=new Date().toISOString();event.outcome=outcome;event.httpStatus=Number.isInteger(status)?status:null;};
  try{return wx.uploadFile({...options,success:r=>{finish('http_response',r.statusCode);options.success(r);},fail:e=>{finish('native_failure',null);options.fail(e);}});}catch(e){finish('synchronous_failure',null);throw e;}
 };
 const api=createNativeApi(observed,config),media=createMedia(wx);
 const jobs=createRecognitionJobs({...jobOptions,api:api.jobs,createKey:()=>requestId(wx),currentBinding:()=>{if(!binding||api.identity()!==binding.identity)throw fail('访客身份已变化','OWNER_CHANGED');return binding;}});
 async function validate(){const c=await api.catalog();const b=verifyOcrBinding(snapshots.cn,snapshots.global,c,expected,api.identity());catalog=c;return b;}
 async function connect(){if(disposed)throw fail('工程已关闭','DISPOSED');if(busy)throw fail('识别任务进行中','BUSY');if(connection)return connection;
  const ticket=epoch;connection=(async()=>{state='connecting';errorCode=null;diagnostic=null;httpStatus=null;try{await api.reconnectSession();const identity=api.identity();const cn=verifyNativeSnapshot(await api.snapshot('cn'),'cn',identity),global=verifyNativeSnapshot(await api.snapshot('global'),'global',identity),c=await api.catalog();const next=verifyOcrBinding(cn,global,c,expected,identity);if(ticket!==epoch||!visible||disposed)throw fail('连接已停止','STOPPED');if(binding&&binding.identity!==identity){jobs.cancel();selection=null;pending=null;consent=false;}binding=next;snapshots={cn,global};catalog=c;state='ready';return report();}catch(e){if(ticket===epoch){state='failed';errorCode=e.code||'CONNECTION_FAILED';captureFailure(e);}throw e;}})();try{return await connection;}finally{connection=null;}}
 async function execute(resume){if(!visible||disposed||busy)throw fail('当前不能识别','BUSY');if(resume&&permission.noRecovery)throw fail('本次授权不恢复任务','RECOVERY_NOT_AUTHORIZED');if(!permission.uploadDomainDeclared||permission.maxUploads===0)throw fail('尚未批准实图与费用范围','UPLOAD_NOT_AUTHORIZED');if(!resume&&(!consent||!selection||counts.uploads>=permission.maxUploads))throw fail('请先选图并同意本次处理，或本轮额度已用完','UPLOAD_NOT_AUTHORIZED');
  const ticket=epoch;busy=true;state=resume?'recovering':'recognizing';errorCode=null;diagnostic=null;httpStatus=null;pending=null;
  try{const b=await validate();if(!binding||b.identity!==binding.identity||ticket!==epoch)throw fail('绑定已变化','OWNER_CHANGED');if(catalog.worker!=='ready')throw fail('识别服务未就绪','WORKER_NOT_READY');const value=await (resume?jobs.resume():jobs.start({...selection,expected_sha256:permission.sampleSha256}));if(ticket!==epoch||!visible)throw fail('识别已暂停','STOPPED');pending=value.slots;state='pending_confirmation';return report();}catch(e){if(ticket===epoch){state='failed';errorCode=e.safetyCode||e.code||'OCR_REQUEST_FAILED';captureFailure(e);if(permission.lockOnFailure){permission.maxUploads=0;permission.uploadDomainDeclared=false;consent=false;}}throw e;}finally{if(ticket===epoch)busy=false;}
 }
 function report(){return {state,errorCode,httpStatus,diagnostic,diagnosticsRevision:2,lastUpload:lastUpload&&{...lastUpload},ready:!!binding,verifiedVersions:binding?{cn:snapshots.cn.version,global:snapshots.global.version}:null,worker:catalog&&catalog.worker,maps:expected.maps,applied:applied.map(m=>m&&{...m}),pending:pending&&pending.map(m=>m&&{...m}),hasImage:!!selection,consent,counts:{...counts},maxUploads:permission.maxUploads,uploadAllowed:permission.uploadDomainDeclared&&permission.maxUploads>counts.uploads,taskPhase:jobs.state().phase,delivery:expected.delivery_id,cnCatalog:expected.cn_catalog_version,accounts:false};}
 return {connect,report,lockUploads(){permission.maxUploads=0;permission.uploadDomainDeclared=false;consent=false;},setConsent(value){consent=value===true;},async choose(){if(disposed||busy)throw fail('当前不能选图','BUSY');const ticket=++mediaEpoch;const image=await media.choose();if(ticket!==mediaEpoch||disposed||!image)return; jobs.cancel();pending=null;selection=image;consent=false;},recognize:()=>execute(false),resume:()=>execute(true),
  setMap(index,map,pendingSlot=false){if(busy)throw fail('任务进行中','BUSY');if(!Number.isInteger(index)||index<0||index>4||!expected.maps.some(m=>m.big===map.big&&m.small===map.small))throw fail('地图不在目录','MAP_INVALID');const target=pendingSlot?pending:applied;if(!target)throw fail('没有待确认结果','NO_RESULT');if(target.some((m,i)=>i!==index&&m&&m.big===map.big))throw fail('大地图不能重复','DUPLICATE_MAP');target[index]={big:map.big,small:map.small};},
  async confirm(){if(busy||!visible||!pending||pending.some(m=>!m)||new Set(pending.map(m=>m.big)).size!==5)throw fail('请补齐五张不同大地图','INCOMPLETE_MAPS');const ticket=epoch;const saved=pending.map(m=>({...m}));busy=true;try{await validate();if(ticket!==epoch||!pending)throw fail('结果已失效','STOPPED');saved.forEach((m,i)=>{applied[i]=m;});pending=null;selection=null;consent=false;state='confirmed';}finally{if(ticket===epoch)busy=false;}},
  hide(){visible=false;epoch++;busy=false;jobs.suspend();pending=null;consent=false;},show(){visible=true;},cancel(){epoch++;mediaEpoch++;busy=false;jobs.cancel();pending=null;selection=null;consent=false;state='ready';},dispose(){disposed=true;epoch++;mediaEpoch++;jobs.cancel();api.session.invalidate();selection=null;pending=null;consent=false;}};
}
module.exports={createOcrProbe,verifyOcrBinding};
