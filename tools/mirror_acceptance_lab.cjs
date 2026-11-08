'use strict';
// Local acceptance fixtures only. Passwords, cookies and tokens stay in this process.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),cp=require('node:child_process'),assert=require('node:assert/strict');
const {createNativeApi}=require('../miniapp/adapters/native_api');
const {createAccountClient}=require('../miniapp/services/account');
const runtimeRoot='C:/Users/asus/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {chromium}=require(path.join(runtimeRoot,'playwright'));
const automator=require('../../offline-evaluation/miniprogram-v1-20261102-03/automation/node_modules/miniprogram-automator');
const key=()=>crypto.randomBytes(16).toString('hex');
class Acceptance {
 constructor(lab,out,origin='http://127.0.0.1:8056'){this.root=path.resolve(__dirname,'../..');this.lab=path.resolve(lab);this.out=path.resolve(out);this.origin=origin;assert.ok(/^http:\/\/127\.0\.0\.1:805[678]$/.test(origin));
  assert.ok(this.lab.startsWith(path.join(this.root,'.score-version-sandboxes')+path.sep));const mark=JSON.parse(fs.readFileSync(path.join(this.lab,'mini-integration.json'),'utf8'));assert.equal(mark.production,false);assert.equal(mark.full_mirror,true);assert.equal(mark.lab,this.lab);fs.mkdirSync(this.out,{recursive:true});
  this.users={};this.web={};this.report={fixtureOnly:true,realWechat:false,realDevice:false,checks:[],screens:[],errors:[]};this.temp=[];this.backup=new Map();
  this.wx={getSystemInfoSync:()=>({platform:'devtools'}),getRandomValues:o=>{const b=crypto.randomBytes(16);o.success({randomValues:b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength)});},getFileSystemManager:()=>({unlink(){}}),request:o=>{const abort=new AbortController();fetch(o.url,{method:o.method||'GET',headers:o.header,body:o.data===undefined?undefined:JSON.stringify(o.data),signal:abort.signal,redirect:'error'}).then(async r=>o.success({statusCode:r.status,header:Object.fromEntries(r.headers),data:await r.arrayBuffer()})).catch(()=>o.fail({errMsg:'local fixture request incomplete'}));return {abort:()=>abort.abort()};}};
  const config={enabled:true,kind:'fixture',origin:this.origin,fixtureCode:'fixture-code-2',fixtureKey:'acceptance-seed-20261103-01'};
  this.guest=createNativeApi(this.wx,config);this.native=createAccountClient(this.wx,config,this.guest);
 }
 check(name,extra={}){this.report.checks.push({name,...extra});this.save();return name;}
 save(){fs.writeFileSync(path.join(this.out,'acceptance.json'),JSON.stringify(this.report,null,2));}
 async seed(){await this.guest.session.ensure();const info=await this.guest.accountRequest('/session');assert.equal(info.features.authentication.mail_mode,'file');
  const suffix=key().slice(0,8);
  for(const role of ['player','admin','superadmin','target']){if(this.users[role])continue;const email='accept-'+role+'-'+suffix+'@example.test',password=crypto.randomBytes(30).toString('base64url');await this.native.auth('register',{email,password});
   const mail=fs.readdirSync(path.join(this.lab,'accounts','outbox')).map(n=>JSON.parse(fs.readFileSync(path.join(this.lab,'accounts','outbox',n),'utf8'))).find(m=>m.to===email&&m.purpose==='verify');assert.ok(mail);
   await this.native.auth('verify-email',{token:new URLSearchParams(new URL(mail.url).hash.slice(1)).get('token')});
   if(['admin','superadmin'].includes(role))cp.execFileSync('C:/Python314/python.exe',['-B','-X','utf8','-m','backend.roles','--data-dir',path.join(this.lab,'accounts'),'--email',email,'--role',role],{cwd:path.join(this.root,'map-layout-parser'),stdio:'pipe',env:{...process.env,PYTHONPATH:'C:/Users/asus/AppData/Roaming/Python/Python314/site-packages'}});
   this.users[role]={email,password};
  }
  await this.nativeLogin('player');
  const data=JSON.parse(fs.readFileSync(path.join(this.lab,'reference','gauntlet_data.json'),'utf8'));
  const entries=data.tracks.filter(t=>t.五区?.理论?.some(e=>Number.isFinite(e.time))).slice(0,4).map(t=>{const e=t.五区.理论.find(e=>Number.isFinite(e.time));return {server:'cn',big:t.大地图,small:t.小地图,zone:'五区',tier:'理论',car:e.cars[0].name,stars:null,route:e.sc_type||'',oc:false,time:String(Math.round((e.time-.001)*1000)/1000),notes:'独立本地验收夹具，非真实成绩投稿'};});
  const request_key=key(),draft=await this.native.call('/submissions',{method:'POST',key:request_key,data:{request_key,entries}});this.ids={scores:draft.ids,draft:draft.ids[3]};
  for(const id of draft.ids.slice(0,3))await this.native.call('/submissions/'+id+'/submit',{method:'POST',data:{revision:1}});
  const feedbackKey=key(),feedback=await this.native.call('/feedback',{method:'POST',key:feedbackKey,data:{request_key:feedbackKey,category:'bug',title:'手机页面验收样例',description:'这是新建本地隔离库的测试反馈。',steps:'选择地图，然后展开车库。',expected:'暗色控件保持一致',actual:'等待本轮验收',source_page:'/'}});this.ids.feedback=feedback.id;
  await this.nativeLogin('superadmin');const news=await this.native.call('/admin/announcements',{method:'POST',data:{title:'本地验收公告',body:'用于核对公告排版、提醒及忽略状态。\n不代表真实网站公告。',release_label:'本地样例'}});await this.native.call('/admin/announcements/'+news.id+'/state',{method:'POST',data:{revision:news.revision,action:'publish'}});this.ids.news=news.id;
  this.check('新lab注册四个独立测试身份，准备投稿/反馈/公告；无真实邮件');return {roles:Object.keys(this.users),submissions:this.ids.scores.length};
 }
 async nativeLogin(role){const user=this.users[role];const s=await this.native.auth('login',{email:user.email,password:user.password});user.id=s.actor.id;return s.actor.role;}
 async recoverOwnedFixtures(){await this.guest.session.ensure();const mails=fs.readdirSync(path.join(this.lab,'accounts','outbox')).map(n=>JSON.parse(fs.readFileSync(path.join(this.lab,'accounts','outbox',n),'utf8')));
  for(const role of ['player','admin','superadmin','target']){const mail=mails.find(m=>m.purpose==='verify'&&m.to.startsWith('accept-'+role+'-'));assert.ok(mail);const user={email:mail.to,password:crypto.randomBytes(30).toString('base64url')};await this.native.auth('forgot-password',{email:user.email});const reset=fs.readdirSync(path.join(this.lab,'accounts','outbox')).map(n=>JSON.parse(fs.readFileSync(path.join(this.lab,'accounts','outbox',n),'utf8'))).filter(m=>m.to===user.email&&m.purpose==='reset').at(-1);await this.native.auth('reset-password',{token:new URLSearchParams(new URL(reset.url).hash.slice(1)).get('token'),password:user.password});this.users[role]=user;}
  await this.nativeLogin('player');const scores=await this.native.call('/submissions?scope=mine&status=&q=&offset=0&server=cn'),tickets=await this.native.call('/feedback?status=all&offset=0&q=');this.ids={scores:scores.items.map(x=>x.id),draft:scores.items.find(x=>x.status==='draft').id,feedback:tickets.items[0].id};
  const report=path.join(this.out,'acceptance.json');if(fs.existsSync(report))this.report=JSON.parse(fs.readFileSync(report,'utf8'));return {roles:Object.keys(this.users),scores:this.ids.scores.length};
 }
 async browserStart(){this.browserInstance=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});return 'fresh headless Chrome contexts';}
 async browser(role){if(!this.browserInstance)await this.browserStart();if(this.web[role])return this.web[role].page;
  const context=await this.browserInstance.newContext({viewport:{width:390,height:753}});await context.route('**/*',route=>{const u=new URL(route.request().url());if(u.origin!==this.origin&&!['data:','blob:'].includes(u.protocol))return route.abort();if(u.pathname==='/map_recognition.js'){const body=cp.execFileSync('git',['show','8da16097978500f1a127cc92ada09fcc1a653f2b:map_recognition.js'],{cwd:path.join(this.root,'miniprogram-v1')});return route.fulfill({status:200,contentType:'application/javascript',body});}return route.continue();});
  const page=await context.newPage();page.on('pageerror',e=>{this.report.errors.push('web '+role+': '+e.message);this.save();});this.web[role]={context,page};
  page.setDefaultTimeout(8000);await page.goto(this.origin+'/?server=cn');await page.waitForSelector('#accountOpenLogin');
  if(role!=='guest'){await page.locator('#accountOpenLogin').click();await page.locator('#accountEmail').fill(this.users[role].email);await page.locator('#accountPassword').fill(this.users[role].password);await page.locator('#accountAuthSubmit').click();await page.waitForFunction(()=>globalThis.accountUI?.active?.(),null,{timeout:30000});}
  return page;
 }
 async webShot(role,route,name,ready){const page=await this.browser(role);await page.goto(this.origin+route);if(ready)await page.waitForSelector(ready,{timeout:8000});await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:path.join(this.out,'web-'+name+'.png'),fullPage:true});
  const layout=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,bodyColor:getComputedStyle(document.body).backgroundColor,bodyFont:getComputedStyle(document.body).fontSize}));this.report.screens.push({platform:'web',role,name,route,...layout});this.save();return layout;
 }
 async connect(){this.app=await automator.connect({wsEndpoint:'ws://127.0.0.1:9420'});this.app.on('exception',e=>{this.report.errors.push('native: '+String(e.message||e));this.save();});
  await this.stable('pages/home/home');const s=await this.app.evaluate(()=>getCurrentPages().slice(-1)[0].account.state());assert.equal(s.actor,null,'do not replace a user account session');
  const keys=(await this.app.callWxMethod('getStorageInfoSync')).keys;
  for(const server of ['cn','global'])for(const k of ['racepick.mini.native-fixture.draft.v1.'+server,'racepick.mini.native-fixture.working.v1.'+server,'racepick.mini.view.v1.native-fixture.'+server])if(!this.backup.has(k))this.backup.set(k,{exists:keys.includes(k),value:await this.app.callWxMethod('getStorageSync',k)});
  this.report.system=await this.app.systemInfo();this.save();return this.report.system.SDKVersion;
 }
 async stable(route){for(let i=0;i<80;i++){try{const p=await this.app.currentPage();if(p&&p.path===route){this.page=p;return p;}}catch(_){}await new Promise(r=>setTimeout(r,100));}throw Error('route not settled: '+route);}
 async wait(fn){for(let i=0;i<140;i++){if(await fn())return;await new Promise(r=>setTimeout(r,150));}throw Error('bounded acceptance wait exceeded');}
 async invoke(method,...args){return this.app.evaluate((name,values)=>{const p=getCurrentPages().slice(-1)[0];if(typeof p[name]!=='function')throw Error('missing handler '+name);return p[name](...values);},method,args);}
 async navigate(route){await this.app.callWxMethod('navigateTo',{url:route});return this.stable(route.split('?')[0].slice(1));}
 async home(){await this.app.callWxMethod('reLaunch',{url:'/pages/home/home'});await this.stable('pages/home/home');await this.wait(async()=>await this.page.data('ready'));}
 async login(role,expectedRole=role==='target'?'player':role){if(this.page.path!=='pages/home/home')await this.home();await this.navigate('/pages/account/account');if(await this.page.data('actor'))await this.invoke('logout');await this.invoke('changeMode',{detail:{value:'login'}});
  for(const k of ['email','password']){await this.wait(async()=>{this.page=await this.app.currentPage();return !!await this.page.$('input[data-key="'+k+'"]');});await(await this.page.$('input[data-key="'+k+'"]')).input(this.users[role][k]);await this.wait(async()=>await this.page.data(k)===this.users[role][k]);}
  await this.invoke('submit');await this.wait(async()=>!await this.page.data('busy'));const e=await this.page.data('error');if(e)throw Error(e);assert.equal((await this.page.data('actor')).role,expectedRole);this.users[role].id=(await this.page.data('actor')).id;await this.app.callWxMethod('navigateBack',{delta:1});await this.stable('pages/home/home');await this.wait(()=>this.app.evaluate(()=>!!getCurrentPages().slice(-1)[0].cloudReady));this.role=role;return role;
 }
 async shot(name,selector){if(!selector)await this.app.callWxMethod('pageScrollTo',{scrollTop:0,duration:0});if(selector){const element=await this.page.$(selector);if(element){await this.app.pageScrollTo(0);const offset=await element.offset();await this.app.pageScrollTo(Math.max(0,offset.top-10));}}
  await this.app.screenshot({path:path.join(this.out,'native-'+name+'.png')});this.report.screens.push({platform:'native',role:this.role||'guest',name,route:this.page.path});this.save();return name;
 }
 async tab(tab){await this.invoke('changeTab',{detail:{value:tab}});await this.wait(async()=>!await this.page.data('busy'));const error=await this.page.data('error');if(error)throw Error(error);}
 async confirm(method,args=[]){await this.app.mockWxMethod('showModal',{confirm:true,cancel:false});try{await this.page.setData({error:'',message:''});await this.invoke(method,...args);await this.wait(async()=>!await this.page.data('busy')&&!!((await this.page.data('error'))||(await this.page.data('message'))));const error=await this.page.data('error');if(error)throw Error(error);}finally{await this.app.restoreWxMethod('showModal');}}
 async finish(){if(this.app){try{await this.app.evaluate(async()=>{const pages=getCurrentPages(),home=pages.find(p=>p.account);if(home?.account.state().actor)await home.account.logout();for(const p of pages)if(p.controller)p.controller.destroy();});for(const [k,b] of this.backup)if(b.exists)await this.app.callWxMethod('setStorageSync',k,b.value);else await this.app.callWxMethod('removeStorageSync',k);const keys=(await this.app.callWxMethod('getStorageInfoSync')).keys;for(const [k,b] of this.backup){assert.equal(keys.includes(k),b.exists);if(b.exists)assert.deepEqual(await this.app.callWxMethod('getStorageSync',k),b.value);}const ownedIds=Object.values(this.users).map(x=>x.id).filter(Boolean);for(const k of keys)if(k.startsWith('racepick.mini.')&&ownedIds.some(id=>k.includes(id)))await this.app.callWxMethod('removeStorageSync',k);this.report.guestStorageRestored=true;}finally{await this.app.disconnect();}}if(this.browserInstance)await this.browserInstance.close();this.save();return {checks:this.report.checks.length,errors:this.report.errors};}
}
module.exports={Acceptance};
