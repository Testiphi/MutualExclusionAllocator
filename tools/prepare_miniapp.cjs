'use strict';
// Byte-for-byte generated copies. Never edit miniapp/shared by hand.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const cp = require('node:child_process');
const root = path.resolve(__dirname, '..');
const files = ['allocator.js', 'race_scores.js', 'app_state.js', 'profile_store.js'];
cp.execFileSync('git', ['diff', '--exit-code', 'HEAD', '--', ...files], { cwd: root, stdio: 'pipe' });
const output = path.join(root, 'miniapp/shared');
fs.mkdirSync(output, { recursive: true });
const manifest = { source: cp.execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(), files: {} };
for (const name of files) {
  const bytes = fs.readFileSync(path.join(root, name));
  fs.writeFileSync(path.join(output, name), bytes);
  manifest.files[name] = { bytes: bytes.length, sha256: crypto.createHash('sha256').update(bytes).digest('hex') };
}
fs.writeFileSync(path.join(output, 'source.json'), JSON.stringify(manifest, null, 2) + '\n');
console.log(JSON.stringify(manifest, null, 2));
