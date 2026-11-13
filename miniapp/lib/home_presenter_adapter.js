'use strict';
const presenter=require('../shared/home_presenter');
const core=require('../shared/selection_core');
const mapBanKey=(d,map)=>JSON.stringify([d.server,d.zone,map.big,map.small]);
const waterfrontKey='巴黎/塞纳河岸';
const globalWaterfront=map=>map?.big==='巴黎'&&map.small==='塞纳河岸';
function createWebHomeAdapter(snapshot) {
 const waterfront=snapshot.server==='global'&&snapshot.data.tracks.find(track=>track.大地图==='巴黎'&&track.小地图==='塞纳河岸');
 const types=waterfront?.五区?.理论?.filter(entry=>entry.sc).map(entry=>entry.sc_type)||[];
 function scoreRoutes(d){
  const route=d.routes?.[waterfrontKey];
  if(!waterfront||d.zone!=='zone5'||d.tier!=='理论'||!route)return d.routes;
  if(route==='旧跳图'&&types.includes('跳图')&&!types.includes('旧跳图'))return {...d.routes,[waterfrontKey]:'跳图'};
  // A displayed option can have video but no recorded score. Filtering must
  // not fall back to all special scores when the chosen subtype is absent.
  if(route==='稳定跳图'&&!types.includes(route))return {...d.routes,[waterfrontKey]:'off'};
  return d.routes;
 }
 function routesFor(d,routes){
  if(!waterfront||d.zone!=='zone5'||d.tier!=='理论'||!d.maps.some(globalWaterfront))return routes;
  const route={key:waterfrontKey,label:'塞纳河岸',types:['稳定跳图','旧跳图'],aliases:{跳图:'旧跳图'}};
  const index=routes.findIndex(item=>item.key===waterfrontKey);
  if(index===-1)return [...routes,route];
  return routes.map((item,i)=>i===index?route:item);
 }
 const p=presenter.createHomePresenter(snapshot),selection=core.createSelectionCore(snapshot);let cachedKey,cached;
 function view(d,filters={}) {const key=JSON.stringify([d,filters]);if(key!==cachedKey){cached=p.present({...d,routes:scoreRoutes(d)},filters);cachedKey=key;}return cached;}
 function candidates(d,map){
  return selection.prepareMapCandidates({maps:[map],zone:d.zone,tier:d.tier,starsMap:d.stars,ocMap:d.oc,scStates:scoreRoutes(d)})[0];
 }
 function filteredReferences(d,map){
  const candidate=core.excludeBannedCars(candidates(d,map),new Set(d.mapBans?.[mapBanKey(d,map)]));
  const rules=selection.carRules().rules;
  return presenter.getTopCars(candidate,new Set(d.cars),{tier:d.tier,
   starsFor:car=>core.carStars(rules[car],d.zone,d.stars?.[car],d.server),
   scoreFor:car=>selection.effectiveTime({...map,car,zone:d.zone,tier:d.tier,starsMap:d.stars,ocMap:d.oc,scStates:scoreRoutes(d)})});
 }
 return {
  routesFor,
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
