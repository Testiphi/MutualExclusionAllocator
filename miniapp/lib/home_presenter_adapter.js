'use strict';
const presenter=require('../shared/home_presenter');
const core=require('../shared/selection_core');
const mapBanKey=(d,map)=>JSON.stringify([d.server,d.zone,map.big,map.small]);
function createWebHomeAdapter(snapshot) {
 const p=presenter.createHomePresenter(snapshot),selection=core.createSelectionCore(snapshot);let cachedKey,cached;
 function view(d,filters={}) {const key=JSON.stringify([d,filters]);if(key!==cachedKey){cached=p.present(d,filters);cachedKey=key;}return cached;}
 function candidates(d,map){
  return selection.prepareMapCandidates({maps:[map],zone:d.zone,tier:d.tier,starsMap:d.stars,ocMap:d.oc,scStates:d.routes})[0];
 }
 function filteredReferences(d,map){
  const candidate=core.excludeBannedCars(candidates(d,map),new Set(d.mapBans?.[mapBanKey(d,map)]));
  const rules=selection.carRules().rules;
  return presenter.getTopCars(candidate,new Set(d.cars),{tier:d.tier,
   starsFor:car=>core.carStars(rules[car],d.zone,d.stars?.[car],d.server),
   scoreFor:car=>selection.effectiveTime({...map,car,zone:d.zone,tier:d.tier,starsMap:d.stars,ocMap:d.oc,scStates:d.routes})});
 }
 return {
  defaults:()=>({tier:presenter.initialTier(snapshot.server),selectAllOnFirstLoad:true}),
  visible:(d,query,cls,sort)=>view(d,{query,class:cls,sort}).visibleCars,
  subtitle:d=>view(d).subtitle,
  banOptions(d,map){
   const banned=d.mapBans?.[mapBanKey(d,map)]||[];
   const owned=new Set(d.cars);
   return [...new Set([...candidates(d,map).groups.flat().filter(car=>owned.has(car)),...banned])];
  },
  calculate:d=>({schemes:view(d).schemes}),
  guidance(d,index=0) {
   if(d.maps.some(map=>map?.small&&d.mapBans?.[mapBanKey(d,map)]?.length))return null;
   const result=view(d);
   return result.guidanceByScheme?.length ? result.guidanceByScheme[index]||null : result.guidance||null;
  },
  tops:d=>view(d).references.flatMap((items,index)=>d.maps[index]&&d.maps[index].small?[{index,key:d.maps[index].big+'/'+d.maps[index].small,
   label:['普通','自动'].includes(d.tier)?'查看本图优先候选前三':'查看本图前三可用车',
   items:(d.mapBans?.[mapBanKey(d,d.maps[index])]?.length?filteredReferences(d,d.maps[index]):items).map(x=>({...x,oc:snapshot.server==='global'&&d.oc[x.car]===true,scoreText:x.score==null?'暂无成绩':Number(x.score).toFixed(2)+' 秒'}))}]:[])
 };
}
module.exports={createWebHomeAdapter,mapBanKey};
