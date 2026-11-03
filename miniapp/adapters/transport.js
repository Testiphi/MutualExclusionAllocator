'use strict';
const {decodeUtf8}=require('./hash');
function responseJSON(response) {
  const data=response.data;
  if(typeof data==='string')return JSON.parse(data);
  if(data instanceof ArrayBuffer||ArrayBuffer.isView(data)){if(data.byteLength>2*1024*1024)throw Error('响应超过客户端大小限制');return JSON.parse(decodeUtf8(data));}
  throw Error('响应格式无效');
}
// Low-level only: no guessed mini routes, no production URL, no automatic retry.
function createTransport(wx, { baseURL, enabled = false, allowLocal = false,namespace='visitor' } = {}) {
  if(!['visitor','account'].includes(namespace))throw Error('无效原生空间');
  const valid = typeof baseURL === 'string' &&
    (/^https:\/\/[a-z0-9.-]+(?::\d+)?$/i.test(baseURL) ||
      (allowLocal && /^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(baseURL)));
  let token = null;
  const active = new Set();
  function start(path, options, upload) {
    if (!enabled || !valid) throw Error('原生服务尚未配置');
    const scope=namespace==='account'?'/api/mini/account/v1/':'/api/mini/v1/';
    if (!path.startsWith(scope)||!/^\/api\/mini\/(?:account\/)?v1\/[a-z0-9/_-]+(?:\?[a-z0-9=&_.%-]+)?$/i.test(path)) throw Error('拒绝非原生接口');
    const headers = { ...(options.header || {}) };
    if (Object.keys(headers).some(k => /^(cookie|origin|authorization)$/i.test(k))) throw Error('禁止覆盖会话头');
    if (token) headers.Authorization = 'Bearer ' + token;
    let task;
    const promise = new Promise((resolve, reject) => {
      const done = () => active.delete(task);
      const args = { ...options, url: baseURL + path, header: headers, timeout: 30000,
        success(response) {
          done();
          if (response.statusCode === 401) token = null;
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
        fail(reason) { done();const error=Error('网络请求未完成，请重试');error.nativeReason=reason&&reason.errMsg?String(reason.errMsg).slice(0,240):'';reject(error); }
      };
      if (upload) {
        // wx sets the multipart boundary; callers must not set Content-Type.
        if (Object.keys(headers).some(k => /^content-type$/i.test(k))) throw Error('上传类型由微信生成');
        task = wx.uploadFile(args);
      } else task = wx.request({ ...args, responseType: 'arraybuffer' });
      active.add(task);
    });
    return { promise, abort: () => { if (task) { active.delete(task); task.abort(); } } };
  }
  return {
    setToken(value) { if (typeof value !== 'string' || !value || /[\r\n]/.test(value)) throw Error('无效会话'); token = value; },
    clearSession() { token = null; for (const task of active) task.abort(); active.clear(); },
    request: (path, options = {}) => start(path, options, false),
    upload: (path, options) => start(path, options, true)
  };
}
module.exports = { createTransport, responseJSON };
