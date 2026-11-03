'use strict';
// Presentation metadata only. Pools/stars/OC and scores stay in shared core.
function enrichModel(model,snapshot,draft,core) {
  const metadata=new Map(snapshot.cars.cars.map(c=>[c.nickname,c]));
  return {...model,cars:model.cars.map(c=>{const raw=metadata.get(c.id)||{};return {...c,title:raw.title||c.label,score:raw.score,carClass:raw.class||'',effectiveStar:core&&draft?core.carStars(raw.star_rule,draft.zone,(draft.stars||{})[c.id],snapshot.server):c.defaultStar};})};
}
function visibleCars(cars,query,carClass,sortMode) {
  const q=(query||'').trim().toLowerCase();
  const result=cars.filter(c=>(!q||(c.id+' '+c.label+' '+(c.title||'')).toLowerCase().includes(q))&&(!carClass||c.carClass===carClass));
  return result.sort((a,b)=>{
    if(sortMode==='score-desc'||sortMode==='score-asc') {
      const l=Number.isFinite(a.score),r=Number.isFinite(b.score);
      if(l!==r)return l?-1:1;
      if(l)return sortMode==='score-desc'?b.score-a.score:a.score-b.score;
    }
    return a.id.localeCompare(b.id,'zh');
  });
}
module.exports={enrichModel,visibleCars};
