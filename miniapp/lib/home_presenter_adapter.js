'use strict';
const presenter=require('../shared/home_presenter');
function createWebHomeAdapter(snapshot) {
 const p=presenter.createHomePresenter(snapshot);let cachedKey,cached;
 function view(d,filters={}) {const key=JSON.stringify([d,filters]);if(key!==cachedKey){cached=p.present(d,filters);cachedKey=key;}return cached;}
 return {
  defaults:()=>({tier:presenter.initialTier(snapshot.server),selectAllOnFirstLoad:true}),
  visible:(d,query,cls,sort)=>view(d,{query,class:cls,sort}).visibleCars,
  subtitle:d=>view(d).subtitle,
  calculate:d=>({schemes:view(d).schemes}),
  guidance:(d,index=0)=>{const v=view(d);return v.guidanceByScheme?.length ? (v.guidanceByScheme[index]||null) : (v.guidance||null);},
  tops:d=>view(d).references.flatMap((items,index)=>d.maps[index]&&d.maps[index].small?[{index,key:d.maps[index].big+'/'+d.maps[index].small,
   label:['普通','自动'].includes(d.tier)?'查看本图优先候选前三':'查看本图前三可用车',
   items:items.map(x=>({...x,oc:snapshot.server==='global'&&d.oc[x.car]===true,scoreText:x.score==null?'暂无成绩':Number(x.score).toFixed(2)+' 秒'}))}]:[])
 };
}
module.exports={createWebHomeAdapter};
