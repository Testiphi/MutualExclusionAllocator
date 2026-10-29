'use strict';
(()=>{
const $=id=>document.getElementById(id),node=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;};
let session=null,view=null,zone='五区',tier='理论',offset=0,ticket=0,writing=false,pageSize=48;
const params=new URLSearchParams(location.search),starChoices=new Map();
const legacyStars=/^[1-6]$/.test(params.get('stars')||'')?params.get('stars'):'all';
function choices(){const key=$('server').value+':'+zone;if(!starChoices.has(key))starChoices.set(key,new Map());return starChoices.get(key);}
if(params.get('server')==='global')$('server').value='global';
if(['五区','四区'].includes(params.get('zone')))zone=params.get('zone');
if(params.get('tier')==='高手')tier='高手';
if(params.get('route')==='special')$('route').value='special';
$('gaps').checked=params.get('gaps')==='true';
if(params.has('q'))$('search').value=params.get('q').slice(0,80);
offset=Math.max(0,Math.min(5000,Number(params.get('offset'))||0));
async function call(method,path,body,account=session?.user?.id){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
 try{
 const r=await fetch('/api'+path,{method,signal:controller.signal,credentials:'same-origin',headers:{'Content-Type':'application/json',...(session?{'X-CSRF-Token':session.csrf}:{}),...(account?{'X-Account-ID':account}:{})},...(body?{body:JSON.stringify(body)}:{})});
 const data=await r.json().catch(()=>({detail:'服务器响应无法识别，请刷新核对'}));if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:'字段不符合要求，请核对');return data;
 }catch(e){if(e.name==='AbortError')throw Error('请求超时，请刷新核对；已保存草稿不会自动重复创建。');throw e;}finally{clearTimeout(timer);}
}
function query(){return new URLSearchParams({server:$('server').value,zone,tier,big:$('map').value,route:$('route').value,q:$('search').value,stars:legacyStars,offset:String(offset),gaps:String($('gaps').checked)});}
function option(select,value,text){const o=node('option',text);o.value=value;select.append(o);}
function clear(){ clearSelection();$('head').replaceChildren();$('body').replaceChildren();$('summary').textContent='';view=null; }
async function load(focusCar=null){
 const scroll=focusCar?{left:$('sheet-wrap').scrollLeft||0,top:$('sheet-wrap').scrollTop||0}:null;
 const stamp=++ticket;clear();$('message').textContent='';
 try{
  const currentSession=await call('GET','/auth/me');if(stamp!==ticket)return;session=currentSession;
  if($('server').value==='global'){zone='五区';tier='理论';}
  const chosen=$('map').value==='all'&&params.has('big')?params.get('big'):$('map').value;
  const q=query();if(chosen)q.set('big',chosen);
  const data=await call('POST','/coverage/view',{...Object.fromEntries(q),star_map:tier==='高手'?Object.fromEntries(choices()):{}});if(stamp!==ticket)return;
  if((session.user?.id||null)!==data.user_id)throw Error('账号已变化，请刷新后重试');
  view=data;offset=data.column_offset;pageSize=data.column_limit||48;$('map').replaceChildren();option($('map'),'all','全部地图');$('choice').replaceChildren();
  for(const m of data.maps){option($('map'),m.id,m.name);option($('choice'),m.id,m.name);}
  $('map').value=data.maps.some(m=>m.id===chosen)?chosen:'all';params.delete('big');
  render();if(scroll){$('sheet-wrap').scrollLeft=scroll.left;$('sheet-wrap').scrollTop=scroll.top;const selected=headerStars.get(focusCar);if(selected?.focus)selected.focus({preventScroll:true});}if(globalThis.history?.replaceState)history.replaceState(null,'','/score-table?'+query());if(view.production===false)$('message').textContent='独立本地验收，投稿仅进入测试库。';
  const pick=params.get('pick');if(pick){params.delete('pick');const cell=data.rows.flatMap(r=>r.cells).find(c=>c.key===pick);if(cell&&cell.status==='empty')open(cell);else $('message').textContent='所选格子已变化，请重新选择。';}
 }catch(e){if(stamp===ticket){clear();$('message').textContent=e.message;}}
}
const headerStars=new Map();
function render(){
 headerStars.clear();
 const access=view.access,global=view.server==='global';$('choose-map').hidden=global||access.level!==1||!!access.chosen;
 $('rights').textContent=global?'国际服暂仅浏览。':access.admin?'管理账号可查看全部国服成绩。':access.level===2?'国服成绩已全部解锁。':access.chosen&&access.level===1?'已开放所选大地图。':'已开放部分成绩，其余可贡献解锁。';
 $('sheets').replaceChildren();for(const [z,t] of global?[['五区','理论']]:[['五区','理论'],['五区','高手'],['四区','理论'],['四区','高手']]){const b=node('button',z+' · '+t);b.setAttribute('aria-current',String(z===zone&&t===tier));b.onclick=()=>{zone=z;tier=t;offset=0;void load();};$('sheets').append(b);}
 $('sheet').style.setProperty('--coverage-columns',String(view.columns.length));
 const h=node('tr');for(const [label,cls] of [['#','row-num'],['大地图','map-col'],['小地图'+($('route').value==='special'?' / 跑法':''),'track-col']]){const th=node('th',label);th.className=cls;h.append(th);}
 for(const c of view.columns){
  const th=node('th',c.car);th.className='car-col';th.title=c.title+' · 全表'+(tier==='高手'?'全部星级':'')+'覆盖'+c.coverage_count+'图';
  if(tier==='高手'){
    const select=node('select');select.className='star-select';select.setAttribute('aria-label',c.car+' 星级');
    for(const star of [...c.star_options].reverse())option(select,String(star),star+'星');select.value=String(c.stars);
    select.onchange=()=>{choices().set(c.car,Number(select.value));void load(c.car);};headerStars.set(c.car,select);th.append(select);
  }else th.append(node('small','满星 '+c.max_stars+'星'));
  h.append(th);
 }$('head').replaceChildren(h);
 let filled=0,empty=0;
 view.rows.forEach((row,i)=>{const tr=node('tr');for(const [value,cls] of [[i+1,'row-num'],[row.big,'map-col'],[row.small+(row.route?' / '+row.route:''),'track-col']]){const th=node('th',value);th.className=cls;tr.append(th);}
  row.cells.forEach((c,j)=>{const td=node('td');td.className=c.status;
   if(c.status==='filled'){filled++;td.append(node('span',c.value===null?'***':String(c.value)));td.title='已有成绩';}
   else{empty++;const button=node('button');button.className='cell';const label=row.small+' '+view.columns[j].car+(view.columns[j].stars?' '+view.columns[j].stars+'星':'')+' 暂无记录，可投稿';button.setAttribute('aria-label',label);button.title=label;
    if(c.mine){const mark=node('span');mark.className='pending-mark';button.append(mark);button.title+=' · 我的'+({draft:'草稿',pending:'待审核',needs_info:'待补充',accepted:'待发布'}[c.mine.status]||'投稿');}
    bindCell(button,c);td.append(button);}
   tr.append(td);
  });$('body').append(tr);
 });
 $('summary').textContent=`${view.rows.length}行 · 当前列已填 ${filled} · 待补 ${empty}`;
 $('empty-result').hidden=!!(view.rows.length&&view.columns.length);$('sheet-wrap').hidden=!view.rows.length||!view.columns.length;
 $('column-page').textContent=view.column_total?`${offset+1}–${offset+view.columns.length} / ${view.column_total}列`:'0列';$('previous-columns').disabled=offset===0;$('next-columns').disabled=offset+pageSize>=view.column_total;
}
let selectedCell=null,lastPointer=null,scrollBlockedUntil=0;
function clearSelection(){
 if(selectedCell?.button)selectedCell.button.classList?.remove('selected-cell');selectedCell=null;
 $('cell-tap-hint').hidden=true;
}
function destination(cell){
 if(cell.mine)return '/submissions#'+cell.mine.id;
 const prefill={server:'cn',...cell.target};return '/submissions?prefill='+encodeURIComponent(JSON.stringify(prefill))+'#new';
}
function open(cell){
 if(!cell.target){$('message').textContent='国际服投稿暂未开放。';return;}
 const path=destination(cell);
 if(!session.user){location.assign('/?login=1&returnTo='+encodeURIComponent(path));return;}
 location.assign(path);
}
function bindCell(button,cell){
 const epoch=ticket;
 button.onpointerdown=e=>{lastPointer={id:e.pointerId,kind:e.pointerType,x:e.clientX,y:e.clientY,moved:false};};
 button.onpointermove=e=>{if(lastPointer&&lastPointer.id===e.pointerId&&Math.hypot(e.clientX-lastPointer.x,e.clientY-lastPointer.y)>10){lastPointer.moved=true;clearSelection();}};
 button.onpointercancel=()=>{if(lastPointer)lastPointer.moved=true;clearSelection();};
 button.onclick=(event={})=>{
  if(epoch!==ticket)return;
  if(!cell.target){$('message').textContent='国际服投稿暂未开放。';return;}
  const touch=event.pointerType?event.pointerType==='touch'||event.pointerType==='pen':event.detail===0?false:lastPointer?.kind==='touch'||!!globalThis.matchMedia?.('(pointer:coarse)').matches;
  if(touch){
   if(lastPointer?.moved||Date.now()<scrollBlockedUntil)return;
   if(selectedCell?.cell.key===cell.key){clearSelection();open(cell);return;}
   clearSelection();selectedCell={cell,button};button.classList?.add('selected-cell');
   const hint=$('cell-tap-hint'),rect=button.getBoundingClientRect();hint.textContent=cell.mine?'再点一次查看投稿':'再点一次填写';
   hint.hidden=false;hint.style.left=Math.max(8,Math.min(rect.left+(rect.width-120)/2,(globalThis.innerWidth||document.documentElement.clientWidth)-128))+'px';
   hint.style.top=Math.max(8,rect.top>42?rect.top-36:rect.bottom+6)+'px';
  }else open(cell);
 };
}
$('sheet-wrap').onscroll=()=>{scrollBlockedUntil=Date.now()+200;if(lastPointer?.kind==='touch')lastPointer.moved=true;clearSelection();};
globalThis.addEventListener?.('scroll',clearSelection,{passive:true});

$('filters').onsubmit=e=>{e.preventDefault();offset=0;void load();};
for(const id of ['server','map','route','gaps'])$(id).onchange=()=>{offset=0;if(id==='server'){$('map').value='all';params.delete('big');}void load();};
$('previous-columns').onclick=()=>{offset=Math.max(0,offset-pageSize);void load();};$('next-columns').onclick=()=>{offset+=pageSize;void load();};
for(const b of document.querySelectorAll('[data-close]'))b.onclick=()=>{if(!writing)$(b.dataset.close).close();};

$('choose-map').onclick=()=>{$('choice-error').textContent='';$('choice-dialog').showModal();};
$('choice-dialog').oncancel=e=>{if(writing)e.preventDefault();};
$('confirm-choice').onclick=async()=>{if(writing)return;writing=true;$('confirm-choice').disabled=$('choice').disabled=true;try{await call('POST','/coverage/choice',{map_id:$('choice').value});$('choice-dialog').close();await load();}catch(e){$('choice-error').textContent=e.message;}finally{writing=false;$('confirm-choice').disabled=$('choice').disabled=false;}};
$('progress').onclick=()=>{if(!view)return;const a=view.access;$('progress-summary').textContent=`累计积分 ${a.points}；有效贡献 ${a.valid}；高质量 ${a.high}${a.admin?'；管理账号工作权限独立于贡献等级':''}。`;$('one-status').textContent=a.level>=1?'已达成':'未达成';$('two-status').textContent=a.level>=2?'已达成':'未达成';$('progress-dialog').showModal();};
void load();
})();
