'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../usage.js'),'utf8');
function fixture({pathname='/',search='',hidden=false,disabled=false,storageBlocked=false,fail=false}={}){
    let clock=1800000000000,serial=0;const calls=[],timers=[],listeners=new Map(),windowListeners=new Map();
    const storage=()=>({values:new Map(),getItem(k){if(storageBlocked)throw Error('blocked');return this.values.get(k)||null;},setItem(k,v){if(storageBlocked)throw Error('blocked');this.values.set(k,v);},removeItem(k){this.values.delete(k);}});
    const localStorage=storage(),sessionStorage=storage();
    const document={hidden,readyState:'complete',addEventListener(name,fn){if(!listeners.has(name))listeners.set(name,[]);listeners.get(name).push(fn);},removeEventListener(name,fn){listeners.set(name,(listeners.get(name)||[]).filter(f=>f!==fn));}};
    class Clock extends Date{static now(){return clock;}}
    const context={RACEPICK_USAGE_ENABLED:!disabled,location:{pathname,search},document,Date:Clock,URLSearchParams,AbortController,
        crypto:{randomUUID:()=>String(++serial).padStart(32,'0')},localStorage,sessionStorage,
        setTimeout(fn,ms){const timer={fn,ms,cleared:false};timers.push(timer);return timer;},clearTimeout:t=>{t.cleared=true;},
        addEventListener:(name,fn)=>windowListeners.set(name,fn),
        async fetch(url,options){const body=JSON.parse(options.body);calls.push({url,body,options});
            if(fail && url.endsWith('/events'))throw Error('offline');
            return {ok:true,status:200,json:async()=>url.endsWith('/session')?{token:'signed-collector-token',identity:'same-visitor'}:{accepted:body.events.length}};}};
    vm.runInNewContext(code,context);
    const settle=async()=>{for(let i=0;i<30;i++)await Promise.resolve();};
    const emit=(name,event={})=>{for(const fn of [...(listeners.get(name)||[])])fn({target:{closest:()=>null},...event});};
    const events=()=>calls.filter(c=>c.body.events).flatMap(c=>c.body.events);
    return {context,document,calls,timers,emit,events,settle,advance:ms=>clock+=ms};
}

test('opening and returning are visits; only visible trusted interaction produces minute activity',async()=>{
    const f=fixture();await f.settle();assert.equal(f.events().length,1);assert.equal(f.events()[0].kind,'visit');
    f.emit('input',{isTrusted:false,target:{value:'never collect this'}});await f.settle();assert.equal(f.events().length,1);
    f.emit('input',{isTrusted:true,target:{value:'private typed content'}});f.emit('pointerdown',{isTrusted:true});await f.settle();
    assert.equal(f.events().filter(e=>e.kind==='active').length,1);
    assert.equal(JSON.stringify(f.calls).includes('private typed content'),false);
    f.document.hidden=true;f.advance(60000);f.emit('input',{isTrusted:true});await f.settle();assert.equal(f.events().filter(e=>e.kind==='active').length,1);
    f.document.hidden=false;f.emit('visibilitychange');await f.settle();assert.equal(f.events().at(-1).reason,'resume');
    f.emit('input',{isTrusted:true});await f.settle();assert.equal(f.events().filter(e=>e.kind==='active').length,2);
});

test('a background-opened page creates its first open only when visible, not an extra resume',async()=>{
    const f=fixture({hidden:true});await f.settle();assert.equal(f.calls.length,0);f.advance(120000);
    f.document.hidden=false;f.emit('visibilitychange');await f.settle();
    assert.equal(f.events().length,1);assert.equal(f.events()[0].reason,'open');
});

test('international pages send only usage context and never initialize account/profile APIs',async()=>{
    const f=fixture({search:'?server=global'});await f.settle();
    assert.ok(f.calls.every(c=>c.url.startsWith('/api/usage/')));assert.equal(f.events()[0].server,'global');
    f.context.Usage.feature('generate','success');await f.settle();assert.equal(f.events().filter(e=>e.kind==='feature').length,0);
    f.emit('click',{isTrusted:true});f.context.Usage.feature('generate','success');await f.settle();
    const featureTimer=f.timers.find(t=>t.ms===1000&&!t.cleared);featureTimer.fn();await f.settle();
    assert.equal(f.events().filter(e=>e.feature==='generate').length,1);
    f.context.Usage.feature('submission_submit','success');await f.settle();assert.equal(f.events().some(e=>e.feature==='submission_submit'),false);
    assert.deepEqual(Object.keys(f.context.Usage.headers()),['X-Usage-Token']);
});

test('administration pages and a disabled collector produce no traffic',async()=>{
    for(const options of [{pathname:'/admin-usage'},{pathname:'/admin-feedback'},{disabled:true}]){
        const f=fixture(options);await f.settle();assert.equal(f.calls.length,0);assert.equal(f.context.Usage,undefined);
    }
});

test('blocked storage degrades to an ephemeral visitor; retries preserve event ids',async()=>{
    const f=fixture({storageBlocked:true,fail:true});await f.settle();
    const initial=f.events()[0];assert.ok(initial);const retry=f.timers.find(t=>t.ms===5000&&!t.cleared);assert.ok(retry);
    f.advance(5000);retry.fn();await f.settle();assert.equal(f.events()[1].id,initial.id);
    f.advance(35000);const next=f.timers.filter(t=>t.ms===5000&&!t.cleared).at(-1);next.fn();await f.settle();
    assert.equal(f.events().length,2); // No offline history replay after the 30-second deadline.
});
