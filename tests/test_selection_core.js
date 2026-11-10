'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const core = require('../selection_core');
const allocator = require('../allocator');
const scores = require('../race_scores');
const state = require('../app_state');
const reference = require('./fixtures/selection_page_reference.cjs');
const read = name => JSON.parse(fs.readFileSync(path.join(__dirname, '..', name), 'utf8'));

function oldPage(cars, data, server) {
    return new Function('cars', 'data', 'APP_CONFIG', 'appState', 'raceScores', 'globalThis', `
        let RACE_DATA=data, carStats=Object.fromEntries(cars.cars.map(c=>[c.title,c]));
        let zone5Cars=[],zone4Cars=[],CAR_STAR_RULES={},smallMapsByBig={},bigMapList=[];
        let currentZone='zone5',currentTier='理论',starsMap={},ocMap={},specialRouteEnabled={};
        ${reference}
        buildCarRules();
        return {
            rules:()=>({zone5Cars,zone4Cars,rules:CAR_STAR_RULES}),
            configure:input=>{currentZone=input.zone;currentTier=input.tier;starsMap=input.starsMap;
                ocMap=input.ocMap;specialRouteEnabled={...input.scStates};buildMapIndex();},
            candidates:maps=>prepareMapCandidates(maps,currentZone),
            time:(m,c)=>getCarScore(m.big,m.small,c,currentZone),
            stars:c=>getCarStars(c)
        };
    `)(cars, data, {server}, state, scores, {RACEPICK_SERVER: server});
}
const canonical = value => JSON.parse(JSON.stringify(value, (_, item) => item instanceof Map ? [...item] : item));

for (const server of ['cn', 'global']) test(`${server}: candidate and score parity; legacy tiers retain ordered schemes`, () => {
    const cars = read(server === 'cn' ? 'cars.json' : 'cars.global.json');
    const data = read(server === 'cn' ? 'gauntlet_data.json' : 'gauntlet_data.global.json');
    const before = JSON.stringify({cars, data});
    const old = oldPage(cars, data, server), shared = core.createSelectionCore({cars, data, server});
    const context = core.createSelectionContext({cars,data,server,version:'local-test'});
    assert.deepEqual(shared.carRules(), old.rules());
    const maps = data.tracks.map((t, originalIndex) => ({big:t.大地图,small:t.小地图,originalIndex}));
    // Include unsupported route choices, both OC states, corrupt/low/mixed stars and every CN tier/zone.
    const routes = ['all','off','旧跳图','稳定跳图','滑栏杆','not-a-route'];
    for (const zone of server === 'cn' ? ['zone5','zone4'] : ['zone5']) {
        for (const tier of server === 'cn' ? ['理论','高手','普通','自动'] : ['理论']) {
            for (const starMode of ['mixed','invalid']) for (const route of routes) for (const oc of [false,true]) {
                const names = shared.carRules()[zone === 'zone4' ? 'zone4Cars' : 'zone5Cars'];
                const input = {zone,tier,starsMap:Object.fromEntries(names.map((n,i)=>[n,starMode==='mixed'?1+i%6:'3'])),
                    ocMap:Object.fromEntries(names.map(n=>[n,oc])),scStates:Object.fromEntries(maps.map(m=>[m.big+'/'+m.small,route]))};
                old.configure(input);
                const expected=old.candidates(maps),actual=shared.prepareMapCandidates({...input,maps});
                assert.deepEqual(canonical(actual),canonical(expected),`${zone}/${tier}/${starMode}/${route}/${oc}`);
                for (let i=0;i<maps.length;i++) for (const car of actual[i].groups.flat()) {
                    assert.equal(shared.effectiveTime({...input,...maps[i],car}),old.time(maps[i],car));
                }
                const picked=[];
                for(let i=0;i<maps.length && picked.length<5;i++) if(!picked.some(j=>maps[j].big===maps[i].big)) picked.push(i);
                const owned=new Set(picked.flatMap(i=>actual[i].groups.slice(0,2).flat()).slice(0,4));
                const a=allocator.generateParetoSchemes(picked.map(i=>actual[i]),owned,25);
                const b=allocator.generateParetoSchemes(picked.map(i=>expected[i]),owned,25);
                assert.deepEqual(a,b);
                const draft={schema:1,server,zone,tier,maps:picked.map(i=>maps[i]),cars:[...owned],stars:input.starsMap,oc:input.ocMap,routes:input.scStates};
                while(draft.maps.length<5) draft.maps.push(null);
                const result=context.calculate(draft);
                if (!['高手','理论'].includes(tier)) assert.deepEqual(result.schemes.map(s=>({assignment:s.assignment,vector:s.vector})),b.map(s=>{
                    const assignment=new Array(5).fill(null),vector=new Array(5).fill(null);
                    picked.forEach((_,i)=>{assignment[i]=s.assignment[i];vector[i]=s.vector[i];});
                    return {assignment,vector};
                }));
                for(const scheme of result.schemes) {
                    const times=scheme.rows.map((row,i)=>row.car===null?null:old.time(draft.maps[i],row.car));
                    assert.deepEqual(scheme.rows.map(row=>row.time),times);
                    assert.equal(scheme.total,scheme.rows.every(row=>row.car!==null && row.time!==null)?times.reduce((sum,t)=>sum+t,0):null);
                }
                for (const scheme of a) {
                    const times=scheme.assignment.map((car,i)=>car===null?null:shared.effectiveTime({...input,...maps[picked[i]],car}));
                    const oldTimes=scheme.assignment.map((car,i)=>car===null?null:old.time(maps[picked[i]],car));
                    assert.deepEqual(times,oldTimes);
                    assert.equal(times.reduce((sum,t)=>sum+(t??0),0),oldTimes.reduce((sum,t)=>sum+(t??0),0));
                }
            }
        }
    }
    const input={zone:'zone5',tier:'理论',starsMap:{},ocMap:{},scStates:{}};
    old.configure(input);
    assert.deepEqual(canonical(shared.prepareMapCandidates({...input,maps:[{big:'missing',small:'missing'}]})),canonical(old.candidates([{big:'missing',small:'missing'}])));
    assert.equal(JSON.stringify({cars,data}),before,'shared operations must not mutate snapshot data');
});

test('native DTO retains incomplete slots, legitimate empty garages and route names from the current tier', () => {
    const cars=read('cars.json'),data=read('gauntlet_data.json');
    const context=core.createSelectionContext({cars,data,server:'cn',version:'local-test'});
    const river=data.tracks.find(t=>t.小地图==='河畔漂移');
    assert.ok(river);
    const map={big:river.大地图,small:river.小地图};
    const draft={schema:1,server:'cn',zone:'zone5',tier:'高手',maps:[null,{big:map.big,small:''},map,null,null],cars:[],stars:{},oc:{},routes:{}};
    const before=JSON.stringify(draft), result=context.calculate(draft);
    assert.equal(result.schemes.length,1);
    assert.equal(result.schemes[0].rows.length,5);
    assert.equal(result.schemes[0].rows[2].map,'河畔漂移');
    assert.ok(result.schemes[0].rows.every(row=>row.car===null && row.time===null));
    assert.equal(result.schemes[0].total,null);
    assert.deepEqual(result.schemes[0].vector,[null,null,99,null,null]);
    assert.deepEqual(context.getModel(draft).routes[0].types,['稳定跳图']);
    assert.match(context.getModel(draft).routes[0].label,/稳定跳图/);
    assert.equal(JSON.stringify(draft),before);
    assert.throws(()=>context.calculate({...draft,maps:[map,map,null,null,null]}),/不能重复/);
    assert.throws(()=>context.calculate({...draft,server:'global'}),/不匹配/);
    assert.throws(()=>context.calculate({...draft,maps:[]}),/五槽/);
    assert.deepEqual(context.calculate({...draft,maps:[null,null,null,null,null]}).schemes,[]);
});

test('global capabilities reject unsupported tiers/zones without falling back to national data', () => {
    const shared=core.createSelectionCore({cars:read('cars.global.json'),data:read('gauntlet_data.global.json'),server:'global'});
    for(const [zone,tier] of [['zone4','理论'],['zone5','高手']]) assert.throws(()=>shared.prepareMapCandidates({maps:[],zone,tier}),/仅支持/);
    assert.throws(()=>core.createSelectionCore({server:'unknown'}),/未知服别/);
});
