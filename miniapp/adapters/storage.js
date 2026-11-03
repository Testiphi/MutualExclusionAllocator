'use strict';
const {sha256,utf8}=require('./hash');
// Separate namespaces for mock/real and each server. No browser or account access.
function createStorage(wx, namespace) {
  if (!['mock', 'local', 'native', 'native-fixture'].includes(namespace)) throw Error('无效的存储空间');
  const key = server => {
    if (!['cn', 'global'].includes(server)) throw Error('无效服别');
    return 'racepick.mini.' + namespace + '.draft.v1.' + server;
  };
  function validate(value,server) {
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
  function read(server) {return validate(wx.getStorageSync(key(server)),server);}
  const fingerprint=value=>sha256(utf8(JSON.stringify(value)));
  const workingKey=server=>key(server).replace('.draft.v1.','.working.v1.');
  function write(server, draft, expected) {
    // One platform write, only after serializing. A failed write leaves UI dirty.
    const value = JSON.parse(JSON.stringify(draft));
    if (value.schema !== 1 || value.server !== server) throw Error('草稿服别不符');
    if(arguments.length>=3&&fingerprint(read(server))!==fingerprint(expected))throw Error('另一窗口已保存新车库，请先恢复后重试');
    wx.setStorageSync(key(server), value);
  }
  function readWorking(server,saved) {
    const record=wx.getStorageSync(workingKey(server));if(record===''||record==null)return null;
    if(!record||record.schema!==1||record.server!==server||record.base!==fingerprint(saved))throw Error('临时草稿与已保存车库不一致，原记录已保留');
    const value=validate(record.draft,server);if(!value)throw Error('临时草稿损坏，原记录已保留');return value;
  }
  function writeWorking(server,draft,saved) {wx.setStorageSync(workingKey(server),{schema:1,server,base:fingerprint(saved),draft:JSON.parse(JSON.stringify(draft))});}
  function clearWorking(server) {if(typeof wx.removeStorageSync==='function')wx.removeStorageSync(workingKey(server));}
  return { read, write,readWorking,writeWorking,clearWorking };
}
module.exports = { createStorage };
