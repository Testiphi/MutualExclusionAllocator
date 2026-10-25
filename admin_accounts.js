'use strict';
(()=>{
 const $=id=>document.getElementById(id),el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
 let owner,csrf,offset=0,busy=false,current=null,news=[],usageEnabled=false,selectedAccount=null,activityOffset=0,activityApplied=null;
 function notice(text){$('message').textContent=text;$('notice').showModal();}$('close').onclick=()=>$('notice').close();
 async function api(method,path,body){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);try{const r=await fetch('/api'+path,{method,signal:controller.signal,credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf||'','X-Account-ID':owner?.id||''},...(body?{body:JSON.stringify(body)}:{})});const data=await r.json();if(!r.ok){const e=new Error(typeof data.detail==='string'?data.detail:'输入不正确');e.status=r.status;throw e;}return data;}finally{clearTimeout(timer);}}
 async function run(fn){if(busy)return;busy=true;$('main').inert=true;try{await fn();}catch(e){if([401,403].includes(e.status)){$('main').hidden=true;if($('activityDialog').open)$('activityDialog').close();}notice(e.name==='AbortError'?'请求超时，请刷新核对结果后再操作':e.message);}finally{busy=false;$('main').inert=false;}}
 function ask(text,reason=false){return new Promise(resolve=>{$('question').textContent=text;$('reasonLabel').hidden=!reason;$('reason').value='';const d=$('confirm');const done=value=>{d.close();resolve(value);};$('yes').onclick=()=>{if(reason&&!$('reason').value.trim()){$('reason').focus();return;}done(reason?$('reason').value.trim():true);};$('cancel').onclick=()=>done(false);d.oncancel=e=>{e.preventDefault();done(false);};d.showModal();$('cancel').focus();});}
 function button(text,fn){const b=el('button',text);b.onclick=()=>run(fn);if(['停用账号','强制退出'].includes(text))b.classList.add('ui-danger');return b;}
 const roles={player:'玩家',admin:'管理员',superadmin:'超级管理员'},states={draft:'草稿',published:'已发布',withdrawn:'已撤下'};
 const activityWhen=t=>t===null||t===undefined?'—':new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(t*1000));
 const featureNames={generate:'生成方案',server_switch:'切换服别',garage_save_account:'保存账号车库',garage_save_local:'保存本机车库',submission_submit:'提交成绩',feedback_submit:'新建问题反馈'};
 const resultNames={success:'成功',empty:'无可用方案 / 未选地图',failed:'失败'};
 function meta(parent,text){const n=el('small',text);n.className='account-meta';parent.append(n);}
 async function accounts(){
  const query=new URLSearchParams({q:$('search').value,role:$('role').value,verified:$('verified').value,status:$('status').value,offset:String(offset),activity:usageEnabled?$('activity').value:'all',order:usageEnabled?$('activityOrder').value:'registered'});
  const data=await api('GET','/admin/accounts?'+query);$('count').textContent=`共${data.total}个账号 · 第${Math.floor(offset/50)+1}页`;$('accounts').replaceChildren();$('previous').disabled=!offset;$('next').disabled=offset+50>=data.total;
  for(const item of data.items){
   const tr=el('tr'),identity=el('td'),name=usageEnabled?button(item.email,()=>openActivity(item)):el('strong',item.email);name.className='account-name';identity.append(name);meta(identity,(item.nickname||'未设置昵称')+' · '+(item.leaderboard_anonymous?'榜单匿名':'榜单公开'));tr.append(identity);
   const role=el('td',roles[item.role]||item.role);meta(role,(item.disabled?'已停用':'正常')+' · '+(item.verified?'已验证':'待验证'));tr.append(role);
   const recent=el('td',usageEnabled?activityWhen(item.last_interaction):activityWhen(item.created_at));meta(recent,usageEnabled?'最近交互':'注册时间');meta(recent,(usageEnabled?'访问：':'登录：')+activityWhen(usageEnabled?item.last_visit:item.last_login));tr.append(recent,el('td',String(item.submissions)));
   const actions=el('td');actions.className='account-actions';
   if(usageEnabled)actions.append(button('访问与活跃',()=>openActivity(item)));
   if(item.role==='superadmin')actions.append(el('span','主号保护'));
   else for(const action of [item.disabled?'restore':'disable','logout']){const labels={restore:'恢复账号',disable:'停用账号',logout:'强制退出'};actions.append(button(labels[action],async()=>{const reason=await ask(`${labels[action]}：${item.email}？账号资料和投稿不会删除。${action==='restore'?'恢复后原角色继续有效。':''}`,true);if(!reason)return;await api('POST',`/admin/accounts/${item.id}/control`,{action,reason,revision:item.revision});await accounts();notice('操作完成');}));}
   tr.append(actions);$('accounts').append(tr);
  }
  if(!data.items.length){const tr=el('tr'),td=el('td','暂无符合条件的账号');td.colSpan=5;tr.append(td);$('accounts').append(tr);}
 }
 function activityRange(days){
  const parts=Object.fromEntries(new Intl.DateTimeFormat('en',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()).map(p=>[p.type,p.value]));
  const end=Date.UTC(Number(parts.year),Number(parts.month)-1,Number(parts.day));$('activityEnd').value=new Date(end).toISOString().slice(0,10);$('activityStart').value=new Date(end-(days-1)*86400000).toISOString().slice(0,10);
 }
 async function openActivity(item){
  selectedAccount=item;activityOffset=0;activityApplied=null;$('activityPeriod').value='7';$('activityServer').value='all';activityRange(7);
  $('activityIdentity').textContent=item.email+(item.nickname?' · '+item.nickname:'');$('activityFacts').replaceChildren();$('activityRows').replaceChildren();$('activitySummary').replaceChildren();$('activityMessage').textContent='';$('activityCount').textContent='';
  if(!$('activityDialog').open)$('activityDialog').showModal();await loadActivity(true);
 }
 async function loadActivity(apply=false){
  if(apply){activityOffset=0;activityApplied={start:$('activityStart').value,end:$('activityEnd').value,server:$('activityServer').value};}
  if(!selectedAccount||!activityApplied)return;
  $('activityMessage').textContent='正在读取活动记录…';$('activityRows').replaceChildren();$('activitySummary').replaceChildren();$('activityCount').textContent='';$('activityPrevious').disabled=true;$('activityNext').disabled=true;
  let data;
  try{data=await api('GET','/admin/usage/accounts/'+selectedAccount.id+'?'+new URLSearchParams({...activityApplied,offset:String(activityOffset)}));}
  catch(error){$('activityMessage').textContent=error.name==='AbortError'?'读取超时，可保持筛选条件重试':error.message;if([401,403].includes(error.status))throw error;return;}
  $('activityMessage').textContent='';$('activityStart').value=data.start;$('activityEnd').value=data.end;$('activityServer').value=data.server;
  $('activityFacts').replaceChildren();
  for(const [label,value] of [['注册时间',data.account.created_at],['最近登录',data.account.last_login],['首次观测',data.first_seen],['最近访问',data.last_visit],['最近交互',data.last_interaction]]){const box=el('div');box.append(el('small',label),el('span',activityWhen(value)));$('activityFacts').append(box);}
  for(const [label,value] of [['访问次数',data.summary.opens+data.summary.resumes],['活跃天数',data.summary.active_days],['活跃分钟',data.summary.active_minutes]]){const box=el('div',label+' ');box.append(el('strong',String(value)));$('activitySummary').append(box);}
  for(const item of data.items){const tr=el('tr');for(const text of [item.day,`打开 ${item.opens} · 返回 ${item.resumes}`,String(item.active_minutes)])tr.append(el('td',text));const td=el('td');
   if(!item.features.length)td.textContent='—';
   for(const f of item.features){const n=el('span',`${featureNames[f.feature]||f.feature} · ${resultNames[f.result]||f.result} ${f.uses}次`);n.className='activity-feature';td.append(n);}tr.append(td);$('activityRows').append(tr);
  }
  if(!data.items.length){const tr=el('tr'),td=el('td','该日期与服别范围暂无活动记录');td.colSpan=4;tr.append(td);$('activityRows').append(tr);}
  $('activityCount').textContent=`${data.start} 至 ${data.end} · 共 ${data.total} 天 · 第 ${Math.floor(activityOffset/10)+1} 页`;$('activityPrevious').disabled=!activityOffset;$('activityNext').disabled=activityOffset+10>=data.total;
 }
 $('activityClose').onclick=()=>$('activityDialog').close();
 $('activityForm').onsubmit=e=>{e.preventDefault();if($('activityForm').reportValidity())void run(()=>loadActivity(true));};
 $('activityPeriod').onchange=()=>{if($('activityPeriod').value!=='custom'){activityRange(Number($('activityPeriod').value));void run(()=>loadActivity(true));}};
 for(const id of ['activityStart','activityEnd'])$(id).onchange=()=>{$('activityPeriod').value='custom';};
 $('activityPrevious').onclick=()=>run(async()=>{activityOffset=Math.max(0,activityOffset-10);await loadActivity();});
 $('activityNext').onclick=()=>run(async()=>{activityOffset+=10;await loadActivity();});
 function form(item=null){current=item;$('title').value=item?.title||'';$('body').value=item?.body||'';$('release').value=item?.release_label||'';$('newsState').textContent=item?`状态：${states[item.state]} · 版本${item.revision}`:'新公告草稿';$('announcementPreview').replaceChildren();$('publish').disabled=!item;$('withdraw').disabled=!item||item.state!=='published';}
 async function listNews(){news=(await api('GET','/admin/announcements')).items;$('announcements').replaceChildren();for(const item of news){const o=el('option',`${item.title} · ${states[item.state]}`);o.value=item.id;$('announcements').append(o);}if(current){current=news.find(n=>n.id===current.id);$('announcements').value=current?.id||'';}}
 const dirty=()=>!current?Boolean($('title').value||$('body').value||$('release').value):($('title').value!==current.title||$('body').value!==current.body||$('release').value!==current.release_label);
 $('usersTab').onclick=()=>run(async()=>{$('users').hidden=false;$('news').hidden=true;await accounts();});
 $('newsTab').onclick=()=>run(async()=>{$('users').hidden=true;$('news').hidden=false;await listNews();});
 $('query').onclick=()=>run(async()=>{offset=0;await accounts();});$('previous').onclick=()=>run(async()=>{offset=Math.max(0,offset-50);await accounts();});$('next').onclick=()=>run(async()=>{offset+=50;await accounts();});
 $('new').onclick=()=>run(async()=>{if((dirty()||!current&&$('body').value)&&!await ask('放弃未保存的公告内容？'))return;form();});
 $('load').onclick=()=>run(async()=>{if(dirty()&&!await ask('放弃当前未保存修改？'))return;form(news.find(n=>n.id===$('announcements').value));});
 $('preview').onclick=()=>{$('announcementPreview').replaceChildren(el('h3',$('title').value),el('p',$('release').value),el('p',$('body').value));};
 $('save').onclick=()=>run(async()=>{const body={title:$('title').value,body:$('body').value,release_label:$('release').value};if(current?.state==='published'&&!await ask('修改已发布公告的内容？不会重新提醒已忽略该公告的用户。'))return;const r=await api(current?'PUT':'POST',current?'/admin/announcements/'+current.id:'/admin/announcements',current?{...body,revision:current.revision}:body);const id=current?.id||r.id;await listNews();form(news.find(n=>n.id===id));notice('公告已保存');});
 for(const action of ['publish','withdraw'])$(action).onclick=()=>run(async()=>{if(!current)throw Error('请先保存公告');if(dirty())throw Error('请先保存或放弃修改，再改变发布状态');if(!await ask(action==='publish'?'发布这条公告，符合提醒设置的用户将看到弹窗？':'撤下这条公告？历史选择和记录保留。'))return;const id=current.id;await api('POST','/admin/announcements/'+id+'/state',{action,revision:current.revision});await listNews();form(news.find(n=>n.id===id));notice(action==='publish'?'公告已发布':'公告已撤下');});
 addEventListener('focus',()=>{if(!owner)return;void api('GET','/auth/me').then(session=>{if(session.user?.id!==owner.id||session.user?.role!=='superadmin'){$('main').hidden=true;if($('activityDialog').open)$('activityDialog').close();notice('账号或权限已变化，请刷新页面重新登录。');}}).catch(()=>{});});
 run(async()=>{const session=await api('GET','/auth/me');owner=session.user;csrf=session.csrf;if(owner?.role!=='superadmin')throw Error('此页面仅超级管理员可用');$('identity').textContent=owner.email+' · 超级管理员'+(session.mail_mode==='production'?'':' · 本地环境');usageEnabled=session.usage===true;$('activityFilter').hidden=!usageEnabled;$('activityOrderFilter').hidden=!usageEnabled;$('activityHeading').textContent=usageEnabled?'最近活动':'注册 / 最近登录';$('main').hidden=false;await accounts();form();});
})();
