'use strict';
const {createNativeApi}=require('../adapters/native_api');
const {verifyNativeSnapshot}=require('../adapters/snapshot');
function createNetworkProbe(wx,config,expected){
 if(!config||config.kind!=='platform')throw Error('网络基础验收只接受明确的platform配置');
 if(expected&&expected.origin!==config.origin)throw Error('检查入口与固定交付不符');
 function check(checked){
  if(!expected)return;
  if(checked.version!==expected.versions[checked.server]||checked.catalogVersion!==null||checked.capabilities.map_recognition!==false)throw Error('快照版本或第一阶段能力与固定交付不符');
  for(const [name,f] of Object.entries(checked.envelope.files)){const pin=expected.files[name];if(!pin||pin.bytes!==f.bytes||pin.sha256!==f.sha256)throw Error('快照文件与固定交付不符');}
  if(checked.server==='global'&&checked.cars._meta.dataset_version!==expected.globalDataset)throw Error('国际服数据集与固定交付不符');
 }
 const receipt=checked=>({stage:'snapshot_'+checked.server,passed:true,version:checked.version,files:Object.fromEntries(Object.entries(checked.envelope.files).map(([name,f])=>[name,{bytes:f.bytes,sha256:f.sha256}])),mapRecognitionDeclared:checked.capabilities.map_recognition,catalogVersion:checked.catalogVersion});
 let epoch=0,flight=null,disposed=false,last={state:'idle',checks:[]};
 const counters={logins:0,session:0,cn:0,global:0};
 // Constrain this independent probe to the accepted session/snapshot wire only.
 const observed=Object.create(wx);observed.login=options=>{counters.logins++;return wx.login(options);};
 observed.request=options=>{const url=options.url;if(url===config.origin+'/api/mini/v1/session'&&options.method==='POST')counters.session++;else if(url===config.origin+'/api/mini/v1/snapshot?server=cn'&&(!options.method||options.method==='GET'))counters.cn++;else if(url===config.origin+'/api/mini/v1/snapshot?server=global'&&(!options.method||options.method==='GET'))counters.global++;else throw Error('网络探针拒绝非会话/快照请求');return wx.request(options);};
 observed.uploadFile=()=>{throw Error('网络基础阶段不上传图片');};
 const api=createNativeApi(observed,config);
 const snapshot=()=>JSON.parse(JSON.stringify(last));
 async function run(){if(disposed)throw Error('网络探针已关闭');if(flight)return flight;const ticket=++epoch;
  const work=(async()=>{last={state:'running',checks:[]};let stage='wechat_session';try{
   await api.reconnectSession();if(ticket!==epoch)throw Error('网络探针已关闭');const identity=api.identity();last.checks.push({stage,passed:true});
   stage='snapshot_cn';const cn=verifyNativeSnapshot(await api.snapshot('cn'),'cn',identity);if(ticket!==epoch)throw Error('网络探针已关闭');check(cn);last.checks.push(receipt(cn));
   stage='snapshot_global';const global=verifyNativeSnapshot(await api.snapshot('global'),'global',identity);if(ticket!==epoch||api.identity()!==identity)throw Error('访客身份已变化');check(global);last.checks.push(receipt(global));
   last={...last,state:'passed',expiresAt:api.session.current().expiresAt,counts:{...counters},fixture:false,pinnedDelivery:expected?expected.deliveryId:null,identityMatched:true,accountLoginTested:false,ocrTested:false,phoneTested:false,domainRegistrationVerified:false};return snapshot();
  }catch(e){last={...last,state:'failed',failedStage:stage,httpStatus:e.status||null,errorCode:e.code||'NETWORK_OR_PROTOCOL_ERROR',retryAfterMs:e.retryAfterMs||0,counts:{...counters}};throw e;}})();
  flight=work;try{return await work;}finally{if(flight===work)flight=null;}
 }
 return {run,report:snapshot,dispose(){disposed=true;epoch++;api.session.invalidate();}};
}
module.exports={createNetworkProbe};
