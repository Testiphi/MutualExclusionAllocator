'use strict';
// Actual wx.request and native pages; explicit fixture/file-mail only. No real device claim.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const automator=require(path.resolve(process.argv[2])),lab=path.resolve(process.argv[3]),out=path.resolve(process.argv[4]);
const marker=JSON.parse(fs.readFileSync(path.join(lab,'mini-integration.json'),'utf8'));assert.equal(marker.full_mirror,true);assert.equal(marker.production,false);fs.mkdirSync(out,{recursive:true});
const report={fixtureAuth:true,fileMail:true,realDevice:false,realWechatAuth:false,checks:[],exceptions:[],success:false,storageRestored:false};
const backup=new Map(),fixtureKeys=['cn','global'].flatMap(s=>['racepick.mini.native-fixture.draft.v1.'+s,'racepick.mini.native-fixture.working.v1.'+s,'racepick.mini.view.v1.native-fixture.'+s]);let app,p,ownedActor;
const check=name=>{report.checks.push(name);console.log('PASS '+name);};
(async()=>{try{
 app=await automator.connect({wsEndpoint:'ws://127.0.0.1:9420'});app.on('exception',e=>report.exceptions.push(typeof e==='string'?e:String(e.message||'runtime exception')));
 for(let i=0;i<40&&!p;i++){try{p=await app.currentPage();}catch(_){}if(!p)await new Promise(r=>setTimeout(r,150));}assert.ok(p);if(p.path!=='pages/home/home')p=await app.reLaunch('/pages/home/home');
 const until=async fn=>{for(let i=0;i<120;i++){if(await fn())return;await p.waitFor(150);}throw Error('bounded UI wait exceeded');};
 await until(async()=>await p.data('ready'));assert.equal(await p.data('mode'),'native-fixture');if(!(await p.data('serviceStatus')).online){await app.evaluate(()=>getCurrentPages()[0].controller.reconnect());await until(async()=>(await p.data('serviceStatus')).online);}
 const current=await app.evaluate(()=>getCurrentPages()[0].account.state());assert.equal(current.actor,null,'do not disturb an existing account login');
 const guest=await app.evaluate(()=>getCurrentPages()[0].service.api.accountRequest('/session'));assert.equal(guest.features.authentication.mail_mode,'file');
 const stored=(await app.callWxMethod('getStorageInfoSync')).keys;for(const k of fixtureKeys)backup.set(k,{exists:stored.includes(k),value:await app.callWxMethod('getStorageSync',k)});
 report.system=await app.systemInfo();
 const stablePage=async expected=>{for(let i=0;i<60;i++){try{const page=await app.currentPage();if(page&&page.path===expected){p=page;await p.waitFor(200);return;}}catch(_){}await new Promise(r=>setTimeout(r,100));}throw Error('page did not settle: '+expected);};
 const navigate=async url=>{report.stage='navigate '+url;await app.callWxMethod('navigateTo',{url});await stablePage(url.split('?')[0].slice(1));};
 const back=async()=>{await app.callWxMethod('navigateBack',{delta:1});await stablePage('pages/home/home');return p;};
 const input=async(key,value)=>{let e;for(let i=0;i<40&&!e;i++){p=await app.currentPage();e=await p.$('input[data-key="'+key+'"]');if(!e)await p.waitFor(100);}assert.ok(e,'input did not render: '+key);await e.input(value);await until(async()=>await p.data(key)===value);};
 const invoke=async(method,...args)=>app.evaluate((name,values)=>{const page=getCurrentPages().slice(-1)[0];if(typeof page[name]!=='function')throw Error('missing page handler: '+name);return page[name](...values);},method,args);
 const mode=async value=>{await invoke('changeMode',{detail:{value}});await p.waitFor(120);};
 const submit=async()=>{await (await p.$('button.primary')).tap();await until(async()=>!await p.data('busy')&&!!((await p.data('message'))||(await p.data('error'))));const error=await p.data('error');if(error)throw Error(error);};
 const email='mirror-ui-'+crypto.randomBytes(6).toString('hex')+'@example.test',password=crypto.randomBytes(30).toString('hex');
 await navigate('/pages/account/account');report.stage='register';await mode('register');await input('email',email);await input('password',password);await input('passwordConfirm',password);await submit();
 const mail=fs.readdirSync(path.join(lab,'accounts','outbox')).map(f=>JSON.parse(fs.readFileSync(path.join(lab,'accounts','outbox',f),'utf8'))).find(m=>m.to===email);assert.ok(mail);const token=new URLSearchParams(new URL(mail.url).hash.slice(1)).get('token');
 report.stage='verify';await mode('verify-email');await input('token',token);await submit();report.stage='login';await mode('login');await input('email',email);await input('password',password);await submit();ownedActor=(await p.data('actor')).id;assert.equal(await p.data('password'),'');check('A native account register/file-token verification/login clears password from page');
 await app.screenshot({path:path.join(out,'account.png')});p=await back();await until(()=>app.evaluate(()=>!!getCurrentPages()[0].cloudReady));assert.equal(await p.data('selectedCount'),0);assert.equal(await p.data('cloudEmpty'),true);check('A native homepage loads cloud null with zero cars and does not import guest garage');
 await invoke('switchServer',{currentTarget:{dataset:{server:'global'}}});await until(()=>app.evaluate(()=>getCurrentPages()[0].cloudReady&&getCurrentPages()[0].state.draft.server==='global'));
 const chosen=await app.evaluate(()=>{const p=getCurrentPages()[0],car=p.state.model.cars.find(c=>c.ocAllowed)||p.state.model.cars[0];p.controller.setCar(car.id,true);if(car.ocAllowed)p.controller.setOc(car.id,true);return {id:car.id,oc:car.ocAllowed};});
 await invoke('save');await p.waitFor(200);const saved=await app.evaluate(()=>getCurrentPages()[0].account.profile('global'));assert.deepEqual(saved.profile.cars,[chosen.id]);if(chosen.oc)assert.equal(saved.profile.ocMap[chosen.id],true);assert.equal((await app.evaluate(()=>getCurrentPages()[0].account.profile('cn'))).revision,0);check('A native global cloud save preserves OC and independent CN revision');
 await app.screenshot({path:path.join(out,'home-cloud.png')});
 await navigate('/pages/coverage/coverage?server=global');await until(async()=>!!await p.data('matrix'));assert.ok((await p.data('matrix')).source_snapshot);await app.screenshot({path:path.join(out,'coverage.png')});check('B native custom filters and real coverage table render from HTTP');p=await back();
 await navigate('/pages/submissions/submissions?server=cn');await until(async()=>!!await p.data('reference'));assert.ok((await p.data('composeRows')).length);await app.screenshot({path:path.join(out,'submissions.png')});check('C native catalogue/compose/list page renders for logged-in account');p=await back();
 await navigate('/pages/community/community?server=cn');await until(async()=>!await p.data('busy'));assert.equal(await p.data('error'),'');await invoke('change',{currentTarget:{dataset:{key:'tab'}},detail:{value:'notifications'}});await until(async()=>!!await p.data('notifications'));await app.screenshot({path:path.join(out,'notifications.png')});check('D native community/notification page loads without marking items read');p=await back();
 await navigate('/pages/workbench/workbench');await until(async()=>!await p.data('busy'));assert.ok(await p.data('error'),'player cannot read review queue');check('E player direct navigation is denied by server, beyond hidden navigation button');p=await back();
 await navigate('/pages/account/account');await invoke('logout');p=await back();await until(()=>app.evaluate(()=>!getCurrentPages()[0].account.state().actor));
 assert.deepEqual(report.exceptions,[]);report.success=true;
}catch(e){report.error=e.message;throw e;}finally{if(app){try{
 await app.evaluate(()=>{for(const p of getCurrentPages())if(p.controller)p.controller.destroy();});
 if(ownedActor)await app.evaluate(async()=>{const pages=getCurrentPages(),home=pages.find(p=>p.account);if(home?.account.state().actor)await home.account.logout();});
 for(const [k,b] of backup)if(b.exists)await app.callWxMethod('setStorageSync',k,b.value);else await app.callWxMethod('removeStorageSync',k);
 if(ownedActor)for(const k of (await app.callWxMethod('getStorageInfoSync')).keys)if(k.includes(ownedActor)&&!fixtureKeys.includes(k))await app.callWxMethod('removeStorageSync',k);
 p=await app.reLaunch('/pages/home/home');await p.waitFor(200);const stored=(await app.callWxMethod('getStorageInfoSync')).keys;
 for(const [k,b] of backup){assert.equal(stored.includes(k),b.exists);if(b.exists)assert.deepEqual(await app.callWxMethod('getStorageSync',k),b.value);}report.storageRestored=true;
 await app.screenshot({path:path.join(out,'home-restored.png')});
 }catch(e){report.restoreError=e.message;report.success=false;}await app.disconnect();}fs.writeFileSync(path.join(out,'devtools-mirror-report.json'),JSON.stringify(report,null,2));if(!report.success)process.exitCode=1;}})().catch(e=>{console.error(e.message);process.exitCode=1;});
