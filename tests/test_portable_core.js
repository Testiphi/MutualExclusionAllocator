'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
function browser(file,name){const context=vm.createContext({});return vm.runInContext(fs.readFileSync(path.join(root,file),'utf8')+'\n;'+name,context);}
test('CommonJS and browser cores give identical ordered allocations without DOM or platform APIs',()=>{
 const native=require('../allocator.js'),web=browser('allocator.js','allocator');
 const candidates=[{groups:[['a'],['b']],carToPriority:new Map([['a',0],['b',1]])},{groups:[['a']],carToPriority:new Map([['a',0]])}],owned=new Set(['a','b']);
 const result=native.generateParetoSchemes(candidates,owned);assert.deepEqual(result,JSON.parse(JSON.stringify(web.generateParetoSchemes(candidates,owned))));
 assert(result.some(r=>r.assignment[0]==='b'&&r.assignment[1]==='a'));
});
test('portable score core preserves actual interpolation and separates OC from normal records',()=>{
 const core=require('../race_scores.js'),web=browser('race_scores.js','raceScores');
 const entries=[{cars:[{name:'a',stars:4}],time:22},{cars:[{name:'a',stars:6}],time:20},{cars:[{name:'a',stars:6,oc:true}],time:19}];
 assert.equal(core.effectiveTime(entries,'a','高手',5,'all'),21);assert.equal(core.effectiveTime(entries,'a','理论',6,'all',null,{ocMap:{a:true}}),19);
 assert.equal(core.effectiveTime(entries,'a','高手',5,'all'),web.effectiveTime(entries,'a','高手',5,'all'));
});
test('portable state core filters a garage without persisting or replacing the input',()=>{
 const state=require('../app_state.js'),original=['a','old'];assert.deepEqual([...state.garage(original,new Set(['a']))],['a']);assert.deepEqual(original,['a','old']);
 assert.equal(state.route('unrecognized',['跳图']),'all');
});
