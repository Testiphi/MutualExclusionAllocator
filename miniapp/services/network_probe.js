'use strict';
const {createNativeApi}=require('../adapters/native_api');
const {verifyNativeSnapshot}=require('../adapters/snapshot');
function createNetworkProbe(wx,config){
 if(!config||config.kind!=='platform')throw Error('网络基础验收只接受明确的platform配置');
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
   stage='snapshot_cn';const cn=verifyNativeSnapshot(await api.snapshot('cn'),'cn',identity);if(ticket!==epoch)throw Error('网络探针已关闭');last.checks.push({stage,passed:true,version:cn.version,files:Object.keys(cn.envelope.files),mapRecognitionDeclared:cn.capabilities.map_recognition});
   stage='snapshot_global';const global=verifyNativeSnapshot(await api.snapshot('global'),'global',identity);if(ticket!==epoch||api.identity()!==identity)throw Error('访客身份已变化');last.checks.push({stage,passed:true,version:global.version,files:Object.keys(global.envelope.files)});
   last={...last,state:'passed',expiresAt:api.session.current().expiresAt,counts:{...counters},fixture:false,accountLoginTested:false,ocrTested:false,phoneTested:false,domainRegistrationVerified:false};return snapshot();
  }catch(e){last={...last,state:'failed',failedStage:stage,httpStatus:e.status||null,errorCode:e.code||'NETWORK_OR_PROTOCOL_ERROR',retryAfterMs:e.retryAfterMs||0,counts:{...counters}};throw e;}})();
  flight=work;try{return await work;}finally{if(flight===work)flight=null;}
 }
 return {run,report:snapshot,dispose(){disposed=true;epoch++;api.session.invalidate();}};
}
module.exports={createNetworkProbe};
