'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

function fixture(request) {
    const nodes=[], listeners=new Map(), documentListeners=new Map(), timers=new Set();
    const doc={hidden:false,querySelectorAll:()=>nodes.filter(n=>n.dataset.unreadChannels),createElement:()=>({hidden:false,setAttribute(){}}),
        addEventListener:(e,f)=>documentListeners.set(e,f),removeEventListener:e=>documentListeners.delete(e)};
    const context={document:doc,setInterval:f=>{timers.add(f);return f;},clearInterval:f=>timers.delete(f),
        addEventListener:(e,f)=>listeners.set(e,f),removeEventListener:e=>listeners.delete(e)};
    vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../notifications.js'),'utf8'),context);
    const controller=context.Unread.create({request,user:{id:'owner',role:'admin'}});
    function target(){const n={dataset:{},marker:null,querySelector(){return this.marker;},append(m){this.marker=m;}};nodes.push(n);return n;}
    const response=(items={review:['s1'],submissions:['mine']})=>({user_id:'owner',role:'admin',items,counts:Object.fromEntries(Object.entries(items).map(([k,v])=>[k,v.length]))});
    return {controller,target,doc,listeners,documentListeners,timers,response};
}

test('outer directories, child entries and individual rows follow the same unread source',async()=>{
    let next;const f=fixture(async()=>next);next=f.response();
    const parent=f.target(),child=f.target(),row=f.target(),other=f.target();
    f.controller.track(parent,'review feedback_admin');f.controller.track(child,'review');
    f.controller.track(row,'review','s1');f.controller.track(other,'review','s2');
    await f.controller.refresh();assert.equal(parent.marker.hidden,false);assert.equal(child.marker.hidden,false);
    assert.equal(row.marker.hidden,false);assert.equal(other.marker,null);
    next=f.response({review:[],submissions:['mine']});await f.controller.refresh();
    assert.equal(parent.marker.hidden,true);assert.equal(child.marker.hidden,true);assert.equal(row.marker.hidden,true);
    f.controller.stop();
});

test('hidden pages pause refresh and never acknowledge; rendered cursor is used exactly',async()=>{
    const calls=[];let f;f=fixture(async(method,path,body)=>{calls.push({method,path,body});return f.response();});
    f.doc.hidden=true;await f.controller.refresh();await f.controller.read({id:'s1',notification_cursors:{review:11}},'review');
    assert.equal(calls.length,0);f.doc.hidden=false;
    await f.controller.read({id:'s1',notification_cursors:{review:11}},'review');
    assert.equal(calls[0].method,'POST');assert.equal(calls[0].body.event_id,11);assert.equal(calls[0].body.item_id,'s1');
    assert.equal(calls[1].path,'/notifications');f.controller.stop();
});

test('network failures retain state; revoked session clears it and stops polling',async()=>{
    let error=null,f;f=fixture(async()=>{if(error)throw error;return f.response();});
    const button=f.target();f.controller.track(button,'review');await f.controller.refresh();
    error=new Error('offline');await f.controller.refresh();assert.equal(button.marker.hidden,false);
    error=Object.assign(new Error('expired'),{status:401});await f.controller.refresh();
    assert.equal(button.marker.hidden,true);assert.equal(f.timers.size,0);assert.equal(f.listeners.has('focus'),false);
});

test('concurrent refresh shares a request and role changes discard old-account dots',async()=>{
    let resolve,calls=0;const f=fixture(()=>{calls++;return new Promise(r=>{resolve=r;});});
    const a=f.controller.refresh(),b=f.controller.refresh();assert.equal(calls,1);resolve(f.response());await Promise.all([a,b]);
    const button=f.target();f.controller.track(button,'review');assert.equal(button.marker.hidden,false);
    const pending=f.controller.refresh();resolve({...f.response(),role:'player'});await pending;
    assert.equal(button.marker.hidden,true);assert.equal(f.timers.size,0);
});

test('last row receives its dot even when registered before attachment to the document',async()=>{
    let f;f=fixture(async()=>f.response());await f.controller.refresh();
    const detached={dataset:{},marker:null,querySelector(){return this.marker;},append(m){this.marker=m;}};
    f.controller.track(detached,'review','s1');assert.equal(detached.marker.hidden,false);
    f.controller.stop();
});

test('handling an item refreshes parent dots even if the new detail has no unread cursor',async()=>{
    let next,posts=0;const f=fixture(async(method)=>{if(method==='POST')posts++;return next;});
    next=f.response();const parent=f.target();f.controller.track(parent,'review');await f.controller.refresh();
    next=f.response({review:[],submissions:[]});await f.controller.read({id:'s1',notification_cursors:{review:0}},'review');
    assert.equal(parent.marker.hidden,true);assert.equal(posts,0);f.controller.stop();
});
