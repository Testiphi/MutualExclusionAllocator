'use strict';
// Byte-for-byte generated copies. Never edit miniapp/shared by hand.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const cp = require('node:child_process');
const root = path.resolve(__dirname, '..');
const config = require('../miniapp/shared-source.json');
const files = config.files;
const output = path.join(root, 'miniapp/shared');
fs.mkdirSync(output, { recursive: true });
const manifest = { source: cp.execFileSync('git', ['rev-parse', config.ref], { cwd: root, encoding: 'utf8' }).trim(), files: {} };
for (const name of files) {
  // Read immutable Git blobs, never the website's concurrently edited worktree.
  const bytes = cp.execFileSync('git', ['show', manifest.source + ':' + name], { cwd: root });
  fs.writeFileSync(path.join(output, name), bytes);
  manifest.files[name] = { bytes: bytes.length, sha256: crypto.createHash('sha256').update(bytes).digest('hex') };
}
fs.writeFileSync(path.join(output, 'source.json'), JSON.stringify(manifest, null, 2) + '\n');
console.log(JSON.stringify(manifest, null, 2));
const receiptIndex = process.argv.indexOf('--data-receipt');
const generated = path.join(root,'miniapp/generated'); fs.mkdirSync(generated,{recursive:true});
if (receiptIndex !== -1) {
  if (!process.argv[receiptIndex + 1]) throw Error('缺少本地接收回执路径');
  const receiptPath = path.resolve(process.argv[receiptIndex + 1]);
  const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
  const expected = ['cars.json','gauntlet_data.json','cars.global.json','gauntlet_data.global.json','global-data-manifest.json'];
  if (Object.keys(receipt.runtime).sort().join() !== [...expected].sort().join()) throw Error('运行文件白名单不符');
  const bundle = { kind: 'local-unfrozen', files: {}, hashes: receipt.runtime };
  for (const name of expected) {
    const bytes = fs.readFileSync(path.join(path.dirname(receiptPath), 'runtime', name));
    if (bytes.length !== receipt.runtime[name].bytes || crypto.createHash('sha256').update(bytes).digest('hex') !== receipt.runtime[name].sha256) throw Error('本地数据SHA不符：' + name);
    bundle.files[name] = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
  }
  fs.writeFileSync(path.join(generated,'local-bundle.js'),'module.exports = ' + JSON.stringify(bundle) + ';\n');
  console.log('已生成未冻结本地数据，仅用于本机计算；未接入真实OCR');
} else fs.writeFileSync(path.join(generated,'local-bundle.js'),'module.exports = null;\n');
