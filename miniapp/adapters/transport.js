'use strict';
// Low-level only: no guessed mini routes, no production URL, no automatic retry.
function createTransport(wx, { baseURL, enabled = false, allowLocal = false } = {}) {
  const valid = typeof baseURL === 'string' &&
    (/^https:\/\/[a-z0-9.-]+(?::\d+)?$/i.test(baseURL) ||
      (allowLocal && /^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(baseURL)));
  let token = null;
  const active = new Set();
  function start(path, options, upload) {
    if (!enabled || !valid) throw Error('原生服务尚未配置');
    if (!/^\/api\/mini\/v1\/[a-z0-9/_-]+(?:\?[a-z0-9=&_.%-]+)?$/i.test(path)) throw Error('拒绝非原生接口');
    const headers = { ...(options.header || {}) };
    if (Object.keys(headers).some(k => /^(cookie|authorization)$/i.test(k))) throw Error('禁止覆盖会话头');
    if (token) headers.Authorization = 'Bearer ' + token;
    let task;
    const promise = new Promise((resolve, reject) => {
      const done = () => active.delete(task);
      const args = { ...options, url: baseURL + path, header: headers, timeout: 30000,
        success(response) {
          done();
          if (response.statusCode === 401) token = null;
          if (response.statusCode < 200 || response.statusCode >= 300) {
            const error = Error('请求失败（' + response.statusCode + '）');
            error.status = response.statusCode; reject(error); return;
          }
          resolve(response);
        },
        fail() { done(); reject(Error('网络请求未完成，请重试')); }
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
module.exports = { createTransport };
