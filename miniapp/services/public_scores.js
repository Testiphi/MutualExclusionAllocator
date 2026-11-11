'use strict';
const {networkDiagnostic}=require('../adapters/transport');

const ORIGIN = 'https://racepick.cn';
const SCORES = '/api/coverage';
const VIDEOS = '/api/route-videos/matrix';

function get(wx, path, query, pending) {
  if(pending.cancelled)return Promise.reject(Error("已取消读取。"));
  const suffix = Object.entries(query).map(([key, value]) => key+'='+encodeURIComponent(value)).join('&');
  return new Promise((resolve, reject) => {
    const task = wx.request({
      url: ORIGIN+path+'?'+suffix,
      method: 'GET',
      timeout: 30000,
      success({statusCode, data}) {
        if(statusCode===200 && data && typeof data==='object')resolve(data);
        else reject(Error('读取公开表格失败，请重试。'));
      },
      fail(reason) {
        reject(Error(networkDiagnostic(reason).kind==='timeout'?'读取公开表格超时，请重试。':'网络请求未完成，请重试。'));
      }
    });
    pending.push(task);
  });
}

function validateScores(result, scope) {
  if (result.server!==scope.server || result.user_id!==null || !result.version ||
      result.oc!==scope.oc || !Array.isArray(result.maps) || !Array.isArray(result.columns) ||
      !Number.isInteger(result.column_offset) || !Number.isInteger(result.column_total) ||
      !Number.isInteger(result.column_limit) || result.column_limit<1 ||
      !Array.isArray(result.rows) || result.rows.some(row=>row.cells?.length!==result.columns.length ||
        row.cells.some(cell=>cell.visibility!=='public' ||
          (cell.status==='filled'?!Number.isFinite(cell.value):cell.status!=='empty'||cell.value!==null)))) {
    throw Error('公开成绩响应与所选范围不符，请重试。');
  }
  return result;
}

function changedScores() {
  return Object.assign(Error('成绩版本或筛选结果已变化，请刷新重试。'),{code:'SCORE_VERSION_CHANGED'});
}

async function readScores(wx, scope, starsByCar, pending, previous=null) {
  const read=async (stars,query=scope)=>validateScores(await get(wx,SCORES,{...query,stars},pending),query);
  const base=previous||await read('all');
  const byStar=new Map();
  if(scope.tier==='高手')base.columns.forEach((column,index)=>{
    const star=starsByCar.get(column.car);
    if(star!==column.stars && column.star_options?.includes(star)){
      if(!byStar.has(star))byStar.set(star,[]);
      byStar.get(star).push(index);
    }
  });
  if(!byStar.size)return base;
  const columns=base.columns.slice();
  const rows=base.rows.map(row=>({...row,cells:row.cells.slice()}));

  // A single changed column can use the existing search endpoint. Check the
  // exact vehicle ID because the server search also matches partial titles.
  await Promise.all([...byStar].map(async ([star,indexes])=>{
    let variant,positions;
    if(indexes.length===1){
      const car=base.columns[indexes[0]].car;
      variant=await read(star,{...scope,q:car,offset:0});
      if(variant.version!==base.version)throw changedScores();
      const position=variant.columns.findIndex(column=>column.car===car);
      if(position!==-1)positions=[position];
    }
    if(!positions){
      variant=await read(star);
      if(variant.column_offset!==base.column_offset || variant.columns.length!==base.columns.length ||
         variant.columns.some((column,i)=>column.car!==base.columns[i].car))throw changedScores();
      positions=indexes;
    }
    if(variant.version!==base.version || variant.rows.length!==base.rows.length ||
       variant.rows.some((row,i)=>row.map_id!==base.rows[i].map_id || row.big!==base.rows[i].big ||
         row.small!==base.rows[i].small || row.route!==base.rows[i].route))throw changedScores();
    for(const [i,index] of indexes.entries()){
      const position=positions[i];
      if(variant.columns[position].stars!==star)throw Error('所选星级暂不可用，请刷新重试。');
      columns[index]=variant.columns[position];
      for(let j=0;j<rows.length;j++)rows[j].cells[index]=variant.rows[j].cells[position];
    }
  }));
  return {...base,columns,rows};
}

function projectScores(data) {
  let filled=0,empty=0;
  const columns=data.columns.map(column=>({
    id:column.car,
    stars:column.stars,
    note:column.stars==null?'满星 '+column.max_stars+'星':'',
    options:[...(column.star_options||[])].reverse().map(value=>({value,label:value+'星'}))
  }));
  const rows=data.rows.map((row,index)=>({
    id:index,big:row.big,small:row.small+(row.route?' / '+row.route:''),
    cells:row.cells.map((cell,i)=>{
      if(cell.status==='filled')filled++;else empty++;
      return {id:columns[i].id,text:cell.status==='filled'?String(cell.value):''};
    })
  }));
  return {columns,rows,offset:data.column_offset,total:data.column_total,limit:data.column_limit,
    summary:rows.length+'行 · 当前列已填 '+filled+' · 空白 '+empty};
}

async function readReference(wx, scope, pending) {
  const data=await get(wx,VIDEOS,scope,pending);
  if((data.server && data.server!==scope.server)||!Array.isArray(data.maps)||!Array.isArray(data.cars)||
     !Array.isArray(data.counts)||!Number.isInteger(data.column_limit)||data.column_limit<1)
    throw Error('跑法参考响应无效，请重试。');
  return data;
}

const cellKey=(big,small,car)=>JSON.stringify([big,small,car]);
function projectReference(data, {mapQuery,carQuery,only,offset}) {
  const includes=(values,query)=>values.join(' ').toLowerCase().includes(query.trim().toLowerCase());
  const counts=new Map(data.counts.map(([big,small,car,count])=>[cellKey(big,small,car),count]));
  let maps=data.maps.filter(names=>includes(names,mapQuery));
  let cars=data.cars.filter(names=>includes(names,carQuery));
  if(only)cars=cars.filter(([car])=>maps.some(([big,small])=>counts.has(cellKey(big,small,car))));
  const total=cars.length,limit=data.column_limit;
  offset=Math.min(offset,Math.max(0,Math.ceil(total/limit)-1)*limit);
  const columns=cars.slice(offset,offset+limit).map(([id])=>({id}));
  if(only)maps=maps.filter(([big,small])=>columns.some(({id})=>counts.has(cellKey(big,small,id))));
  const rows=maps.map(([big,small],index)=>({
    id:index,big,small,
    cells:columns.map(({id})=>{
      const count=counts.get(cellKey(big,small,id));
      return {id,text:count?count+' 条':''};
    })
  }));
  return {columns,rows,offset,total,limit,summary:rows.length+' 张地图'};
}

module.exports={readScores,projectScores,readReference,projectReference};

