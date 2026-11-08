'use strict';
// Independent developer source project, local fixed data + lazy read-only A.
// No CLI preview/upload, no server, no network, no credentials.
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),workspace=path.dirname(root),out=path.resolve(process.argv[2]||''),planId=process.argv[3];
assert.ok(out.startsWith(path.join(workspace,'offline-evaluation')+path.sep)&&!fs.existsSync(out));
const {binding}=require('../miniapp/services/account_readonly'),{validateAccountProfile}=require('../miniapp/services/account_connection');
const candidate=/^--w3-candidate-[ab]$/.test(process.argv[4]||'');
const role=/^--w3-(prepare|candidate)-a$/.test(process.argv[4]||'')?'a':/^--w3-(prepare|candidate)-b$/.test(process.argv[4]||'')?'b':null;
const writable=process.argv[4]==='--write-w1w2'||candidate,readback=process.argv[4]==='--saved-readback';
const registration=process.argv[4]==='--isolated-registration';
const localSync=process.argv[4]==='--local-sync';
const formalWrite=process.argv[4]==='--formal-write';
const firstRelease=process.argv[4]==='--formal-first-release';
const formalOcr=process.argv[4]==='--formal-ocr-readonly'||firstRelease;
const formal=process.argv[4]==='--formal-readonly'||formalWrite||formalOcr;
assert.ok(!process.argv[4]||writable||readback||role||localSync||formal||registration);
if(localSync)assert.match(planId,/^mini-local-sync-[a-zA-Z0-9_-]+$/);
const readbackBinding=require('../miniapp/services/account_readback_binding');
const writableBinding=require('../miniapp/services/account_writable_binding');
const config=validateAccountProfile(formal?JSON.parse(fs.readFileSync(process.argv[5],'utf8')):localSync?{enabled:false}:{enabled:true,origin:binding.origin,allowCloudWrites:writable,planId,...(registration?{registrationDelivery:process.argv[5]}:{}),...(writable?{writableReceipt:writableBinding.handoff_sha256}: {}),...(readback?{readbackReceipt:readbackBinding.receipt_sha256}: {}),...(role?{conflictRole:role,conflictGroup:'w3-20261107-01',conflictReceipt:readbackBinding.receipt_sha256}: {})});
if(formal){assert.equal(config.mode,'production-a');assert.equal(config.allowCloudWrites,formalWrite||firstRelease);assert.equal(config.planId,planId);}
const ocr=formalOcr?require('../docs/MINI_OCR_EXPECTED_20261104.json'):null;
const native=ocr?{enabled:true,kind:'platform',origin:ocr.origin}:{enabled:false};
const ocrBinding=ocr?{snapshot_versions:ocr.snapshot_versions,files:ocr.files,global_dataset:ocr.global_dataset,cn_catalog_version:ocr.cn_catalog_version}:null;
if(ocr){
 assert.equal(ocr.origin,'https://mini-test.racepick.cn');
 assert.deepEqual(ocr.files,config.fixedRuntime.files);
 assert.equal(ocr.global_dataset,config.fixedRuntime.global_dataset);
 assert.match(ocr.cn_catalog_version,/^[a-f0-9]{64}$/);
}
const source=cp.execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim();
const receipt={source,dirty:!!cp.execFileSync('git',['status','--porcelain'],{cwd:root,encoding:'utf8'}).trim(),planId,origin:config.origin,allowCloudWrites:config.allowCloudWrites===true,...(registration?{registrationDelivery:config.registrationDelivery}:{}),...(readback?{readbackBinding}: {}),...(writable?{writableBinding}: {}),...(ocr?{ocrOrigin:ocr.origin,ocrBinding}:{}),files:{},previewInvoked:false,formalPackage:firstRelease,uploaded:false,networkExecuted:false};
function write(name,bytes,from){const file=path.join(out,name);assert.ok(!fs.existsSync(file));fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,bytes,{flag:'wx'});receipt.files[name]={sha256:crypto.createHash('sha256').update(bytes).digest('hex'),bytes:Buffer.byteLength(bytes),from};}
const files=cp.execFileSync('git',['ls-files','-z','miniapp'],{cwd:root,encoding:'utf8'}).split('\0').filter(Boolean);
for(const name of ['account_write_acceptance.js','account_writable_binding.js','account_readback_binding.js','account_conflict_acceptance.js','profile_conflict.js','account_production.js']){const file='miniapp/services/'+name;if(!files.includes(file))files.push(file);}
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
const bundle={kind:'local-unfrozen',files:{},hashes:{}};
for(const [name,fixedMeta] of Object.entries(binding.fixed_runtime.files)){
 const b=localSync?cp.execFileSync('git',['show',mirror.ref+':'+name],{cwd:root}):fs.readFileSync(path.join(workspace,'offline-evaluation/mini-account-isolation-20261105-01/candidate-04/snapshot',name));
 const meta=localSync?{bytes:b.length,sha256:crypto.createHash('sha256').update(b).digest('hex')}:formal?config.fixedRuntime.files[name]:fixedMeta;
 assert.equal(b.length,meta.bytes);assert.equal(crypto.createHash('sha256').update(b).digest('hex'),meta.sha256);
 bundle.hashes[name]=meta;
 bundle.files[name]=new TextDecoder('utf-8',{fatal:true}).decode(b);
}
require('../miniapp/adapters/snapshot').verifyLocalBundle(bundle);
write('generated/local-bundle.js','module.exports='+JSON.stringify(bundle)+';\n',localSync?mirror.ref+':five local runtime JSON blobs':'fixed account delivery five raw files');
write('generated/native-config.js','module.exports='+JSON.stringify(native)+';\n',ocr?'fixed OCR gateway':'no OCR/visitor-service connection');
write('generated/account-config.js','module.exports='+JSON.stringify(config)+';\n','independent account origin and write policy');
const buildId=crypto.createHash('sha256').update(JSON.stringify(receipt.files)+planId+out).digest('hex').slice(0,20);receipt.buildId=buildId;write('generated/build-info.js','module.exports='+JSON.stringify(localSync?{buildId,storageScope:planId}:{buildId,...(firstRelease?{}:{planId}),...(ocr?{ocrBinding}:{})})+';\n','bound developer build identity');
const local=JSON.parse(fs.readFileSync(path.join(root,'miniapp/project.config.json'),'utf8'));
write('project.config.json',JSON.stringify({...local,projectname:firstRelease?'RacePick-first-release':formalOcr?'RacePick-formal-OCR-readonly-candidate':formalWrite?'RacePick-formal-cloud-save-candidate':localSync?'RacePick-local-source-sync':registration?'RacePick-isolated-registration':role?'RacePick-W3-'+role+(candidate?'-CANDIDATE':'-PREPARED-NO-WRITES'):writable?'RacePick-W1W2-write-acceptance':readback?'RacePick-saved-readback':'RacePick-mirror-account-readonly',setting:{...local.setting,urlCheck:true}},null,2),'local ignored identity; never print AppID');
fs.writeFileSync(path.join(path.dirname(out),'mirror-project-receipt.json'),JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({project:out,planId,buildId,source,dirty:receipt.dirty,accountLazy:true,cloudWrites:receipt.allowCloudWrites,networkExecuted:false}));
