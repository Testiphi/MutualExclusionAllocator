'use strict';
function requestId(wx) {
  if (typeof wx.getRandomValues !== 'function') return Promise.reject(Error('基础库缺少安全随机数接口'));
  return new Promise((resolve, reject) => wx.getRandomValues({ length: 16,
    success(result) {
      const bytes = new Uint8Array(result.randomValues);
      if (bytes.length !== 16) { reject(Error('随机请求ID生成失败')); return; }
      resolve(Array.from(bytes, x => x.toString(16).padStart(2, '0')).join(''));
    }, fail() { reject(Error('随机请求ID生成失败')); }
  }));
}
module.exports = { requestId };
