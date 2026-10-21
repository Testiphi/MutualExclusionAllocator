'use strict';
(()=>{
 const $=id=>document.getElementById(id);let user,csrf,preview,current,retry=null;const picks=new Map();
 const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
 const status={prepared:'待逐项确认',applying:'执行中，需恢复核对',applied:'已应用到测试库',rolling_back:'回滚中，需恢复',recovery_required:'需恢复，禁止继续维护',failed_restored:'执行失败，已恢复原文件',rolled_back:'已回滚'};
 function notice(text){$('message').textContent=text;$('notice').showModal();}
 $('close').onclick=()=>$('notice').close();
 function ask(text){return new Promise(resolve=>{const d=$('confirm');$('confirmText').textContent=text;const done=v=>{d.close();resolve(v);};$('yes').onclick=()=>done(true);$('cancel').onclick=()=>done(false);d.oncancel=e=>{e.preventDefault();done(false);};d.showModal();$('cancel').focus();});}
 async function api(method,path,body){const r=await fetch('/api'+path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf||'','X-Account-ID':user?.id||''},...(body?{body:JSON.stringify(body)}:{})});const d=await r.json();if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'字段无效，请检查输入');return d;}
 let busy=false;async function run(fn){if(busy)return;busy=true;$('main').inert=true;$('busy').hidden=false;try{await fn();}catch(e){notice(e.message+'。若执行请求中断，请先查看批次状态，不要重复新建批次。');}finally{busy=false;$('main').inert=false;$('busy').hidden=true;}}
 function button(text,fn){const b=el('button',text);b.onclick=()=>run(fn);return b;}
 function check(label){const wrap=el('label'),input=el('input');input.type='checkbox';wrap.append(input,document.createTextNode(label));return {wrap,input};}
 function target(i){const p=i.target||i.accepted_payload;return `${p.zone}/${p.tier} ${p.big}/${p.small} ${p.car}★${p.stars??'满星'} ${p.sc?p.sc_type:'普通跑法'}：${i.old??'不存在'} → ${i.new}`;}
 function effects(root,r){root.append(el('h3','完整模拟影响'));for(const e of r.actual_changes)root.append(el('p',`${e.origin==='ordinary_mirror'?'派生普通镜像':'直接变化'} · ${target(e)}`));root.append(el('p',`新增${r.summary.new}，更新${r.summary.updated}，更慢${r.summary.slower}，普通镜像${r.summary.ordinary_mirrors}。两份测试工作簿将同步重导。`));}
 async function list(){const d=await api('GET','/admin/writeback');$('lab').textContent='当前测试目录：'+d.lab;$('batches').replaceChildren();for(const b of d.items){const o=el('option',`${b.id.slice(0,8)} · ${status[b.state]||b.state}`);o.value=b.id;$('batches').append(o);}if(current)$('batches').value=current.id;}
 async function show(id){current=await api('GET','/admin/writeback/'+id);const m=current,root=$('result');root.replaceChildren(el('h3',`${m.id.slice(0,8)} · ${status[m.state]||m.state}`));effects(root,m.result);
 const details=el('details');details.append(el('summary','备份、版本与回执'));details.append(el('pre',JSON.stringify({before:m.before,after:m.after,approval:m.approval,rollback:m.rollback,events:m.events},null,2)));root.append(details);
 if(m.state==='prepared'){
  const approvals=[];
  for(const item of m.result.items){if(item.kind==='unchanged')continue;const section=el('section'),c=check('确认 '+target(item));section.append(c.wrap);const s=check('再次确认接受更慢成绩'),reason=el('textarea');reason.placeholder='更慢成绩写回原因（必填）';reason.setAttribute('aria-label','更慢成绩写回原因');if(item.slower)section.append(s.wrap,reason);root.append(section);approvals.push({item,c,s,reason});}
  const all=check('已核对本批次全部普通镜像和两份测试工作簿同步影响');root.append(all.wrap);
  root.append(button('确认写入测试库',async()=>{
   const items=approvals.map(({item,c,s,reason})=>({submission_id:item.submission_id,confirmed:c.input.checked,slower_confirmed:s.input.checked,slower_reason:reason.value}));
   if(items.some(i=>!i.confirmed)||!all.input.checked)throw Error('请逐项确认及勾选影响确认');
   if(approvals.some(a=>a.item.slower&&(!a.s.input.checked||!a.reason.value.trim())))throw Error('更慢成绩必须再次确认并填写原因');
   if(!await ask(`将写入隔离测试库，直接条目${items.length}，更慢${m.result.summary.slower}，普通镜像${m.result.summary.ordinary_mirrors}。已备份原文件，确认继续？`))return;
   await api('POST',`/admin/writeback/${m.id}/execute`,{digest:m.digest,items,effects_confirmed:true});await show(m.id);await list();notice('测试库写回完成，工作簿已同步；真实数据未操作。');
  }));
 }
 if(['applied','applying','rolling_back','recovery_required'].includes(m.state)){
  const reason=el('textarea');reason.placeholder='填写回滚或恢复原因';reason.setAttribute('aria-label','回滚或恢复原因');root.append(reason);const action=m.state==='applied'?'rollback':'recover';
  root.append(button(action==='rollback'?'回滚整个测试批次':'恢复未完成批次',async()=>{if(!reason.value.trim())throw Error('请填写原因');if(!await ask('恢复本批次执行前的JSON及两份测试工作簿。若有后续编辑将阻止覆盖，确认继续？'))return;await api('POST',`/admin/writeback/${m.id}/${action}`,{reason:reason.value});await show(m.id);await list();notice('原文件已恢复，历史回执保留。');}));
 }
 }
 $('load').onclick=()=>run(async()=>{preview=await api('GET','/admin/previews/'+$('previews').value);picks.clear();retry=null;$('picks').replaceChildren();if(preview.state!=='ready')throw Error('预览已过期或存在阻止项');for(const i of preview.items){const c=check(target(i)+(i.kind==='unchanged'?'（无需改动）':''));c.input.onchange=()=>{if(c.input.checked)picks.set(i.submission_id,{id:i.submission_id,revision:i.revision});else picks.delete(i.submission_id);retry=null;};$('picks').append(c.wrap);}effects($('picks'),preview);});
 $('prepare').onclick=()=>run(async()=>{if(!picks.size)throw Error('至少选择一条');retry??=crypto.randomUUID().replaceAll('-','');current=await api('POST','/admin/writeback',{preview_id:preview.id,items:[...picks.values()],request_key:retry});await show(current.id);await list();notice('备份及工作簿暂存校验完成，请在下方逐项确认。尚未替换测试库。');});
 $('refresh').onclick=()=>run(async()=>{if(!$('batches').value)throw Error('暂无批次');await show($('batches').value);await list();});
 run(async()=>{const session=await api('GET','/auth/me');user=session.user;csrf=session.csrf;if(!session.writeback_lab||user?.role!=='superadmin')throw Error('需要在隔离测试站登录超级管理员');const d=await api('GET','/admin/previews');for(const p of d.items){const o=el('option',p.id.slice(0,8)+' · '+new Date(p.created_at*1000).toLocaleString());o.value=p.id;$('previews').append(o);}await list();});
})();
