'use strict';
const { utf8, sha256 } = require('./hash');
// Local bundle adapter. A future network envelope must be adapted separately.
function verifyLocalBundle(bundle) {
  if (!bundle || bundle.kind !== 'local-unfrozen') throw Error('本地数据来源不明');
  const expected = ['cars.json','gauntlet_data.json','cars.global.json','gauntlet_data.global.json','global-data-manifest.json'];
  if (Object.keys(bundle.files).sort().join() !== expected.slice().sort().join()) throw Error('本地文件清单不符');
  const parsed = {};
  for (const name of expected) {
    if (typeof bundle.files[name] !== 'string') throw Error('快照必须保留原始UTF-8文本');
    const raw = utf8(bundle.files[name]), meta = bundle.hashes[name];
    if (!meta || raw.byteLength !== meta.bytes || sha256(raw) !== meta.sha256) throw Error('快照完整性校验失败：' + name);
    parsed[name] = JSON.parse(bundle.files[name]);
  }
  const manifest = parsed['global-data-manifest.json'], meta = manifest._meta;
  const keys = ['server_id','schema_version','dataset_version','catalog_payload_sha256','scores_payload_sha256','manifest_file'];
  if (!meta || meta.server_id !== 'global' || meta.schema_version !== 1 || meta.manifest_file !== 'global-data-manifest.json') throw Error('国际服快照元数据无效');
  for (const name of ['cars.global.json','gauntlet_data.global.json']) {
    const value = parsed[name], entry = manifest.files && manifest.files[name];
    if (!value._meta || keys.some(k => value._meta[k] === undefined || value._meta[k] !== meta[k]) ||
        !entry || entry.sha256 !== bundle.hashes[name].sha256 || entry.bytes !== bundle.hashes[name].bytes ||
        entry.payload_sha256 !== (name === 'cars.global.json' ? meta.catalog_payload_sha256 : meta.scores_payload_sha256)) throw Error('国际服原子版本不一致');
  }
  if (!expected.filter(x=>x!=='global-data-manifest.json').every(name=>Array.isArray(parsed[name][name.startsWith('cars')?'cars':'tracks']))) throw Error('目录结构无效');
  return {
    cn: {server:'cn',version:'local-unfrozen-' + bundle.hashes['cars.json'].sha256 + '-' + bundle.hashes['gauntlet_data.json'].sha256,cars:parsed['cars.json'],data:parsed['gauntlet_data.json']},
    global: {server:'global',version:'local-unfrozen-' + meta.dataset_version,cars:parsed['cars.global.json'],data:parsed['gauntlet_data.global.json']}
  };
}
module.exports = { verifyLocalBundle };
