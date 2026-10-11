// node --expose-gc perf/benchmark.js [--baseline]
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const read = f => fs.readFileSync(path.join(__dirname, '..', f), 'utf8');
const files = ['index.html', 'app_state.js', 'race_scores.js'];
const sources = Object.fromEntries(files.map(f => [f, read(f)]));
const cases = require('./page_inputs').prepare(sources, JSON.parse(read('cars.json')), JSON.parse(read('gauntlet_data.json')));
const load = f => new Function(read(f) + ';return allocator.generateParetoSchemes;')();
const implementations = {reference: load('perf/allocator_reference.js')};
if (!process.argv.includes('--baseline')) implementations.pruned = load('allocator.js');
const report = {environment: {node:process.version, platform:process.platform, arch:process.arch, cpu:os.cpus()[0].model},
    hashes:Object.fromEntries([...files,'cars.json','gauntlet_data.json','allocator.js','perf/allocator_reference.js'].map(f=>[f,crypto.createHash('sha256').update(read(f)).digest('hex')])),
    method:'First call separately; 2 warmups then 7 alternating-order repeats; allocator only; GC before each timed call when available; heap after-before is NOT peak.', cases:[]};
for (const c of cases) {
    const args = [c.candidates,new Set(c.owned),25,99];
    const results = {};
    for (const [name, fn] of Object.entries(implementations)) {
        global.gc?.(); const heap = process.memoryUsage().heapUsed; const t = performance.now();
        const value = fn(...args); const firstMs = performance.now()-t;
        results[name] = {firstMs, firstHeapDeltaBytes:process.memoryUsage().heapUsed-heap, samplesMs:[], heapDeltaBytes:[]};
        if (name === 'reference') results.expected = value; else assert.deepEqual(value,results.expected);
        fn(...args); fn(...args);
    }
    for (let i=0;i<7;i++) for (const name of Object.keys(implementations).sort((a,b)=>i%2?a.localeCompare(b):b.localeCompare(a))) {
        global.gc?.(); const heap=process.memoryUsage().heapUsed; const t=performance.now();
        const value=implementations[name](...args); const ms=performance.now()-t;
        results[name].heapDeltaBytes.push(process.memoryUsage().heapUsed-heap);
        results[name].samplesMs.push(ms); assert.deepEqual(value,results.expected);
    }
    delete results.expected;
    for (const r of Object.values(results)) {const sorted=[...r.samplesMs].sort((a,b)=>a-b);r.medianMs=sorted[3];r.minMs=sorted[0];r.maxMs=sorted[6];}
    const {candidates,...metadata}=c;
    report.cases.push({...metadata, counts:candidates.map(m=>m.groups.flat().filter(x=>args[1].has(x)).length),results});
}
console.log(JSON.stringify(report,null,2));
