'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const home=require('../home_presenter'),core=require('../selection_core');
const reference=require('./fixtures/home_page_reference.cjs');
const read=n=>JSON.parse(fs.readFileSync(path.join(__dirname,'..',n),'utf8'));

for(const server of ['cn','global'])test(`${server}: presenter matches frozen page filters/subtitle/top references and ordered result summaries`,()=>{
 const cars=read(server==='cn'?'cars.json':'cars.global.json'),data=read(server==='cn'?'gauntlet_data.json':'gauntlet_data.global.json');
 const before=JSON.stringify({cars,data}),snapshot={cars,data,server,version:'owned-fixture'};
 const selection=core.createSelectionCore(snapshot),presenter=home.createHomePresenter(snapshot);
 const carStats=Object.fromEntries(cars.cars.map(c=>[c.title,c])),nickToName={...cars._nickname_map};
 cars.cars.forEach(c=>{if(c.nickname&&!nickToName[c.nickname])nickToName[c.nickname]=c.title;});
 const old=new Function('carStats','nickToName','NICKNAME_ALIASES',Object.values(reference.functions).slice(0,3).join('\n')+'\nreturn {filterBySearch,filterByClass,sortCarList};')(carStats,nickToName,home.aliases);
 const maps=[];for(const t of data.tracks)if(maps.length<5&&!maps.some(m=>m.big===t.大地图))maps.push({big:t.大地图,small:t.小地图});
 for(const zone of server==='global'?['zone5']:['zone5','zone4'])for(const tier of server==='global'?['理论']:['理论','高手','普通','自动']){
  const pool=selection.carRules()[zone==='zone4'?'zone4Cars':'zone5Cars'];
  const draft={schema:1,server,zone,tier,maps,cars:pool.slice(0,4),stars:Object.fromEntries(pool.map((n,i)=>[n,1+i%6])),oc:{[pool[0]]:true},routes:{}};
  while(draft.maps.length<5)draft.maps.push(null);
  for(const query of ['', 'evo','杰','RS','不存在'])for(const mode of ['alpha','score-desc','score-asc'])for(const cls of [null,'S','R']){
   const model=presenter.present(draft,{query,sort:mode,class:cls});
   assert.deepEqual(model.visibleCars,old.sortCarList(old.filterByClass(old.filterBySearch(pool,query),cls),mode));
   const sub={textContent:'帕累托最优 · 擂台选车'};
   // Execute the frozen function as well as defining it.
   new Function('APP_CONFIG','RACE_DATA','currentZone','currentTier','document',reference.functions.updateSubtitle+';updateSubtitle();')({server},data,zone,tier,{querySelector:()=>sub});
   assert.equal(model.subtitle,sub.textContent);
   const input={maps:maps.filter(m=>m?.small),zone,tier,starsMap:draft.stars,ocMap:draft.oc,scStates:{}};
   const candidates=selection.prepareMapCandidates(input),owned=new Set(draft.cars);
   for(let i=0;i<input.maps.length;i++){
    const m=input.maps[i],getStars=car=>core.carStars(selection.carRules().rules[car],zone,draft.stars[car],server);
    const score=(big,small,car)=>selection.effectiveTime({...input,big,small,car});
    const top=new Function('currentTier','getCarStars','getCarScore',reference.functions.getTopCars+';return getTopCars;')(tier,getStars,score);
    assert.deepEqual(model.references[i],top(candidates[i],owned,m.big,m.small,zone));
   }
   model.schemes.forEach((s,i)=>{
    const parts=maps.flatMap((m,row)=>m?.big&&m?.small?[`${row+1}:${s.assignment[row]||'空'}`]:[]);
    assert.equal(s.summary,`方案${i+1} · ${parts.join(' ')} · Σ=${s.vector.reduce((sum,n)=>sum+(n===null?0:n),0)}`);
   });
  }
 }
 assert.equal(JSON.stringify({cars,data}),before);
});

test('exported theme exactly preserves CSS values, conditions and natural-width chips',()=>{
 const theme=read('home_theme.json');assert.equal(theme.tokens['--rp-bg'],'#0d1117');
 for(const [name,value] of Object.entries(theme.sources)){
  const text=fs.readFileSync(path.join(__dirname,'..',name),'utf8').replace(/\r\n/g,'\n');
  assert.equal(text,value.text);assert.equal(crypto.createHash('sha256').update(text).digest('hex'),value.sha256_utf8_lf);
 }
 assert(theme.rules.some(r=>r.selector==='.car-grid'&&/display:\s*flex/.test(r.declarations)));
 assert(theme.rules.some(r=>r.conditions.some(c=>c.startsWith('@media'))));
});
