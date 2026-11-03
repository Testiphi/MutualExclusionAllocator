'use strict';
// Build-time extraction from the owning website commit. Fail on source drift.
function generateWebHomeAdapter(source) {
  const names=['filterBySearch','filterByClass','sortCarList','getTopCars','updateSubtitle'];
  const functions=names.map(name=>{const m=source.match(new RegExp('^    function '+name+'\\([^]*?^    }','m'));if(!m)throw Error('网页函数边界已变，请重新核对：'+name);return m[0];});
  const aliases=source.match(/^    const NICKNAME_ALIASES = \{[^]*?^    };/m);
  const tier=source.match(/^    let currentTier = (.+);$/m);
  if(!aliases||!tier||!source.includes('if (isFirstLoad) {')||!source.includes('carList.forEach(c => selectedCars.add(c));'))throw Error('网页首次默认语义已变，请重新核对');
  return `'use strict';
// Generated from fixed website index.html. Never edit this file.
function createWebHomeAdapter(snapshot,core) {
 const APP_CONFIG={server:snapshot.server};
 let currentTier=${tier[1]},currentZone='zone5',starsMap={},ocMap={},specialRouteEnabled={};
 const initialTier=currentTier,carStats=Object.fromEntries(snapshot.cars.cars.map(c=>[c.title,c])),nickToName={...snapshot.cars._nickname_map};
 const RACE_DATA=snapshot.data,subtitleNode={textContent:'帕累托最优 · 擂台选车'},document={querySelector:s=>s==='.sub'?subtitleNode:null};
 for(const car of snapshot.cars.cars)if(car.nickname)nickToName[car.nickname]=car.title;
 const shared=core.createSelectionCore(snapshot),derived=shared.carRules();
 ${aliases[0]}
 function configure(d){currentTier=d.tier;currentZone=d.zone;starsMap=d.stars||{};ocMap=d.oc||{};specialRouteEnabled=d.routes||{};}
 function input(){return {zone:currentZone,tier:currentTier,starsMap,ocMap,scStates:specialRouteEnabled};}
 function getCarStars(car){return core.carStars(derived.rules[car],currentZone,starsMap[car],snapshot.server);}
 function getCarScore(big,small,car,zone){return shared.effectiveTime({...input(),big,small,car,zone});}
 ${functions.join('\n')}
 return {
  defaults:()=>({tier:initialTier,selectAllOnFirstLoad:true}),
  subtitle(d){configure(d);updateSubtitle();return subtitleNode.textContent;},
  visible(d,query,cls,sort){configure(d);const pool=derived[currentZone==='zone4'?'zone4Cars':'zone5Cars'];return sortCarList(filterByClass(filterBySearch(pool,query),cls),sort);},
  tops(d){configure(d);const maps=d.maps.map((m,i)=>m&&m.big&&m.small?{...m,originalIndex:i}:null).filter(Boolean);
   const candidates=shared.prepareMapCandidates({...input(),maps}),pool=derived[currentZone==='zone4'?'zone4Cars':'zone5Cars'];
   const owned=new Set(d.cars.filter(c=>pool.includes(c)));
   return maps.map((m,i)=>({index:m.originalIndex,key:m.big+'/'+m.small,label:currentTier==='普通'||currentTier==='自动'?'查看本图优先候选前三':'查看本图前三可用车',
    items:getTopCars(candidates[i],owned,m.big,m.small,currentZone).map(x=>({...x,oc:snapshot.server==='global'&&ocMap[x.car]===true,scoreText:x.score==null?'暂无成绩':Number(x.score).toFixed(2)+' 秒'}))}));
  }
 };
}
module.exports={createWebHomeAdapter};
`;
}
module.exports={generateWebHomeAdapter};
