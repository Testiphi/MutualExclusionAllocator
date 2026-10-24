'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const {webcrypto} = require('node:crypto');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'api.js'), 'utf8') + '\n;globalThis.testApi=api;';

function setup(fetch, config = {}) {
    const waits = [];
    const context = vm.createContext({APP_CONFIG:{dataSource:'static', ...config},
        RACEPICK_VERSIONED_SCORES:true, fetch, TextDecoder, Uint8Array, crypto:webcrypto,
        setTimeout(callback, delay){waits.push(delay);queueMicrotask(callback);}});
    vm.runInContext(source, context);
    return {api:context.testApi, waits};
}
const response = (status, value, retryAfter = null) => ({status, ok:status===200,
    headers:{get:()=>retryAfter}, json:async()=>value});

test('CN bootstrap shares bounded 429/503 retries and keeps cars and scores in one snapshot', async()=>{
    let calls = 0;
    const snapshot = {cars:{cars:['before']}, data:{time:20}};
    const {api, waits} = setup(async()=>++calls===1 ? response(429) : calls===2 ? response(503,null,'1') : response(200,snapshot));
    const [cars, data] = await Promise.all([api.getCars(), api.getRaceData()]);
    assert.equal(calls,3);assert.deepEqual(waits,[1000,1000]);
    assert.equal(cars,snapshot.cars);assert.equal(data,snapshot.data);
});

test('persistent rate limiting stops after three requests and a later load can recover',async()=>{
    let calls = 0, healthy = false;
    const {api, waits} = setup(async()=>{calls++;return healthy ? response(200,{cars:{cars:['recovered']}}) : response(429);});
    await assert.rejects(api.getCars(),/HTTP 429/);
    assert.equal(calls,3);assert.deepEqual(waits,[1000,2000]);
    healthy=true;assert.equal((await api.getCars()).cars[0],'recovered');assert.equal(calls,4);
});

test('404 and long Retry-After responses do not start retry loops',async()=>{
    for (const [status, retryAfter] of [[404,null],[429,'60']]) {
        let calls=0;const {api,waits}=setup(async()=>{calls++;return response(status,null,retryAfter);});
        await assert.rejects(api.getCars(),new RegExp('HTTP '+status));
        assert.equal(calls,1);assert.deepEqual(waits,[]);
    }
});

test('global bootstrap retries only the throttled file, then verifies the original bytes and metadata',async()=>{
    const calls=[],first=new Set();
    const {api,waits}=setup(async name=>{
        calls.push(name);
        if(name==='cars.global.json'&&!first.has(name)){first.add(name);return response(429);}
        const raw=fs.readFileSync(path.join(root,name));
        return {ok:true,status:200,arrayBuffer:async()=>raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength)};
    },{server:'global',staticPaths:{manifestJson:'global-data-manifest.json',carsJson:'cars.global.json',dataJson:'gauntlet_data.global.json'}});
    const [cars,data]=await Promise.all([api.getCars(),api.getRaceData()]);
    assert.equal(cars._meta.dataset_version,data._meta.dataset_version);
    assert.equal(calls.length,4);assert.deepEqual(waits,[1000]);
    assert.equal(calls.filter(name=>name==='gauntlet_data.global.json').length,1);
});

test('garage writes are never retried on 429',async()=>{
    const calls=[];
    const {api,waits}=setup(async(url,options)=>{calls.push([url,options.method]);return response(429,{detail:'limited'});},
        {dataSource:'api',apiBaseUrl:'',apiPrefix:'/api'});
    await assert.rejects(api.saveGarage(new Set(['car'])),/limited/);
    assert.deepEqual(calls,[['/api/garage','PUT']]);assert.deepEqual(waits,[]);
});
