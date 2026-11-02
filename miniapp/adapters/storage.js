'use strict';
// Separate namespaces for mock/real and each server. No browser or account access.
function createStorage(wx, namespace) {
  if (!['mock', 'native'].includes(namespace)) throw Error('无效的存储空间');
  const key = server => {
    if (!['cn', 'global'].includes(server)) throw Error('无效服别');
    return 'racepick.mini.' + namespace + '.draft.v1.' + server;
  };
  function read(server) {
    const value = wx.getStorageSync(key(server));
    if (value === '' || value == null) return null;
    if (!value || value.schema !== 1 || value.server !== server ||
        !Array.isArray(value.maps) || value.maps.length !== 5 ||
        value.maps.some(x => x !== null && (!x || typeof x.big !== 'string' || typeof x.small !== 'string')) ||
        typeof value.zone !== 'string' || typeof value.tier !== 'string' ||
        !Array.isArray(value.cars) || value.cars.some(x => typeof x !== 'string') ||
        !value.stars || typeof value.stars !== 'object' || Array.isArray(value.stars) ||
        Object.values(value.stars).some(x => !Number.isInteger(x)) ||
        !value.oc || typeof value.oc !== 'object' || Array.isArray(value.oc) ||
        Object.values(value.oc).some(x => typeof x !== 'boolean') ||
        !value.routes || typeof value.routes !== 'object' || Array.isArray(value.routes)) {
      throw Error('本机草稿损坏，已保留原记录');
    }
    return JSON.parse(JSON.stringify(value));
  }
  function write(server, draft) {
    // One platform write, only after serializing. A failed write leaves UI dirty.
    const value = JSON.parse(JSON.stringify(draft));
    if (value.schema !== 1 || value.server !== server) throw Error('草稿服别不符');
    wx.setStorageSync(key(server), value);
  }
  return { read, write };
}
module.exports = { createStorage };
