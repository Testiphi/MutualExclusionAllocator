'use strict';
// Prepare an isolated developer project; does not invoke preview, upload or packaging.
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),workspace=path.dirname(root),out=path.resolve(process.argv[2]||'');
assert.ok(out.startsWith(path.join(workspace,'offline-evaluation')+path.sep),'phone project must stay in offline-evaluation');
assert.ok(!fs.existsSync(out),'do not overwrite an existing developer project');
const commit=cp.execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),files=cp.execFileSync('git',['ls-files','miniapp'],{cwd:root,encoding:'utf8'}).trim().split(/\r?\n/);
const provenance=require('../miniapp/shared/source.json'),report={commit,offlineOnly:true,uploaded:false,formalPackage:false,storagePrefix:'racepick.devicecheck.20261103.',files:{}};
function write(name,bytes,source){const target=path.join(out,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,bytes);report.files[name]={sha256:crypto.createHash('sha256').update(bytes).digest('hex'),source};}
for(const file of files){if(file.endsWith('/README.md'))continue;const original=fs.readFileSync(path.join(root,file)),fixed=cp.execFileSync('git',['show',commit+':'+file],{cwd:root});assert.equal(original.toString('utf8').replace(/\r\n/g,'\n'),fixed.toString('utf8').replace(/\r\n/g,'\n'),'commit client changes before preparing phone project: '+file);const name=file.slice('miniapp/'.length);let bytes=original;
 if(name==='adapters/storage.js')bytes=Buffer.from(original.toString('utf8').replace("'racepick.mini.'", "'racepick.devicecheck.20261103.'"));
 if(name==='pages/home/home.js')bytes=Buffer.from(original.toString('utf8').replace("'racepick.mini.view.v1.'", "'racepick.devicecheck.20261103.view.v1.'"));
 if(name==='pages/home/home.wxml')bytes=Buffer.from(original.toString('utf8').replace('本地计算 · 数据未冻结 · 识图尚未接入','离线真机验收 · 独立测试存储 · 识图未接入'));
 if(name==='project.config.json'){const config=JSON.parse(bytes);config.projectname='RacePick-phone-local';config.description='Isolated offline device acceptance, no native backend';bytes=Buffer.from(JSON.stringify(config,null,2)+'\n');}
 write(name,bytes,file);
}
// Actual identity stopped being tracked; inherit only the local App ID, never private settings or secrets.
const localProject=JSON.parse(fs.readFileSync(path.join(root,'miniapp/project.config.json'),'utf8'));
require('./setup_miniapp_project.cjs').setup(out,localProject.appid);
const phoneProject=JSON.parse(fs.readFileSync(path.join(out,'project.config.json'),'utf8'));phoneProject.projectname='RacePick-phone-local';phoneProject.description='Isolated offline device acceptance';phoneProject.setting.urlCheck=true;write('project.config.json',Buffer.from(JSON.stringify(phoneProject,null,2)+'\n'),'local-only project identity');
for(const name of [...Object.keys(provenance.files),'home_presenter.js','feature_contract.js','theme.wxss','functional_theme.wxss','source.json']){const bytes=fs.readFileSync(path.join(root,'miniapp/shared',name));if(provenance.files[name])assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),provenance.files[name].sha256);write('shared/'+name,bytes,'fixed generated dependency');}
const bundle=fs.readFileSync(path.join(root,'miniapp/generated/local-bundle.js'));require('../miniapp/adapters/snapshot').verifyLocalBundle(require('../miniapp/generated/local-bundle'));write('generated/local-bundle.js',bundle,'approved unfrozen runtime receipt');write('generated/native-config.js',Buffer.from('module.exports = {enabled:false};\n'),'offline adapter');
write('generated/account-config.js',Buffer.from('module.exports = {enabled:false};\n'),'offline account disabled');
write('generated/build-info.js',Buffer.from('module.exports='+JSON.stringify({buildId:crypto.createHash('sha256').update(out+commit).digest('hex').slice(0,20)})+';\n'),'independent build identity');
const core=require(path.join(out,'shared/selection_core')),service=require(path.join(out,'services/local')).createLocalService(core,require(path.join(out,'generated/local-bundle')));
report.calculations={};for(const server of ['cn','global']){const d={schema:1,server,zone:'zone5',tier:service.defaults(server).tier,maps:[null,null,null,null,null],cars:[],stars:{},oc:{},routes:{}};const model=service.model(d);d.maps[0]=model.maps[0];d.cars=model.cars.map(c=>c.id);const r=service.calculate(d);assert.ok(r.schemes.length);report.calculations[server]={cars:d.cars.length,schemes:r.schemes.length};}
const keys=[],storage=require(path.join(out,'adapters/storage')).createStorage({getStorageSync:k=>{keys.push(k);return '';},setStorageSync(){},removeStorageSync(){}},'local');storage.read('cn');assert.ok(keys.every(k=>k.startsWith(report.storagePrefix)));report.independentStorageVerified=true;
fs.writeFileSync(path.join(path.dirname(out),'phone-local-receipt.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({project:out,commit,independentStorage:true,calculations:report.calculations,previewInvoked:false}));
