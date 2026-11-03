'use strict';
// Independent DevTools project: session + two verified snapshots, no media/account/business requests.
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {readProfile,platformConfig}=require('./native_profile.cjs');
const root=path.resolve(__dirname,'..'),workspace=path.dirname(root),out=path.resolve(process.argv[2]||'');
assert.ok(out.startsWith(path.join(workspace,'offline-evaluation')+path.sep),'probe must stay in offline-evaluation');assert.ok(!fs.existsSync(out),'do not overwrite an existing probe project');
const profileIndex=process.argv.indexOf('--profile'),file=profileIndex<0?path.join(root,'miniapp/platform.profile.local.json'):path.resolve(process.argv[profileIndex+1]||'');
const profile=readProfile(file);let native={enabled:false},waiting='等待网站/运维确认隔离HTTPS、真实微信验证和request域名';
const expectedIndex=process.argv.indexOf('--expected'),expected=expectedIndex<0?null:JSON.parse(fs.readFileSync(path.resolve(process.argv[expectedIndex+1]),'utf8'));
if(profile.origin&&profile.isolatedServiceDeclared&&profile.realWechatConfiguredDeclared&&profile.requestDomainConfiguredDeclared){native=platformConfig(profile);waiting='等待点击检查';}
else if(profile.origin)require('../miniapp/adapters/native_config').validateNativeConfig({enabled:true,kind:'platform',origin:profile.origin});
if(native.enabled){assert.ok(expected&&expected.schema===1&&expected.origin===native.origin,'enabled network checks require an explicit fixed delivery receipt');}
const local=JSON.parse(fs.readFileSync(path.join(root,'miniapp/project.config.json'),'utf8'));assert.ok(/^wx[0-9a-f]{16}$/i.test(local.appid),'local real App ID must be configured first');
const report={source:cp.execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(),sourceDirty:!!cp.execFileSync('git',['status','--porcelain'],{cwd:root,encoding:'utf8'}).trim(),enabled:native.enabled,origin:native.enabled?native.origin:null,appIdLocalOnly:true,domainRegistrationVerified:false,networkExecuted:false,uploads:false,accountRequests:false,files:{}};
function write(name,bytes){const target=path.join(out,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,bytes);report.files[name]={sha256:crypto.createHash('sha256').update(bytes).digest('hex')};}
for(const name of ['adapters/native_config.js','adapters/native_api.js','adapters/session.js','adapters/transport.js','adapters/hash.js','adapters/id.js','adapters/snapshot.js','services/network_probe.js'])write(name,fs.readFileSync(path.join(root,'miniapp',name)));
write('generated/native-config.js','module.exports = '+JSON.stringify(native)+';\n');
write('generated/expected.js','module.exports = '+JSON.stringify(expected)+';\n');
write('app.js','App({});\n');write('app.json',JSON.stringify({pages:['pages/probe/probe'],window:{navigationBarTitleText:'网络基础检查',navigationBarBackgroundColor:'#0d1117',navigationBarTextStyle:'white'},style:'v2'}));
const project={...local,projectname:'RacePick-network-probe',description:'Private network acceptance only; no OCR/account/business requests',setting:{...local.setting,urlCheck:true}};write('project.config.json',JSON.stringify(project,null,2)+'\n');
write('pages/probe/probe.json','{}\n');
write('pages/probe/probe.js',`const config=require('../../generated/native-config'),expected=require('../../generated/expected'),{createNetworkProbe}=require('../../services/network_probe');
Page({data:{enabled:config.enabled,busy:false,message:${JSON.stringify(waiting)},report:''},onLoad(){if(config.enabled)this.probe=createNetworkProbe(wx,config,expected);},async run(){if(!this.probe||this.data.busy)return;this.setData({busy:true,message:'正在检查会话与两服原字节快照…'});try{await this.probe.run();if(!this.unloaded)this.setData({message:'网络基础检查通过；OCR与账号尚未验收'});}catch(_){if(!this.unloaded)this.setData({message:'检查未通过，请按失败阶段/状态码核对；不自动换代码或重放请求'});}finally{if(!this.unloaded)this.setData({busy:false,report:JSON.stringify(this.probe.report(),null,2)});}},onUnload(){this.unloaded=true;if(this.probe)this.probe.dispose();}});\n`);
write('pages/probe/probe.wxml','<view class="page"><view class="title">RacePick 网络基础检查</view><view class="note">诊断版 2 · 独立开发者检查工程 · 不上传图片，不访问账号或业务写接口</view><view>{{message}}</view><button disabled="{{!enabled || busy}}" loading="{{busy}}" bindtap="run">检查微信访客会话与快照</button><text class="report" selectable="{{true}}">{{report}}</text></view>');
write('pages/probe/probe.wxss','page{background:#0d1117;color:#e6edf3;font:14px/1.6 system-ui}.page{padding:20px}.title{font-size:22px;font-weight:600}.note{color:#8b949e;margin:16px 0}button{margin:20px 0;background:#21262d;color:#e6edf3;border:1px solid #30363d;font-size:14px}button[disabled]{background:#161b22;color:#6e7681}.report{display:block;white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}');
fs.writeFileSync(path.join(path.dirname(out),'network-probe-receipt.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({project:out,enabled:native.enabled,networkExecuted:false,appIdLocalOnly:true}));
