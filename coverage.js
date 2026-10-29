'use strict';
(()=>{
const $=id=>document.getElementById(id),node=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;};
let session=null,view=null,zone='五区',tier='理论',offset=0,ticket=0,target=null,transaction=null,writing=false;
const params=new URLSearchParams(location.search);
if(params.get('server')==='global')$('server').value='global';
if(['五区','四区'].includes(params.get('zone')))zone=params.get('zone');
if(params.get('tier')==='高手')tier='高手';
if(params.get('route')==='special')$('route').value='special';
$('gaps').checked=params.get('gaps')==='true';
if(params.has('q'))$('search').value=params.get('q').slice(0,80);
if(/^[1-6]$/.test(params.get('stars')||''))$('star').value=params.get('stars');
offset=Math.max(0,Math.min(5000,Number(params.get('offset'))||0));
async function call(method,path,body,account=session?.user?.id){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
 try{
 const r=await fetch('/api'+path,{method,signal:controller.signal,credentials:'same-origin',headers:{'Content-Type':'application/json',...(session?{'X-CSRF-Token':session.csrf}:{}),...(account?{'X-Account-ID':account}:{})},...(body?{body:JSON.stringify(body)}:{})});
 const data=await r.json().catch(()=>({detail:'服务器响应无法识别，请刷新核对'}));if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:'字段不符合要求，请核对');return data;
 }catch(e){if(e.name==='AbortError')throw Error('请求超时，请刷新核对；已保存草稿不会自动重复创建。');throw e;}finally{clearTimeout(timer);}
}
function query(){return new URLSearchParams({server:$('server').value,zone,tier,big:$('map').value,route:$('route').value,q:$('search').value,stars:$('star').value,offset:String(offset),gaps:String($('gaps').checked)});}
function option(select,value,text){const o=node('option',text);o.value=value;select.append(o);}
function clear(){ $('head').replaceChildren();$('body').replaceChildren();$('summary').textContent='';view=null; }
async function load(){
 const stamp=++ticket;clear();$('message').textContent='';
 try{
  const currentSession=await call('GET','/auth/me');if(stamp!==ticket)return;session=currentSession;
  if($('server').value==='global'){zone='五区';tier='理论';}
  const chosen=$('map').value==='all'&&params.has('big')?params.get('big'):$('map').value;
  const q=query();if(chosen)q.set('big',chosen);
  const data=await call('GET','/coverage?'+q);if(stamp!==ticket)return;
  if((session.user?.id||null)!==data.user_id)throw Error('账号已变化，请刷新后重试');
  view=data;$('map').replaceChildren();option($('map'),'all','全部地图');$('choice').replaceChildren();
  for(const m of data.maps){option($('map'),m.id,m.name);option($('choice'),m.id,m.name);}
  $('map').value=data.maps.some(m=>m.id===chosen)?chosen:'all';params.delete('big');
  render();if(globalThis.history?.replaceState)history.replaceState(null,'','/score-table?'+query());if(view.production===false)$('message').textContent='独立本地验收，投稿仅进入测试库。';
  const pick=params.get('pick');if(pick){params.delete('pick');const cell=data.rows.flatMap(r=>r.cells).find(c=>c.key===pick);if(cell&&cell.status==='empty')open(cell);else $('message').textContent='所选格子已变化，请重新选择。';}
 }catch(e){if(stamp===ticket){clear();$('message').textContent=e.message;}}
}
function render(){
 const access=view.access,global=view.server==='global';$('star-label').hidden=tier!=='高手';$('choose-map').hidden=global||access.level!==1||!!access.chosen;
 $('rights').textContent=global?'国际服暂仅浏览。':access.admin?'管理账号可查看全部国服成绩。':access.level===2?'国服成绩已全部解锁。':access.chosen&&access.level===1?'已开放所选大地图。':'贡献达标后可解锁成绩。';
 $('sheets').replaceChildren();for(const [z,t] of global?[['五区','理论']]:[['五区','理论'],['五区','高手'],['四区','理论'],['四区','高手']]){const b=node('button',z+' · '+t);b.setAttribute('aria-current',String(z===zone&&t===tier));b.onclick=()=>{zone=z;tier=t;offset=0;void load();};$('sheets').append(b);}
 const h=node('tr');for(const [label,cls] of [['#','row-num'],['大地图','map-col'],['小地图'+($('route').value==='special'?' / 跑法':''),'track-col']]){const th=node('th',label);th.className=cls;h.append(th);}
 for(const c of view.columns){const th=node('th',c.car);th.className='car-col';th.append(node('small',tier==='高手'?c.stars+'星':'满星 '+c.max_stars+'星'));h.append(th);}$('head').replaceChildren(h);
 let filled=0,empty=0;
 view.rows.forEach((row,i)=>{const tr=node('tr');for(const [value,cls] of [[i+1,'row-num'],[row.big,'map-col'],[row.small+(row.route?' / '+row.route:''),'track-col']]){const th=node('th',value);th.className=cls;if(cls==='track-col'&&row.reference){const r=row.reference,ref=node('small','普通理论 '+r.car+' ★'+r.stars+' · '+r.value+'秒');ref.className='row-reference';ref.title='公开普通跑法满星理论参考，不是投稿门槛。';th.append(ref);}tr.append(th);}
  row.cells.forEach((c,j)=>{const td=node('td');td.className=c.status+(c.public?' public-ref':'');
   if(c.status==='filled'){filled++;td.append(node('span',c.value===null?'***':String(c.value)));td.title=c.public?'公开普通跑法满星理论参考，不是投稿门槛。':'已有成绩';}
   else{empty++;const button=node('button');button.className='cell';const label=row.small+' '+view.columns[j].car+(view.columns[j].stars?' '+view.columns[j].stars+'星':'')+' 暂无记录，可投稿';button.setAttribute('aria-label',label);button.title=label;
    if(c.mine){const mark=node('span');mark.className='pending-mark';button.append(mark);button.title+=' · 我的'+({draft:'草稿',pending:'待审核',needs_info:'待补充',accepted:'待发布'}[c.mine.status]||'投稿');}
    button.onclick=()=>open(c);td.append(button);}
   tr.append(td);
  });$('body').append(tr);
 });
 $('summary').textContent=`${view.rows.length}行 · 当前列已填 ${filled} · 待补 ${empty}`;
 $('empty-result').hidden=!!(view.rows.length&&view.columns.length);$('sheet-wrap').hidden=!view.rows.length||!view.columns.length;
 $('column-page').textContent=view.column_total?`${offset+1}–${offset+view.columns.length} / ${view.column_total}列`:'0列';$('previous-columns').disabled=offset===0;$('next-columns').disabled=offset+24>=view.column_total;
}
function open(cell){
 if(!cell.target){$('message').textContent='国际服投稿暂未开放。';return;}
 if(!session.user){const back=new URL('/score-table',location.origin);for(const [k,v] of query())back.searchParams.set(k,v);back.searchParams.set('pick',cell.key);location.assign('/?returnTo='+encodeURIComponent(back.pathname+back.search));return;}
 if(!session.user.verified){$('message').textContent='请先在主页完成邮箱验证。';return;}
 if(cell.mine){location.assign('/submissions#'+cell.mine.id);return;}
 target={...cell.target};target.account=session.user.id;transaction=null;$('time').value='';$('evidence').value='';$('video').value='';$('form-error').textContent='';$('saved-draft').hidden=true;
 $('target').replaceChildren();for(const [k,v] of [['服别','国服'],['地图',target.big+' / '+target.small],['分区 / 档位',zone+' / '+tier],['车辆',target.car+(target.stars?' ★'+target.stars:'（该区满星理论）')],['跑法',target.route||'普通跑法']]){$('target').append(node('dt',k),node('dd',v));}
 $('submit-dialog').showModal();
}
async function submit(publish){
 if(writing||!target)return;writing=true;$('send').disabled=$('save-draft').disabled=true;$('form-error').textContent='';
 try{
  if(!session.user||session.user.id!==target.account)throw Error('账号已变化，请刷新');
  const {account,...base}=target,entry={...base,time:$('time').value.trim(),notes:$('evidence').value.trim(),video_url:$('video').value.trim(),unlisted:false};
  if(publish&&!entry.notes&&!entry.video_url)throw Error('请填写来源说明或视频链接；图片可先保存草稿后补充。');
  const signature=JSON.stringify(entry);if(transaction?.id&&transaction.signature!==signature)throw Error('草稿已保存，请打开草稿修改，避免重复创建。');
  if(!transaction||transaction.signature!==signature)transaction={signature,key:crypto.randomUUID().replaceAll('-','')};
  if(!transaction.id){const result=await call('POST','/submissions',{request_key:transaction.key,entries:[entry]},account);transaction.id=result.ids[0];}
  $('saved-draft').href='/submissions#'+transaction.id;$('saved-draft').hidden=false;
  if(!publish){location.assign($('saved-draft').href);return;}
  await call('POST','/submissions/'+transaction.id+'/submit',{revision:1},account);$('submit-dialog').close();target=null;await load();$('message').textContent='已提交审核，成绩覆盖和积分尚未改变。';
 }catch(e){$('form-error').textContent=e.message;}
 finally{writing=false;$('send').disabled=$('save-draft').disabled=false;}
}
$('filters').onsubmit=e=>{e.preventDefault();offset=0;void load();};
for(const id of ['server','map','route','star','gaps'])$(id).onchange=()=>{offset=0;if(id==='server'){$('map').value='all';params.delete('big');}void load();};
$('previous-columns').onclick=()=>{offset=Math.max(0,offset-24);void load();};$('next-columns').onclick=()=>{offset+=24;void load();};
for(const b of document.querySelectorAll('[data-close]'))b.onclick=()=>{if(!writing)$(b.dataset.close).close();};
$('submit-dialog').oncancel=e=>{if(writing)e.preventDefault();};$('submission-form').onsubmit=e=>{e.preventDefault();void submit(true);};$('save-draft').onclick=()=>{if($('time').reportValidity())void submit(false);};
$('choose-map').onclick=()=>{$('choice-error').textContent='';$('choice-dialog').showModal();};
$('choice-dialog').oncancel=e=>{if(writing)e.preventDefault();};
$('confirm-choice').onclick=async()=>{if(writing)return;writing=true;$('confirm-choice').disabled=$('choice').disabled=true;try{await call('POST','/coverage/choice',{map_id:$('choice').value});$('choice-dialog').close();await load();}catch(e){$('choice-error').textContent=e.message;}finally{writing=false;$('confirm-choice').disabled=$('choice').disabled=false;}};
$('progress').onclick=()=>{if(!view)return;const a=view.access;$('progress-summary').textContent=`累计积分 ${a.points}；有效贡献 ${a.valid}；高质量 ${a.high}${a.admin?'；管理账号工作权限独立于贡献等级':''}。`;$('one-status').textContent=a.level>=1?'已达成':'未达成';$('two-status').textContent=a.level>=2?'已达成':'未达成';$('progress-dialog').showModal();};
void load();
})();
