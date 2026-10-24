'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {createHash, webcrypto} = require('node:crypto');
const read = name => fs.readFileSync(path.join(__dirname, name), 'utf8');
const encode = value => Buffer.from(JSON.stringify(value));
const hash = raw => createHash('sha256').update(raw).digest('hex');

function fixture({mismatch = false, corrupt = false} = {}) {
    const meta = {server_id:'global', schema_version:1, dataset_version:'fixture-version', catalog_payload_sha256:'a'.repeat(64), scores_payload_sha256:'b'.repeat(64), manifest_file:'global-data-manifest.json'};
    const cars = {_meta:{...meta}, _nickname_map:{}, cars:[
        {title:'Jesko', nickname:'杰哥', score:4800, class:'S', zones:['五区'], star_rule:{min:1,max:6}},
        {title:'Dendrobium', nickname:'万达', score:4100, class:'A', zones:['五区'], star_rule:{min:1,max:5}},
        {title:'Chiron', nickname:'evo肥龙', score:null, class:null, zones:['五区'], star_rule:{min:1,max:6}}
    ]};
    const track = (small, entries) => ({大地图:'测试', 小地图:small, 五区:{理论:entries,高手:[],普通:[],自动:[]},四区:{理论:[],高手:[],普通:[],自动:[]}});
    const data = {_meta:{...meta}, tracks:[
        track('有OC', [{cars:[{name:'杰哥'}],time:30},{cars:[{name:'杰哥',oc:true}],time:29},{cars:[{name:'万达'}],time:31},{cars:[{name:'万达',oc:true}],time:28}]),
        track('无OC', [{cars:[{name:'杰哥'}],time:20},{cars:[{name:'evo肥龙'}],time:22}])
    ]};
    if (mismatch) cars._meta.dataset_version = 'other-version';
    const rawCars = encode(cars), rawData = encode(data);
    const manifest = {_meta:meta, files:{
        'cars.global.json':{sha256:hash(rawCars), bytes:rawCars.length, payload_sha256:meta.catalog_payload_sha256},
        'gauntlet_data.global.json':{sha256:hash(rawData), bytes:rawData.length, payload_sha256:meta.scores_payload_sha256}
    }};
    return new Map([['cars.global.json', corrupt ? Buffer.concat([rawCars,Buffer.from(' ')]) : rawCars], ['gauntlet_data.global.json',rawData], ['global-data-manifest.json',encode(manifest)]]);
}

function storage(initial = {}) {
    const values = new Map(Object.entries(initial)), writes = [];
    return {values, writes, getItem:key=>values.get(key)??null, setItem(key,value){writes.push(key);values.set(key,String(value));}, removeItem(key){writes.push(key);values.delete(key);}};
}

function dom() {
    const nodes = new Map(); let serial = 0;
    function node(id) {
        if (nodes.has(id)) return nodes.get(id);
        const children = [], events = new Map(), attrs = new Map(), classes = new Set();
        let html = '';
        const value = {id, children, options:children, events, dataset:{},style:{},value:'',textContent:'',hidden:false,disabled:false,
            classList:{add:c=>classes.add(c),remove:c=>classes.delete(c),contains:c=>classes.has(c),toggle(c,on){if(on===undefined)on=!classes.has(c);if(on)classes.add(c);else classes.delete(c);}},
            appendChild(child){children.push(child);child.parentNode=value;return child;}, append(...items){items.forEach(item=>value.appendChild(item));},
            replaceChildren(...items){children.length=0;value.append(...items);},
            querySelector:selector=>node(id+':'+selector), querySelectorAll:()=>[],
            setAttribute:(key,entry)=>attrs.set(key,String(entry)),getAttribute:key=>attrs.get(key)??null,removeAttribute:key=>attrs.delete(key),
            addEventListener(type,callback){events.set(type,callback);}, removeEventListener(){},
            remove(){},focus(){},close(){},showModal(){queueMicrotask(()=>children.at(-1)?.onclick?.());}};
        Object.defineProperty(value,'innerHTML',{get:()=>html,set:entry=>{html=String(entry);children.length=0;}});
        nodes.set(id,value);return value;
    }
    return {nodes,node,document:{getElementById:node,createElement:tag=>node('new:'+tag+':'+(++serial)),createTextNode:()=>node('text:'+(++serial)),querySelector:selector=>node(selector),querySelectorAll:()=>[],addEventListener(){},body:node('body'),documentElement:node('html')}};
}

async function boot({files = fixture(), local = storage(), session = storage(), missing = null, accountActive = true, server = 'global', versioned = true, useAccountStub = true} = {}) {
    const ui = dom(), requests = [], errors = [], globalEvents = new Map(); let accountCalls = 0;
    const search = server === 'cn' ? '?foo=1' : '?server='+encodeURIComponent(server)+'&foo=1';
    const location = {search,href:'http://127.0.0.1:8000/nested/index.html'+search+'#old'};
    const context = vm.createContext({document:ui.document,location,URL,URLSearchParams,TextDecoder,TextEncoder,Uint8Array,crypto:webcrypto,
        localStorage:local,sessionStorage:session,console:{warn:(...args)=>errors.push(args.join(' ')),error:(...args)=>errors.push(args.join(' '))},
        setTimeout,clearTimeout,requestAnimationFrame:callback=>setTimeout(callback,0),addEventListener(type,callback){if(!globalEvents.has(type))globalEvents.set(type,[]);globalEvents.get(type).push(callback);},dispatchEvent(){},Event:class{},
        RACEPICK_VERSIONED_SCORES:versioned,
        accountUI:useAccountStub?{active:()=>accountActive,init(){accountCalls++;throw Error('global called account init');},garage(){accountCalls++;throw Error('global read account garage');},stars(){accountCalls++;throw Error('global read account stars');},saveNow(){accountCalls++;throw Error('global wrote account profile');},restore(){accountCalls++;throw Error('global restored account profile');}}:undefined,
        fetch:async url=>{requests.push(String(url));const raw = files.get(String(url));return {ok:!!raw&&url!==missing,status:raw?200:404,arrayBuffer:async()=>raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength),json:async()=>JSON.parse(raw.toString())};}});
    let inline = read('index.html').match(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/)[1];
    inline = inline.replace(/initApp\(\);/, `globalThis.__page = {state:()=>({zone:currentZone,tier:currentTier,owned:[...selectedCars],ocMap:{...ocMap},rules:CAR_STAR_RULES,dirty:guestDirty,bigMapList:[...bigMapList]}),profile:profileNow,score:getCarScore,groups:getOriginalGroups,stars:getCarStars,setStars:setCarStars,commit:commitGarage,restore:restoreGarage,clear:clearAll,selectAll,sort:sortCarList};globalThis.__boot = initApp();`);
    vm.runInContext([read('config.js'),read('app_state.js'),read('api.js'),read('allocator.js'),read('race_scores.js'),inline].join('\n;\n'),context);
    await context.__boot;
    return {context,page:context.__page,requests,errors,local,session,globalEvents,...ui,accountCalls:()=>accountCalls};
}

const cnLocal = {'racepick.guest-profile.v1':JSON.stringify({cars:['国服车'],stars:{国服车:2}}),garageCars:'["国服旧车"]',starsMap:'{"国服旧车":3}',zoneMode:'"zone4"',sortMode:'"score-desc"'};
const cnSession = {'racepick.guest-draft.v1':'{"base":"national-draft-kept"}','racepick.account-draft.v1.some-user':'{"untouched":true}'};

test('global boot keeps one verified pair, fixed five-zone theory and skips all account/CN data paths',async()=>{
    const app = await boot({local:storage(cnLocal),session:storage(cnSession)});
    assert.deepEqual(app.errors,[]);assert.equal(app.accountCalls(),0);
    assert.deepEqual([...app.page.state().owned].sort(),['evo肥龙','万达','杰哥']);
    assert.equal(app.page.state().zone,'zone5');assert.equal(app.page.state().tier,'理论');
    assert.equal(app.page.stars('万达'),5);app.page.setStars('万达',1);assert.equal(app.page.stars('万达'),5);
    assert.equal(app.node('tierToggle').hidden,true);assert.equal(app.node('zoneToggle').hidden,true);assert.equal(app.node('classFilterR').hidden,true);
    assert.match(app.node('serverNote').textContent,/国际服车库保存于本机/);
    assert.equal(app.node('serverCnLink').href,'http://127.0.0.1:8000/nested/index.html?foo=1');
    assert.equal(app.requests.length,3);assert.ok(app.requests.every(url=>!url.includes('/api/')&&!['cars.json','gauntlet_data.json'].includes(url)));
    for (const [key,value] of Object.entries(cnLocal)) assert.equal(app.local.values.get(key),value);
    for (const [key,value] of Object.entries(cnSession)) assert.equal(app.session.values.get(key),value);
    const sorted = app.page.sort(['evo肥龙','万达','杰哥'],'score-asc');assert.equal(sorted.at(-1),'evo肥龙');
});

test('global OC is a state of the same owned car, persists with explicit local save, restores and never fills an OC gap with normal time',async()=>{
    const local = storage(cnLocal), session = storage(cnSession), app = await boot({local,session});
    assert.equal(app.page.score('测试','有OC','杰哥','zone5'),30);
    const ocButton = () => app.node('carGrid').children.flatMap(tag=>tag.children).find(button=>button.dataset.ocCar==='杰哥');
    assert.equal(ocButton().textContent,'OC');assert.equal(ocButton().getAttribute('aria-pressed'),'false');assert.equal(ocButton().getAttribute('aria-label'),'杰哥 OC超频');assert.equal(ocButton().type,'button');
    const click = app.node('carGrid').events.get('click');
    click({target:{closest:selector=>selector==='.oc-toggle'?{dataset:{ocCar:'杰哥'}}:null}});
    assert.equal(ocButton().textContent,'OC');assert.equal(ocButton().getAttribute('aria-pressed'),'true');
    assert.equal(app.page.score('测试','有OC','杰哥','zone5'),29);
    assert.equal(app.page.score('测试','无OC','杰哥','zone5'),null);
    assert.ok(!app.page.groups('测试','无OC','zone5').flat().includes('杰哥'));
    assert.equal(app.page.state().owned.filter(car=>car==='杰哥').length,1);
    assert.equal(app.local.values.has('racepick.guest-profile.v1.global'),false);
    assert.equal(JSON.parse(session.values.get('racepick.guest-draft.v1.global')).profile.ocMap.杰哥,true);
    await app.page.commit();
    const saved = JSON.parse(local.values.get('racepick.guest-profile.v1.global'));assert.equal(saved.ocMap.杰哥,true);
    assert.equal(session.values.has('racepick.guest-draft.v1.global'),false);assert.equal(app.accountCalls(),0);
    app.page.clear();assert.equal(app.page.state().owned.length,0);await app.page.restore();
    assert.equal(app.page.state().owned.length,3);assert.equal(app.page.state().ocMap.杰哥,true);assert.equal(app.page.state().dirty,false);
    const reloaded = await boot({local,session});assert.equal(reloaded.page.state().ocMap.杰哥,true);assert.equal(reloaded.page.score('测试','有OC','杰哥','zone5'),29);
    for (const [key,value] of Object.entries(cnLocal)) assert.equal(local.values.get(key),value);
    for (const [key,value] of Object.entries(cnSession)) assert.equal(session.values.get(key),value);
});

test('an explicitly empty global garage and its own unsaved draft stay independent of national state',async()=>{
    const local = storage({...cnLocal,'racepick.guest-profile.v1.global':JSON.stringify({cars:[],stars:{},ocMap:{}})});
    const app = await boot({local});assert.equal(app.page.state().owned.length,0);
    const base = local.values.get('racepick.guest-profile.v1.global');
    const session = storage({...cnSession,'racepick.guest-draft.v1.global':JSON.stringify({base,profile:{cars:['杰哥'],stars:{杰哥:1},ocMap:{杰哥:true}}})});
    const draft = await boot({local,session});assert.deepEqual([...draft.page.state().owned],['杰哥']);assert.equal(draft.page.state().ocMap.杰哥,true);assert.equal(draft.page.stars('杰哥'),6);assert.equal(draft.page.state().dirty,true);
    await draft.page.commit();assert.deepEqual(JSON.parse(local.values.get('racepick.guest-profile.v1.global')).cars,['杰哥']);
    assert.equal(local.values.get('racepick.guest-profile.v1'),cnLocal['racepick.guest-profile.v1']);
});

for (const [name, options, message] of [
    ['missing resource',{missing:'cars.global.json'},/国际服数据加载失败/],
    ['mixed catalogue and score versions',{files:fixture({mismatch:true})},/国际服车辆与成绩版本不一致/],
    ['tampered raw resource',{files:fixture({corrupt:true})},/国际服数据完整性校验失败/]
]) test('global rejects '+name+' without falling back to CN or opening the account profile',async()=>{
    const app=await boot(options);assert.match(app.node('mapRowsContainer').innerHTML,message);assert.equal(app.accountCalls(),0);
    assert.ok(app.requests.every(url=>['cars.global.json','gauntlet_data.global.json','global-data-manifest.json'].includes(url)));
    assert.equal(app.local.writes.length,0);
});

test('the actual global runtime bundle boots with 49 shared car identities, 44 tracks and all 21 direct or estimated OC values', async()=>{
    const names=['global-data-manifest.json','cars.global.json','gauntlet_data.global.json'];
    const files=new Map(names.map(name=>[name,fs.readFileSync(path.join(__dirname,name))]));
    const data=JSON.parse(files.get('gauntlet_data.global.json'));
    const app=await boot({files,local:storage(cnLocal),session:storage(cnSession)});
    assert.deepEqual(app.errors,[]);assert.equal(app.page.state().owned.length,49);assert.equal(data.tracks.length,44);
    assert.equal(app.accountCalls(),0);assert.equal(app.requests.length,3);
    const rows=data.tracks.flatMap(track=>track['五区']['理论'].filter(entry=>entry.cars[0].oc===true).map(entry=>({track,entry})));
    assert.equal(rows.length,21);
    for(const {track,entry} of rows){
        const car=entry.cars[0].name;
        if(!app.page.state().ocMap[car])app.node('carGrid').events.get('click')({target:{closest:selector=>selector==='.oc-toggle'?{dataset:{ocCar:car}}:null}});
        assert.equal(app.page.score(track['大地图'],track['小地图'],car,'zone5'),entry.time);
    }
    const physical=new Set(app.page.state().owned);assert.equal(physical.size,49);
    assert.ok(![...physical].some(name=>name.includes('[OC]')));
    const fuji=data.tracks.slice(-2);assert.ok(fuji.every(track=>track['大地图']==='富士山'&&track['五区']['理论'].length===0));
});


function clickLink(app, id) {
    let prevented = false;
    const event = {button:0,preventDefault(){prevented=true;},get defaultPrevented(){return prevented;}};
    app.node(id).events.get('click')(event);
    return prevented;
}
function leaving(app) {
    let prevented = false;
    const event = {preventDefault(){prevented=true;},returnValue:undefined};
    for(const callback of app.globalEvents.get('beforeunload')||[])callback(event);
    return prevented;
}
function nationalFiles(){return new Map(['cars.json','gauntlet_data.json'].map(name=>[name,fs.readFileSync(path.join(__dirname,name))]));}

test('CN unsaved guest draft can switch server without native unload blocking, without saving the garage or losing either server draft',async()=>{
    const original=JSON.stringify({cars:['白龙'],stars:{白龙:6}}),otherDraft='{"global-draft":"keep"}';
    const local=storage({'racepick.guest-profile.v1':original});
    const session=storage({'racepick.guest-draft.v1.global':otherDraft});
    const app=await boot({files:nationalFiles(),server:'cn',versioned:false,useAccountStub:false,local,session});
    assert.deepEqual(app.errors,[]);app.page.clear();assert.equal(app.page.state().dirty,true);
    assert.equal(leaving(app),true); // ordinary closing still has the original protection
    assert.equal(clickLink(app,'serverGlobalLink'),false);
    assert.equal(leaving(app),false);
    assert.deepEqual(JSON.parse(session.values.get('racepick.guest-draft.v1')).profile.cars,[]);
    assert.equal(local.values.get('racepick.guest-profile.v1'),original);
    assert.equal(session.values.get('racepick.guest-draft.v1.global'),otherDraft);
    app.page.selectAll();assert.equal(leaving(app),true); // new edits clear the one-navigation intent
});

test('global unsaved OC draft can switch to CN and returns with ownership and OC intact, without implicit save',async()=>{
    const local=storage(cnLocal),session=storage(cnSession),app=await boot({local,session});
    app.node('carGrid').events.get('click')({target:{closest:selector=>selector==='.oc-toggle'?{dataset:{ocCar:'杰哥'}}:null}});
    assert.equal(leaving(app),true);assert.equal(clickLink(app,'serverCnLink'),false);assert.equal(leaving(app),false);
    assert.equal(local.values.has('racepick.guest-profile.v1.global'),false);
    const next=await boot({local,session});assert.equal(next.page.state().ocMap.杰哥,true);assert.equal(next.page.state().owned.length,3);
    assert.equal(session.values.get('racepick.guest-draft.v1'),cnSession['racepick.guest-draft.v1']);
});

test('server navigation is blocked if the current guest draft cannot be preserved',async()=>{
    const app=await boot();app.page.clear();
    const raw=app.session.values.get('racepick.guest-draft.v1.global');
    app.session.setItem=()=>{throw Error('quota');};
    assert.equal(clickLink(app,'serverCnLink'),true);assert.equal(leaving(app),true);
    assert.equal(app.session.values.get('racepick.guest-draft.v1.global'),raw);
    assert.match(app.node('storageNotice').textContent,/暂不能切换服务器/);
    assert.equal(app.local.values.has('racepick.guest-profile.v1.global'),false);
});

function accountUnload({intent=false,mismatch=false,failWrite=false}={}){
    const profile={cars:['白龙'],stars:{白龙:6}},session=storage({'racepick.account-draft.v1.main':JSON.stringify({revision:4,profile:mismatch?{cars:[],stars:{}}:profile})});
    if(failWrite)session.setItem=()=>{throw Error('quota');};
    const source=read('auth.js'),start=source.indexOf("        addEventListener('beforeunload',e=>{"),end=source.indexOf('\n        });',start)+12;
    let handler;const notices=[];
    const context=vm.createContext({store:{state:()=>({dirty:true}),snapshot:()=>profile},owner:{id:'main'},sessionStorage:session,report:message=>notices.push(message),addEventListener:(type,fn)=>handler=fn,RACEPICK_SERVER_NAVIGATION:intent?{kind:'server-switch',target:'?server=global'}:null});
    vm.runInContext(source.slice(start,end),context);
    let prevented=false;handler({preventDefault(){prevented=true;},returnValue:undefined});
    return {prevented,notices,session};
}

test('account unload exemption requires an explicit server switch and a verified current per-user draft; no profile API is used',()=>{
    assert.equal(accountUnload().prevented,true);
    const allowed=accountUnload({intent:true});assert.equal(allowed.prevented,false);assert.deepEqual(allowed.notices,[]);
    assert.deepEqual(allowed.session.writes,['racepick.account-draft.v1.main']);
    assert.equal(accountUnload({intent:true,mismatch:true}).prevented,true);
    assert.equal(accountUnload({intent:true,failWrite:true}).prevented,true);
});


test('an explicitly unknown server produces a visible error before any CN/global data or account request',async()=>{
    const app=await boot({server:'unknown-market'});
    assert.match(app.node('mapRowsContainer').innerHTML,/未知服务器/);
    assert.deepEqual(app.requests,[]);assert.equal(app.accountCalls(),0);
    assert.equal(clickLink(app,'serverCnLink'),false); // an invalid URL can be corrected via the valid CN link
});


test('the compact OC capsule overrides shared minimum dimensions and only widens its own car tag',()=>{
    const rule=read('styles.css').match(/\.oc-toggle\s*\{([^}]+)\}/)[1];
    const declarations=Object.fromEntries(rule.split(';').filter(entry=>entry.includes(':')).map(entry=>{const [name,value]=entry.split(':');return [name.trim(),value.trim()];}));
    assert.equal(declarations.width,'24px');assert.equal(declarations.height,'18px');
    assert.equal(declarations.top,'50%');assert.equal(declarations.transform,'translateY(-50%)');
    assert.equal(declarations['font-size'],'9px');assert.equal(declarations['line-height'],'16px');
    assert.equal(declarations['min-width'],'0');assert.equal(declarations['min-height'],'0');
    assert.equal(declarations['box-sizing'],'border-box');assert.equal(declarations.padding,'0');
    const tagRule=read('styles.css').match(/\.car-tag\.has-oc-toggle\s*\{([^}]+)\}/)[1];
    assert.match(tagRule,/padding-right:\s*38px/);assert.doesNotMatch(tagRule,/(?:padding-top|padding-bottom|height):/);
});


test('a malformed OC draft is rejected atomically, preserving the saved garage and original bad draft',async()=>{
    const saved=JSON.stringify({cars:['杰哥'],stars:{杰哥:6},ocMap:{杰哥:true}});
    const bad=JSON.stringify({base:saved,profile:{cars:['万达'],stars:{万达:5},ocMap:{万达:'true'}}});
    const local=storage({'racepick.guest-profile.v1.global':saved});
    const session=storage({'racepick.guest-draft.v1.global':bad});
    const app=await boot({local,session});
    assert.deepEqual([...app.page.state().owned],['杰哥']);
    assert.equal(app.page.state().ocMap.杰哥,true);assert.equal(app.page.state().ocMap.万达,undefined);
    assert.equal(app.page.profile().stars.杰哥,6);assert.equal(app.page.profile().stars.万达,undefined);
    assert.equal(app.page.state().dirty,false);
    assert.equal(session.values.get('racepick.guest-draft.v1.global'),bad);
    assert.equal(local.values.get('racepick.guest-profile.v1.global'),saved);
    assert.match(app.node('storageNotice').textContent,/草稿无法载入/);
});
