'use strict';
const {decodeUtf8}=require('./hash');
function responseJSON(response) {
  const data=response.data;
  let kind=typeof data==='string'?'text':'unsupported',bytes;
  // Native bridges can return an ArrayBuffer from another JS realm. instanceof
  // rejects that valid buffer; use the intrinsic brand check and a local view.
  if(ArrayBuffer.isView(data)){kind='view';bytes=new Uint8Array(data.buffer,data.byteOffset,data.byteLength);}
  else if(data&&typeof data==='object'){
    try{Object.getOwnPropertyDescriptor(ArrayBuffer.prototype,'byteLength').get.call(data);bytes=new Uint8Array(data);kind='arraybuffer';}catch(_){}
  }
  try{
    if(bytes){if(bytes.byteLength>2*1024*1024)throw Object.assign(Error('响应超过客户端大小限制'),{code:'RESPONSE_TOO_LARGE'});return JSON.parse(decodeUtf8(bytes));}
    if(kind==='text'){if(data.length>2*1024*1024)throw Object.assign(Error('响应超过客户端大小限制'),{code:'RESPONSE_TOO_LARGE'});return JSON.parse(data);}
    throw Object.assign(Error('响应格式无效'),{code:'RESPONSE_TYPE_UNSUPPORTED'});
  }catch(e){
    // No response body, credentials or arbitrary native error text in diagnostics.
    const error=Object.assign(Error('响应解析未完成'),{code:e.code||'RESPONSE_JSON_OR_UTF8_INVALID',diagnostic:{kind:'response_decode',responseKind:kind,bytes:bytes?bytes.byteLength:null}});
    if(Number.isInteger(response.statusCode))error.status=response.statusCode;
    throw error;
  }
}
function networkDiagnostic(reason){
  const message=reason&&typeof reason.errMsg==='string'?reason.errMsg.toLowerCase():'';
  const kind=/not in domain|url.*domain|domain.*list|合法域名/.test(message)?'domain_rejected':/ssl|tls|certificate|cert |证书/.test(message)?'tls_or_certificate':/dns|resolve|name.*resolved/.test(message)?'dns':/timeout|timed out/.test(message)?'timeout':/abort|cancel/.test(message)?'cancelled':/connect|network|网络/.test(message)?'connection':'unknown';
  const diagnostic={kind};if(reason&&Number.isInteger(reason.errCode)&&Math.abs(reason.errCode)<1e9)diagnostic.nativeCode=reason.errCode;return diagnostic;
}
// Low-level only: no guessed mini routes, no production URL, no automatic retry.
function createTransport(wx, { baseURL, enabled = false, allowLocal = false,namespace='visitor' } = {}) {
  if(!['visitor','account'].includes(namespace))throw Error('无效原生空间');
  const valid = typeof baseURL === 'string' &&
    (/^https:\/\/[a-z0-9.-]+(?::\d+)?$/i.test(baseURL) ||
      (allowLocal && /^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(baseURL)));
  let token = null,sessionEpoch=0;
  const active = new Set();
  function start(path, options, upload) {
    if (!enabled || !valid) throw Error('原生服务尚未配置');
    const scope=namespace==='account'?'/api/mini/account/v1/':'/api/mini/v1/';
    if (!path.startsWith(scope)||!/^\/api\/mini\/(?:account\/)?v1\/[a-z0-9/_-]+(?:\?[a-z0-9=&_.%-]+)?$/i.test(path)) throw Error('拒绝非原生接口');
    const headers = { ...(options.header || {}) };
    if (Object.keys(headers).some(k => /^(cookie|origin|authorization)$/i.test(k))) throw Error('禁止覆盖会话头');
    if (token) headers.Authorization = 'Bearer ' + token;
    const ticket=sessionEpoch;
    const stale=()=>Object.assign(Error(namespace==='account'?'账号已变化，已丢弃旧请求响应':'会话已变化，已丢弃旧请求响应'),{code:'STALE_SESSION_RESPONSE'});
    let task;
    const promise = new Promise((resolve, reject) => {
      const done = () => active.delete(task);
      const args = { ...options, url: baseURL + path, header: headers, timeout: 30000,
        success(response) {
          done();
          if(ticket!==sessionEpoch){reject(stale());return;}
          if (response.statusCode === 401) {token = null;sessionEpoch++;}
          if (response.statusCode < 200 || response.statusCode >= 300) {
            let body;try{body=responseJSON(response);}catch(_){}
            const error = Error(body&&typeof body.detail==='string'?body.detail.slice(0,200):'请求失败（' + response.statusCode + '）');
            error.status = response.statusCode;error.code=body&&body.code;error.body=body;
            const headers=response.header||{},key=Object.keys(headers).find(k=>k.toLowerCase()==='retry-after'),seconds=key===undefined?NaN:Number(headers[key]);
            if(Number.isFinite(seconds)&&seconds>0)error.retryAfterMs=seconds*1000;
            reject(error); return;
          }
          resolve(response);
        },
        fail(reason) { done();if(ticket!==sessionEpoch){reject(stale());return;}const error=Object.assign(Error('网络请求未完成，请重试'),{code:'WX_REQUEST_FAILED',diagnostic:networkDiagnostic(reason)});reject(error); }
      };
      if (upload) {
        // wx sets the multipart boundary; callers must not set Content-Type.
        if (Object.keys(headers).some(k => /^content-type$/i.test(k))) throw Error('上传类型由微信生成');
        task = wx.uploadFile(args);
      } else task = wx.request({ ...args, dataType:'other',responseType: 'arraybuffer' });
      active.add(task);
    });
    return { promise, abort: () => { if (task) { active.delete(task); task.abort(); } } };
  }
  return {
    setToken(value) { if (typeof value !== 'string' || !value || /[\r\n]/.test(value)) throw Error('无效会话'); sessionEpoch++;token = value; },
    clearSession() { sessionEpoch++;token = null; for (const task of active) task.abort(); active.clear(); },
    request: (path, options = {}) => start(path, options, false),
    upload: (path, options) => start(path, options, true)
  };
}
module.exports = { createTransport, responseJSON };
