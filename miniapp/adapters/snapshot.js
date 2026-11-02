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
function verifyNativeSnapshot(value,server,identity) {
  if(!value||value.schema_version!==1||value.server!==server||value.identity!==identity||typeof value.version!=='string'||!value.version)throw Error('快照服别或身份不符');
  const names=server==='cn'?['cars.json','gauntlet_data.json']:server==='global'?['cars.global.json','gauntlet_data.global.json','global-data-manifest.json']:[];
  if(!names.length||!value.files||Object.keys(value.files).sort().join()!==names.slice().sort().join())throw Error('快照文件白名单不符');
  const parsed={};
  for(const name of names){const f=value.files[name];if(!f||typeof f.text!=='string')throw Error('快照没有原文件文本');const bytes=utf8(f.text);if(bytes.length!==f.bytes||sha256(bytes)!==f.sha256)throw Error('快照原始字节校验失败');parsed[name]=JSON.parse(f.text);}
  const cars=parsed[names[0]],data=parsed[names[1]],caps=value.capabilities;
  if(!Array.isArray(cars.cars)||!Array.isArray(data.tracks)||!caps||!Array.isArray(caps.zones)||!Array.isArray(caps.tiers))throw Error('快照能力或结构无效');
  if(server==='global') {
    const m=parsed['global-data-manifest.json'],keys=['server_id','schema_version','dataset_version','catalog_payload_sha256','scores_payload_sha256','manifest_file'];
    if(!m._meta||m._meta.server_id!=='global'||m._meta.schema_version!==1||m._meta.manifest_file!=='global-data-manifest.json'||value.catalog_version!==null||caps.map_recognition!==false||caps.zones.join()!=='zone5'||caps.tiers.join()!=='理论')throw Error('国际服快照能力不符');
    for(const name of names.slice(0,2)){const f=m.files&&m.files[name],raw=value.files[name];if(!parsed[name]._meta||keys.some(k=>m._meta[k]===undefined||parsed[name]._meta[k]!==m._meta[k])||!f||f.sha256!==raw.sha256||f.bytes!==raw.bytes||f.payload_sha256!==(name===names[0]?m._meta.catalog_payload_sha256:m._meta.scores_payload_sha256))throw Error('国际服原子版本不符');}
  } else if(caps.zones.join()!=='zone5,zone4'||caps.tiers.join()!=='理论,高手,普通,自动'||typeof caps.map_recognition!=='boolean'||(caps.map_recognition&&!/^[a-f0-9]{64}$/.test(value.catalog_version)))throw Error('国服快照能力不符');
  return {server,version:value.version,cars,data,catalogVersion:value.catalog_version,identity,capabilities:caps,envelope:value};
}
module.exports = { verifyLocalBundle,verifyNativeSnapshot };
