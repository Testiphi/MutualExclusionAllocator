'use strict';
const {createTransport,responseJSON}=require('./transport');
const {createSession}=require('./session');
const {sha256}=require('./hash');
function createNativeApi(wx,config,{wait=ms=>new Promise(r=>setTimeout(r,ms)),now=Date.now}={}) {
  if(!config||!config.enabled)throw Error('原生接口未配置');
  const fixture=config.kind==='fixture';
  if(fixture&&((wx.getSystemInfoSync().platform!=='devtools')||!/^http:\/\/127\.0\.0\.1:\d+$/.test(config.origin)))throw Error('fixture仅供本机开发者工具使用');
  const transport=createTransport(wx,{enabled:true,baseURL:config.origin,allowLocal:fixture});
  const prefix='/api/mini/v1',fingerprints=new Map(),metrics={uploads:0,queries:0,recoveries:0};
  const json=async(path,options)=>{try{return responseJSON(await transport.request(prefix+path,options).promise);}catch(e){if(e.status===401&&session.current().identity)session.invalidate();throw e;}};
  const session=createSession(wx,{now,autoRenew:false,setToken:transport.setToken,clearToken:transport.clearSession,
    credentials:fixture?async()=>({code:config.fixtureCode,request_key:config.fixtureKey}):undefined,
    exchange:async input=>{
      const s=await json('/session',{method:'POST',header:{'Content-Type':'application/json'},data:{...input,client_schema:1}});
      if(s.schema_version!==1||s.token_type!=='Bearer'||typeof s.identity!=='string'||!s.identity||!Number.isFinite(s.expires_at))throw Error('访客会话响应无效');
      return {token:s.token,identity:s.identity,expiresAt:s.expires_at*1000};
    }});
  function auth(identity) {
    const s=session.current();
    if(!s.identity||s.expiresAt<=now())throw Object.assign(Error('访客会话已失效，请重新连接'),{status:401});
    if(identity&&s.identity!==identity)throw Object.assign(Error('会话已变化，旧任务不可恢复'),{status:403});
    return s.identity;
  }
  const query=p=>'?server='+encodeURIComponent(p.server)+'&catalog_version='+encodeURIComponent(p.catalog_version);
  function current(p){auth(p.identity);if(p.isCurrent&&!p.isCurrent())throw Object.assign(Error('本次识别已停止'),{code:'stopped'});}
  async function upload(p) {
    current(p);
    const bytes=await new Promise((resolve,reject)=>wx.getFileSystemManager().readFile({filePath:p.path,success:r=>resolve(r.data),fail:()=>reject(Error('截图临时文件已失效，请重新选择'))}));
    // wx filesystem buffers may belong to another JS realm; instanceof is false
    // even for a genuine ArrayBuffer. Normalize through a local typed view.
    const view=new Uint8Array(bytes);
    if(view.byteLength!==p.size||p.size>8388608)throw Error('截图大小已变化，请重新选择');
    const hash=sha256(view),previous=fingerprints.get(p.request_key);
    if(previous&&previous!==hash)throw Object.assign(Error('原截图已变化，不能重用上传请求'),{code:'protocol'});
    fingerprints.set(p.request_key,hash);current(p);
    metrics.uploads++;
    try{return responseJSON(await transport.upload(prefix+'/map-recognition/jobs'+query(p)+'&request_key='+encodeURIComponent(p.request_key),{filePath:p.path,name:'image',formData:{}}).promise);}catch(e){if(e.status===401)session.invalidate();throw e;}
  }
  return {
    session,fixture,identity:()=>auth(),metrics:()=>({...metrics}),
    snapshot:server=>{auth();return json('/snapshot?server='+encodeURIComponent(server));},
    catalog:()=>{auth();return json('/map-recognition/catalog?server=cn');},
    jobs:{upload,
      query:p=>{current(p);metrics.queries++;return json('/map-recognition/jobs/'+p.id+query(p));},
      cancel:p=>{current(p);return json('/map-recognition/jobs/'+p.id+query(p),{method:'DELETE'});},
      recover:async p=>{
        metrics.recoveries++;
        const deadline=now()+35000;
        while(true) {
          current(p);
          const response=await transport.request(prefix+'/map-recognition/jobs/by-request'+query(p)+'&request_key='+encodeURIComponent(p.request_key)).promise;
          const r=responseJSON(response);current(p);
          if(r.recovery==='found')return r;
          if(r.recovery==='reading'&&r.retry_same_key===false) {
            const h=response.header||{},k=Object.keys(h).find(k=>k.toLowerCase()==='retry-after');
            const delay=Math.max(1000,(Number(k&&h[k])||2)*1000);
            if(now()+delay>=deadline)throw Error('原上传仍在处理中，请稍后继续查询');
            await wait(delay);continue;
          }
          if(['not_found','interrupted'].includes(r.recovery)&&r.retry_same_key===true)return upload(p);
          throw Error('上传恢复响应无效');
        }
      }
    }
  };
}
module.exports={createNativeApi};
