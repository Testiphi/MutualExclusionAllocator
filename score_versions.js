'use strict';
(()=>{
 const $=id=>document.getElementById(id),picks=new Map();let actor,csrf,busy=false,current=null,retry=null,production=false,enabled=true;
 const states={prepared:'待确认',applying:'执行中，需恢复核对',applied:'已发布到测试数据',rolling_back:'回滚中，需恢复',rolled_back:'已回滚（新数据版本）',aborted:'未提交的批次已终止',recovery_required:'需恢复，禁止继续维护'};
 const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
 function notice(text){$('message').textContent=text;$('notice').showModal();}
 $('close').onclick=()=>$('notice').close();
 function ask(text){return new Promise(resolve=>{const d=$('confirm');$('question').textContent=text;const done=v=>{d.close();resolve(v);};$('yes').onclick=()=>done(true);$('cancel').onclick=()=>done(false);d.oncancel=e=>{e.preventDefault();done(false);};d.showModal();$('cancel').focus();});}
 async function api(method,path,body){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),30000);try{const r=await fetch('/api'+path,{method,signal:controller.signal,credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf||'','X-Account-ID':actor?.id||''},...(body?{body:JSON.stringify(body)}:{})});const d=await r.json();if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'字段无效，请检查输入');return d;}catch(e){if(e.name==='AbortError')throw Error('请求超时，请先查看批次历史确认结果，勿重复新建批次');throw e;}finally{clearTimeout(timer);}}

 async function run(fn){if(busy)return;busy=true;$('main').inert=true;$('busy').hidden=false;try{await fn();}catch(e){notice(e.message);}finally{busy=false;$('main').inert=false;$('busy').hidden=true;}}
 function button(text,fn){const b=el('button',text);b.onclick=()=>run(fn);return b;}
 function check(text){const wrap=el('label'),input=el('input');input.type='checkbox';wrap.append(input,document.createTextNode(text));return {wrap,input};}
 function target(p){return `${p.zone}/${p.tier} · ${p.big}/${p.small} · ${p.car}★${p.stars??'满星'} · ${p.sc?p.sc_type:p.route||'普通跑法'}`;}
 function change(i){return `${target(i.target)}：${i.old??'不存在'} → ${i.new??'不存在'}`;}
 async function refresh(){const data=await api('GET','/admin/score-versions');production=!!data.production;enabled=data.write_enabled!==false;states.applied=production?'已发布到正式成绩':'已发布到测试数据';$('prepare').disabled=!enabled;$('source').textContent=`当前数据版本：${data.current.id} · ${production?(enabled?'生产写回已开启':'生产只读验证，写回关闭'):'独立测试目录：'+data.lab}`;
  $('picks').replaceChildren();picks.clear();retry=null;
  for(const item of data.items){const c=check(`${target(item.accepted_payload)} · ${item.accepted_payload.time}秒`);c.input.onchange=()=>{if(c.input.checked)picks.set(item.id,{id:item.id,revision:item.revision});else picks.delete(item.id);retry=null;};$('picks').append(c.wrap);}
  if(!data.items.length)$('picks').append(el('p','暂无待应用的已采纳投稿。已应用/回滚的历史不会重新排队。'));
  $('batches').replaceChildren();for(const item of data.batches){const o=el('option',`${item.id.slice(0,8)} · ${states[item.state]||item.state}`);o.value=item.id;$('batches').append(o);}if(current)$('batches').value=current.id;
 }
 async function show(id){current=await api('GET','/admin/score-versions/'+id);const m=current,root=$('result');root.replaceChildren(el('h3',`${m.id.slice(0,8)} · ${states[m.state]||m.state}`));
  root.append(el('p',`基准版本 ${m.base} → 候选版本 ${m.target}`));if(m.rollback)root.append(el('p','回滚数据版本：'+m.rollback.version));
  root.append(el('p',`新增${m.result.summary.new} · 更新${m.result.summary.updated} · 更慢${m.result.summary.slower} · 普通镜像${m.result.summary.ordinary_mirrors}`));
  root.append(el('h3','本批次完整变更（历史批次展示当时的变更）'));for(const effect of m.result.actual_changes)root.append(el('p',(effect.origin==='ordinary_mirror'?'派生普通镜像 · ':'直接变化 · ')+change(effect)));
  if(m.stale_reasons?.length)root.append(el('p','确认已失效：'+m.stale_reasons.join('；')));
  const detail=el('details');detail.append(el('summary','查看来源、确认、备份及回执'),el('pre',JSON.stringify({source:m.result.source,approval:m.approval,backup:m.backup,rollback:m.rollback,events:m.events},null,2)));root.append(detail);
  if(m.state==='prepared'&&!m.stale_reasons?.length&&enabled){
   const selections=[];
   for(const item of m.result.items){if(item.kind==='unchanged'){root.append(el('p','无需改动：'+change(item)));continue;}
    const section=el('section'),c=check('确认 '+change(item)),slower=check('再次确认接受更慢成绩'),reason=el('textarea');reason.setAttribute('aria-label','更慢成绩写回原因');reason.placeholder='必填：接受更慢成绩的原因';section.append(c.wrap);if(item.slower)section.append(slower.wrap,reason);root.append(section);selections.push({item,c,slower,reason});
   }
   const effects=check('已核对本批次完整变更及普通镜像影响');root.append(effects.wrap);
   root.append(button(production?'确认发布正式成绩':'确认发布到测试数据',async()=>{
    if(selections.some(s=>!s.c.input.checked)||!effects.input.checked)throw Error('请逐项确认全部直接改动和镜像影响');
    if(selections.some(s=>s.item.slower&&(!s.slower.input.checked||!s.reason.value.trim())))throw Error('更慢成绩必须再次勾选并填写原因');
    if(!await ask(`发布${selections.length}条直接变更，其中更慢${m.result.summary.slower}条、普通镜像${m.result.summary.ordinary_mirrors}条，${production?'将改变正式网站成绩':'仅影响本地测试数据'}。确认继续？`))return;
    await api('POST',`/admin/score-versions/${m.id}/execute`,{digest:m.digest,effects_confirmed:true,items:selections.map(s=>({submission_id:s.item.submission_id,confirmed:s.c.input.checked,slower_confirmed:s.slower.input.checked,slower_reason:s.reason.value}))});await show(m.id);await refresh();notice('成绩已发布，版本指针和回执已一起保存；刷新主页即可读取新版本。');
   }));
  }
  if(['applied','applying','rolling_back','recovery_required'].includes(m.state)){
   const reason=el('textarea');reason.placeholder='填写回滚或恢复原因';reason.setAttribute('aria-label','回滚或恢复原因');root.append(reason);const action=m.state==='applied'?'rollback':'recover';
   root.append(button(action==='rollback'?(production?'整批回滚正式成绩':'整批回滚测试成绩'):'恢复未完成批次',async()=>{if(!reason.value.trim())throw Error('请填写原因');if(!await ask('将处理当前环境的成绩版本，账号和后续投稿不会恢复到旧数据库。存在后续成绩版本时禁止直接回滚。确认继续？'))return;await api('POST',`/admin/score-versions/${m.id}/${action}`,{reason:reason.value});await show(m.id);await refresh();notice('操作完成，历史与回执保留。');}));
  }
 }
 $('refresh').onclick=()=>run(refresh);
 $('show').onclick=()=>run(async()=>{if(!$('batches').value)throw Error('暂无批次');await show($('batches').value);});
 $('prepare').onclick=()=>run(async()=>{if(!picks.size||picks.size>50)throw Error('请选择1–50条投稿');retry??=crypto.randomUUID().replaceAll('-','');current=await api('POST','/admin/score-versions',{request_key:retry,items:[...picks.values()]});await show(current.id);await refresh();notice('确认预览已生成，当前成绩尚未改变。请核对下方完整影响。');});
 $('reauth').onclick=()=>run(async()=>{try{const r=await api('POST','/admin/score-versions/reauth',{password:$('password').value});$('reauthStatus').textContent='身份确认有效至 '+new Date(r.expires_at*1000).toLocaleTimeString();notice('身份验证通过，有效期5分钟。');}finally{$('password').value='';}});
 run(async()=>{const me=await api('GET','/auth/me');actor=me.user;csrf=me.csrf;if(!(me.score_versions||me.score_versions_lab)||actor?.role!=='superadmin')throw Error('请在当前网站登录超级管理员');await refresh();});
})();
