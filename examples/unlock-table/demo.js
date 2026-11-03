'use strict';
const D=UnlockDemo,$=id=>document.getElementById(id);
let state, selected='coast', tab='table', toastTimer;
const saved={};
$('profile').innerHTML=Object.entries(D.profiles).map(([id,p])=>`<option value="${id}">${p.name}</option>`).join('');
$('profile').value='near';
function message(copy){clearTimeout(toastTimer);$('toast').textContent=copy;$('toast').hidden=false;toastTimer=setTimeout(()=>$('toast').hidden=true,4500);}
function setTab(next){tab=next;for(const key of ['table','progress']){$(key+'-pane').hidden=key!==next;$(key+'-tab').setAttribute('aria-selected',String(key===next));}}
function load(){const id=$('profile').value;state=saved[id]||{...D.profiles[id]};saved[id]=state;selected=state.chosen||'coast';$('search').value='';render();}
function requirement(field,target,label){const done=state[field]>=target;return `<li><span class="${done?'check':''}">${done?'✓':'○'} ${label} ${state[field]} / ${target}</span></li>`;}
function render(){
 const level=D.level(state), unlocked=D.maps.filter(m=>D.canRead(state,m.id)).length;
 $('profile-label').textContent=state.logged?'演示账号 · '+state.name:'游客预览';
 $('level-title').textContent=level===2?'全部国服查询已开放':level===1?'一级查询权益已达成':'尚未解锁成绩查询';
 $('level-badge').textContent=level===2?'二级权益':level===1?'一级权益':'尚未解锁';
 for(const id of ['points','valid','high'])$(id).textContent=state[id];
 const gap=D.next(state);
 $('progress-copy').textContent=level===2?'全部国服权益已达成，累计积分仍然保留。':level===1?`距离二级：还需 ${gap.points} 积分、${gap.valid} 个有效贡献、${gap.high} 个高质量贡献。`:`还需 ${gap.points} 积分、${gap.valid} 个有效贡献，即可选择首张地图。`;
 const ratios=level===0?[state.points/50,state.valid/5]:[state.points/150,state.valid/15,state.high/5];
 $('bar').style.width=Math.min(100,Math.min(...ratios)*100)+'%';
 $('perk-title').textContent=level===2?'所有国服地图都可以查询':level===1?(state.chosen?'已开放你选择的大地图':'你可以选择首张地图了'):'贡献与查询权益';
 $('perk-copy').textContent=level===2?'按地图、分区、档位和跑法查找记录。后续新增的国服地图也属于这个权益范围。':level===1?(state.chosen?'继续贡献，达到二级后开放全部国服地图。':'在下方选择一张大地图，确认后保留选择；达到二级即可查询全部地图。'):'完成审核的优质投稿推动解锁。重复投稿不会重复累加，积分和查询权益分开记录。';
 $('map-count').textContent=`${unlocked} / ${D.maps.length} 已开放`;
 $('maps').innerHTML=D.maps.map(m=>`<button class="map" data-map="${m.id}" aria-current="${m.id===selected}"><strong>${m.name}</strong><span class="desc">${m.subtitle} · ${m.tracks.length} 张小地图</span><span class="status ${D.canRead(state,m.id)?'open':''}">${D.canRead(state,m.id)?'已开放':level===1&&!state.chosen?'可选择':'未解锁'}</span></button>`).join('');
 for(const button of $('maps').querySelectorAll('button'))button.onclick=()=>{selected=button.dataset.map;renderMap();for(const b of $('maps').children)b.setAttribute('aria-current',String(b===button));};
 $('level-one').innerHTML=requirement('points',50,'累计积分')+requirement('valid',5,'有效贡献');
 $('level-two').innerHTML=requirement('points',150,'累计积分')+requirement('valid',15,'有效贡献')+requirement('high',5,'高质量贡献');
 $('one-status').textContent=level>=1?(state.chosen?'已选择：'+D.maps.find(m=>m.id===state.chosen).name:level===2?'已达成，二级覆盖全部地图':'已达成 · 返回目录选择地图'):'尚未达成 · 两项条件需同时满足';
 $('two-status').textContent=level===2?'已达成 · 所有国服地图开放':'尚未达成 · 三项条件需同时满足';
 $('one-status').className='small '+(level>=1?'green':'muted');$('two-status').className='small '+(level===2?'green':'muted');
 renderMap();setTab(tab);
}
function renderMap(){
 const map=D.maps.find(m=>m.id===selected),open=D.canRead(state,selected),level=D.level(state);
 $('map-title').textContent=map.name;$('map-subtitle').textContent=`${map.tracks.join(' / ')} · 四区 / 五区`;
 $('locked').hidden=open;$('data-view').hidden=!open;
 // Remove previously shown records even when the next map is locked.
 $('rows').replaceChildren();
 if(open){$('track').innerHTML=map.tracks.map(t=>`<option>${t}</option>`).join('');renderRows();return;}
 $('locked-title').textContent=level===1&&!state.chosen?'把它选作你的首张地图':level===1?'这张地图尚未开放':'解锁后，查看这张地图的成绩';
 $('locked-copy').textContent=!state.logged?'登录后可以查看贡献进度。此处可通过顶部状态切换预览解锁体验。':level===1&&!state.chosen?'你已满足一级条件。选择后，这张大地图下的四区、五区查询都会开放，不扣积分。':level===1?'一级权益已用于其他地图。达到二级后，全部国服地图一起开放。':'累计 50 积分并完成 5 个有效贡献，即可自选一张大地图。首页自动选车不受影响。';
 $('unlock-action').textContent=!state.logged?'预览登录后的状态':level===1&&!state.chosen?'选择这张地图':'查看我的解锁进度';
}
function renderRows(){
 if(!D.canRead(state,selected)){$('rows').replaceChildren();return;}
 const query=$('search').value.trim().toLowerCase();
 const rows=D.rows.filter(r=>r.map===selected&&r.track===$('track').value&&r.zone===$('zone').value&&r.tier===$('tier').value&&(!$('route').value||r.route===$('route').value)&&r.car.toLowerCase().includes(query));
 $('rows').innerHTML=rows.map(r=>`<tr><td>${r.car}</td><td>${r.stars} ★</td><td>${r.route==='特殊跑法'?'<span class="route">特殊跑法</span>':r.route}</td><td>${r.tier==='理论'?'理论记录':'高手实测'}</td><td>${r.time}</td></tr>`).join('');
 $('row-count').textContent=`${$('zone').value} · ${$('tier').value} · ${rows.length} 条模拟记录`;$('no-rows').hidden=rows.length>0;
}
$('profile').onchange=load;
$('reset').onclick=()=>{for(const k of Object.keys(saved))delete saved[k];$('profile').value='near';tab='table';load();message('演示已重置，现有账号和数据未被修改。');};
$('table-tab').onclick=()=>setTab('table');$('progress-tab').onclick=$('progress-button').onclick=()=>setTab('progress');$('back').onclick=()=>setTab('table');
$('contribute').onclick=()=>$('submission').showModal();$('close-submission').onclick=()=>$('submission').close();
$('unlock-action').onclick=()=>{
 if(!state.logged){$('profile').value='near';load();message('已切换为模拟登录状态。');return;}
 if(D.level(state)===1&&!state.chosen){$('confirm-copy').textContent=`将使用一级查询权益开放「${D.maps.find(m=>m.id===selected).name}」。选择后不能自行更换；积分不会扣除，达到二级后会开放全部国服地图。`;$('confirm').showModal();}
 else setTab('progress');
};
$('cancel').onclick=()=>$('confirm').close();
$('confirm-choice').onclick=()=>{try{state=D.choose(state,selected);saved[$('profile').value]=state;$('confirm').close();render();message('地图已开放，积分未扣除。本次选择仅保存在演示内存中。');}catch(e){$('confirm').close();message(e.message);}};
for(const id of ['track','zone','tier','route'])$(id).onchange=renderRows;$('search').oninput=renderRows;
load();
