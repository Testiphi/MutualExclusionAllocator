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
const pageSource=cp.execFileSync('git',['show',manifest.source+':index.html'],{cwd:root});
const mirror=require('../miniapp/mirror-source.json');
manifest.mirror={source:mirror.ref,files:{}};
for(const name of [...mirror.files,mirror.contract]) {
  const bytes=cp.execFileSync('git',['show',mirror.ref+':'+name],{cwd:root});
  fs.writeFileSync(path.join(output,path.basename(name)),bytes);
  manifest.mirror.files[name]={sha256:crypto.createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length};
}
const tokens=JSON.parse(fs.readFileSync(path.join(output,'home_theme.json'),'utf8')).tokens;
// Opt-in local presentation preview. The immutable solver and mirror pins above remain unchanged.
if(process.argv.includes('--local-presenter-preview')) {
 const bytes=fs.readFileSync(path.join(root,'home_presenter.js'));
 fs.writeFileSync(path.join(output,'home_presenter.js'),bytes);
 manifest.localPresenterPreview={source:'uncommitted-local-worktree',file:'home_presenter.js',sha256:crypto.createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length};
 manifest.mirror.files['home_presenter.js']={...manifest.localPresenterPreview,pinnedSource:mirror.ref,pinnedSha256:manifest.mirror.files['home_presenter.js'].sha256};
}
const contractCode='module.exports = '+fs.readFileSync(path.join(output,path.basename(mirror.contract)),'utf8')+';\n';
fs.writeFileSync(path.join(output,'feature_contract.js'),contractCode);
manifest.mirror.contractModuleSha256=crypto.createHash('sha256').update(contractCode).digest('hex');
const theme=`/* Generated from ${mirror.ref}:home_theme.json. */\npage { background:${tokens['--rp-bg']};color:${tokens['--rp-text']};font-family:${tokens['--rp-font']}; }\n.mirror-surface {background:${tokens['--rp-surface']};border-color:${tokens['--rp-divider']};}\n.mirror-muted {color:${tokens['--rp-muted']};}\n.mirror-selected {background:${tokens['--rp-selected']};border-color:${tokens['--rp-blue']};}\n`;
fs.writeFileSync(path.join(output,'theme.wxss'),theme);
manifest.mirror.themeSha256=crypto.createHash('sha256').update(theme).digest('hex');
const homeCode=require('./web_home_adapter.cjs').generateWebHomeAdapter(pageSource.toString('utf8'));
fs.writeFileSync(path.join(output,'web_home.js'),homeCode);
manifest.derived={'web_home.js':{source_file:'index.html',source_sha256:crypto.createHash('sha256').update(pageSource).digest('hex'),sha256:crypto.createHash('sha256').update(homeCode).digest('hex')}};
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
  console.log('已生成未冻结本地数据；原生连接模式以generated/native-config.js为准');
} else fs.writeFileSync(path.join(generated,'local-bundle.js'),'module.exports = null;\n');
const originIndex=process.argv.indexOf('--native-origin');
let native={enabled:false};
if(originIndex!==-1) {
  const value=flag=>{const i=process.argv.indexOf(flag);return i<0?undefined:process.argv[i+1];};
  const origin=value('--native-origin'),fixtureCode=value('--fixture-code'),fixtureKey=value('--fixture-key');
  if(fixtureCode||fixtureKey){if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(origin)||!/^fixture-code-[12]$/.test(fixtureCode)||!/^[\w-]{16,80}$/.test(fixtureKey))throw Error('fixture配置无效');native={enabled:true,kind:'fixture',origin,fixtureCode,fixtureKey};}
  else {if(!/^https:\/\/[a-z0-9.-]+(?::\d+)?$/i.test(origin))throw Error('平台模式必须使用HTTPS');native={enabled:true,kind:'platform',origin};}
}
fs.writeFileSync(path.join(generated,'native-config.js'),'module.exports = '+JSON.stringify(native)+';\n');
