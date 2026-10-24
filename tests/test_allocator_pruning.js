const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const read = f => fs.readFileSync(path.join(__dirname, '..',f),'utf8');
const load = f => new Function(read(f)+';return allocator.generateParetoSchemes;')();
const reference = load('perf/allocator_reference.js');
const actual = load('allocator.js');
const map = groups => ({groups,carToPriority:new Map(groups.flatMap((g,i)=>g.map(c=>[c,i])))});
function compare(maps,owned,noCar=99) {
    const full = reference(maps,owned,Infinity,noCar);
    for(const limit of [Infinity,0,1,2,7,25,100,-1]) {
        assert.deepEqual(actual(maps,owned,limit,noCar),reference(maps,owned,limit,noCar));
    }
    assert.deepEqual(actual(maps,owned,Infinity,noCar),full);
}
test('complete ordered frontier: empty, scarce, equal-vector allocations, leave-empty minimum',()=>{
    for(const maps of [[],[map([])],[map([[]]),map([['A']])],
        Array.from({length:5},()=>map([['A','B']])),
        [map([['A'],['B']]),map([['A']]),map([])],
        [map([['A','B'],['A']]),map([['B','A']])]]) {
        for(const noCar of [-2,0,1,99]) compare(maps,new Set(['A','B']),noCar);
    }
});
test('600 deterministic random inputs, full ordered results and eight limits',()=>{
    let seed=0x631a57;
    const random = n => {seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed%n;};
    const cars=['A','B','C','D','E','F'];
    for(let k=0;k<600;k++) {
        const maps=Array.from({length:random(6)},()=>{
            const groups=Array.from({length:random(4)},()=>[]);
            for(const car of cars) if(groups.length && random(3)) groups[random(groups.length)].push(car);
            const m=map(groups);
            for(const car of m.carToPriority.keys()) {
                if(random(6)===0) m.carToPriority.delete(car);
                else m.carToPriority.set(car,random(8)-2);
            }
            return m;
        });
        compare(maps,new Set(cars.filter(()=>random(3))),[-2,0,1,99][random(4)]);
    }
});
test('non-finite priorities preserve reference behavior',()=>{
    for(const p of [NaN,Infinity,-Infinity]) {
        const maps=[map([['A']]),map([['B']])];maps[1].carToPriority.set('B',p);
        compare(maps,new Set(['A','B']));
    }
});
test('120 equal-vector assignments survive before the 25-result truncation',()=>{
    const cars=['A','B','C','D','E'];
    const maps=Array.from({length:5},()=>map([cars]));
    assert.equal(actual(maps,new Set(cars),Infinity).length,120);
    compare(maps,new Set(cars));
});
test('real page candidates: complete ordered frontiers and limits',()=>{
    const sources=Object.fromEntries(['index.html','app_state.js','race_scores.js'].map(f=>[f,read(f)]));
    const cases=require('../perf/page_inputs').prepare(sources,JSON.parse(read('cars.json')),JSON.parse(read('gauntlet_data.json')));
    for(const c of cases) compare(c.candidates,new Set(c.owned));
});
