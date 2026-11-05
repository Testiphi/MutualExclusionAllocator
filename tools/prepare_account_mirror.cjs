'use strict';
// Independent developer source project, local fixed data + lazy read-only A.
// No CLI preview/upload, no server, no network, no credentials.
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),workspace=path.dirname(root),out=path.resolve(process.argv[2]||''),planId=process.argv[3];
assert.ok(out.startsWith(path.join(workspace,'offline-evaluation')+path.sep)&&!fs.existsSync(out));
const {binding}=require('../miniapp/services/account_readonly'),{validateAccountProfile}=require('../miniapp/services/account_connection');
const config=validateAccountProfile({enabled:true,origin:binding.origin,allowCloudWrites:false,planId});
const source=cp.execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim();
const receipt={source,dirty:!!cp.execFileSync('git',['status','--porcelain'],{cwd:root,encoding:'utf8'}).trim(),planId,origin:config.origin,allowCloudWrites:false,files:{},previewInvoked:false,formalPackage:false,uploaded:false,networkExecuted:false};
function write(name,bytes,from){const file=path.join(out,name);assert.ok(!fs.existsSync(file));fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,bytes,{flag:'wx'});receipt.files[name]={sha256:crypto.createHash('sha256').update(bytes).digest('hex'),bytes:Buffer.byteLength(bytes),from};}
const files=cp.execFileSync('git',['ls-files','-z','miniapp'],{cwd:root,encoding:'utf8'}).split('\0').filter(Boolean);
for(const file of files){if(file==='miniapp/README.md')continue;write(file.slice(8),fs.readFileSync(path.join(root,file)),file);}
// Include newly developed runtime source before a local commit, with dirty provenance.
if(!files.includes('miniapp/services/account_connection.js'))write('services/account_connection.js',fs.readFileSync(path.join(root,'miniapp/services/account_connection.js')),'local client source');
const fixed=require('../miniapp/shared-source.json'),mirror=require('../miniapp/mirror-source.json');
for(const name of fixed.files)write('shared/'+name,cp.execFileSync('git',['show',fixed.ref+':'+name],{cwd:root}),fixed.ref+':'+name);
for(const name of mirror.files)write('shared/'+name,cp.execFileSync('git',['show',mirror.ref+':'+name],{cwd:root}),mirror.ref+':'+name);
const feature=cp.execFileSync('git',['show',mirror.ref+':'+mirror.contract],{cwd:root});
write('shared/feature_contract.js','module.exports='+feature.toString('utf8')+';\n',mirror.ref+':'+mirror.contract);
write('shared/'+path.basename(mirror.contract),feature,mirror.ref+':'+mirror.contract);
const tokens=JSON.parse(fs.readFileSync(path.join(out,'shared/home_theme.json'),'utf8'));
write('shared/theme.wxss',`page{background:${tokens.tokens['--rp-bg']};color:${tokens.tokens['--rp-text']};font-family:${tokens.tokens['--rp-font']};}\n.mirror-surface{background:${tokens.tokens['--rp-surface']};border-color:${tokens.tokens['--rp-divider']};}\n.mirror-muted{color:${tokens.tokens['--rp-muted']};}\n.mirror-selected{background:${tokens.tokens['--rp-selected']};border-color:${tokens.tokens['--rp-blue']};}\n`,mirror.ref+':home_theme.json');
write('shared/functional_theme.wxss',require('./mini_theme.cjs').functionalTheme(tokens),mirror.ref+':home_theme.json');
const page=cp.execFileSync('git',['show',fixed.ref+':index.html'],{cwd:root,encoding:'utf8'});
write('shared/web_home.js',require('./web_home_adapter.cjs').generateWebHomeAdapter(page),fixed.ref+':index.html derived compatibility');
const bundle={kind:'local-unfrozen',files:{},hashes:binding.fixed_runtime.files};
for(const [name,meta] of Object.entries(bundle.hashes)){
 const b=fs.readFileSync(path.join(workspace,'offline-evaluation/mini-account-isolation-20261105-01/candidate-04/snapshot',name));
 assert.equal(b.length,meta.bytes);assert.equal(crypto.createHash('sha256').update(b).digest('hex'),meta.sha256);
 bundle.files[name]=new TextDecoder('utf-8',{fatal:true}).decode(b);
}
require('../miniapp/adapters/snapshot').verifyLocalBundle(bundle);
write('generated/local-bundle.js','module.exports='+JSON.stringify(bundle)+';\n','fixed account delivery five raw files');
write('generated/native-config.js','module.exports={enabled:false};\n','no OCR/visitor-service connection in this acceptance project');
write('generated/account-config.js','module.exports='+JSON.stringify(config)+';\n','independent lazy readonly origin');
const buildId=crypto.createHash('sha256').update(JSON.stringify(receipt.files)+planId+out).digest('hex').slice(0,20);receipt.buildId=buildId;write('generated/build-info.js','module.exports='+JSON.stringify({buildId,planId})+';\n','bound developer build identity');
const local=JSON.parse(fs.readFileSync(path.join(root,'miniapp/project.config.json'),'utf8'));
write('project.config.json',JSON.stringify({...local,projectname:'RacePick-mirror-account-readonly',setting:{...local.setting,urlCheck:true}},null,2),'local ignored identity; never print AppID');
fs.writeFileSync(path.join(path.dirname(out),'mirror-project-receipt.json'),JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({project:out,planId,buildId,source,dirty:receipt.dirty,accountLazy:true,cloudWrites:false,networkExecuted:false}));
