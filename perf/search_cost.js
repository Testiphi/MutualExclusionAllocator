// Diagnostic instrumentation only; never time these copies as production performance.
const fs=require('node:fs');
const path=require('node:path');
const read=f=>fs.readFileSync(path.join(__dirname,'..',f),'utf8');
const sources=Object.fromEntries(['index.html','app_state.js','race_scores.js'].map(f=>[f,read(f)]));
const cases=require('./page_inputs').prepare(sources,JSON.parse(read('cars.json')),JSON.parse(read('gauntlet_data.json')));
const results=[];
for(const c of cases){
    const costs={};
    for(const [name,file] of [['reference','perf/allocator_reference.js'],['pruned','allocator.js']]){
        const stats={nodes:0,leaves:0,dominanceCalls:0,boundChecks:0,boundFrontComparisons:0,boundDimensions:0,pruned:0};
        const source=read(file).replace(/\r\n/g,'\n')
            .replace('function dominates(aVec, bVec) {','function dominates(aVec, bVec) { stats.dominanceCalls++;')
            .replace('function backtrack(idx) {','function backtrack(idx) { stats.nodes++;')
            .replace('if (idx === n) {','if (idx === n) { stats.leaves++;')
            .replace('function branchDominated(idx) {','function branchDominated(idx) { stats.boundChecks++;')
            .replace('for (const existing of paretoFront) {\n                let strictlyBetter', 'for (const existing of paretoFront) { stats.boundFrontComparisons++;\n                let strictlyBetter')
            .replace('const bound = i < idx', 'stats.boundDimensions++; const bound = i < idx')
            .replace('if (noWorse && strictlyBetter) return true;', 'if (noWorse && strictlyBetter) { stats.pruned++; return true; }');
        new Function('stats',source+';return allocator.generateParetoSchemes;')(stats)(c.candidates,new Set(c.owned),25,99);
        if (name==='pruned' && stats.boundChecks && !stats.boundFrontComparisons) throw Error('Instrumentation did not match');
        costs[name]=stats;
    }
    results.push({name:c.name,costs});
}
console.log(JSON.stringify(results,null,2));
