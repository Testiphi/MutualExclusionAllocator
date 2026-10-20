'use strict';
(()=>{
    const $=id=>document.getElementById(id),picks=new Map();
    let user,csrf,offset=0,busy=false,current=null,configured=false,retryRequest=null;
    const names={new:'新增',placeholder:'填入占位',update:'更新',unchanged:'无需改动',conflict:'冲突'};
    function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
    function notice(text){$('previewNoticeText').textContent=text;if(!$('previewNotice').open)$('previewNotice').showModal();$('previewNoticeClose').focus();}
    $('previewNoticeClose').onclick=()=>$('previewNotice').close();
    async function fetchResponse(method,path,body){
        const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),60000);
        try{
            const response=await fetch('/api'+path,{method,credentials:'same-origin',signal:controller.signal,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf||'',...(user?{'X-Account-ID':user.id}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
            if(!response.ok){const data=await response.json().catch(()=>({}));throw new Error(typeof data.detail==='string'?data.detail:'请求失败，请刷新后重试');}
            return response;
        }catch(e){if(e.name==='AbortError')throw new Error('预览请求超时，可重试同一选择或检查历史预览；正式库不会被写入。');throw e;}finally{clearTimeout(timer);}
    }
    async function request(method,path,body){return (await fetchResponse(method,path,body)).json();}
    async function run(fn){if(busy)return;busy=true;$('previewMain').inert=true;$('previewBusy').hidden=false;try{await fn();}catch(e){notice(e.message);}finally{busy=false;$('previewMain').inert=false;$('previewBusy').hidden=true;}}
    function button(text,fn){const b=el('button',text);b.type='button';b.onclick=()=>run(fn);return b;}
    function target(p){return p?`${p.zone}/${p.tier} · ${p.big}/${p.small}\n${p.car} ${p.stars===null?'无星级':'★'+p.stars} · ${p.sc?p.sc_type:p.route||'普通跑法'}`:'目标无效';}
    function value(v){return v===null||v===undefined?'—':String(v);}
    function table(headers){const wrap=el('div');wrap.className='table-wrap';const t=el('table');t.className='preview-table';const head=el('thead'),tr=el('tr');headers.forEach(h=>tr.append(el('th',h)));head.append(tr);const body=el('tbody');t.append(head,body);wrap.append(t);return {wrap,body};}
    function row(body,values){const tr=el('tr');for(const v of values){const td=el('td');if(v instanceof Node)td.append(v);else td.textContent=value(v);tr.append(td);}body.append(tr);return tr;}
    function picked(){ $('pickCount').textContent=`已选 ${picks.size} 条（最多50条）`; }
    async function source(){const info=await request('GET','/admin/preview-source');configured=info.configured;
        $('sourceInfo').textContent=info.configured?`${info.source.directory}\n成绩 SHA256：${info.source.data_sha256}\n规则 SHA256：${info.source.cars_sha256}`:'未配置来源，请通过启动参数 --preview-source 指定正式维护仓库；不会默认使用旧功能分支JSON。';
        $('generatePreview').disabled=!configured;
    }
    async function candidates(){const data=await request('GET','/admin/accepted-submissions?offset='+offset);
        const t=table(['选择','拟采纳目标','拟采纳值','评分 / 原因','审核版本']);
        for(const item of data.items){const c=el('input');c.type='checkbox';c.checked=picks.has(item.id);c.setAttribute('aria-label','选择 '+item.id.slice(0,8));c.onchange=()=>{if(c.checked){if(picks.size>=50){c.checked=false;notice('每批最多50条');return;}picks.set(item.id,{id:item.id,revision:item.revision});}else picks.delete(item.id);retryRequest=null;picked();};
            const p=item.accepted_payload,desc=el('span',target(p));desc.className='preview-target';
            row(t.body,[c,desc,p?(['普通','自动'].includes(p.tier)?'✓（投稿成绩保留）':p.time):'缺少内容',`${item.review_score===null?'未评分':item.review_score+'/5'}\n${item.decision_reason||''}`,`${item.id.slice(0,8)} / v${item.revision}`]);}
        $('candidateTable').replaceChildren(t.wrap);$('candidateCount').textContent=`共${data.total}条，当前${data.items.length}条`;
        $('candidatePrevious').disabled=offset===0;$('candidateNext').disabled=offset+50>=data.total;
    }
    async function history(){const data=await request('GET','/admin/previews');const select=$('previewHistory');select.replaceChildren();const first=el('option','请选择历史预览');first.value='';select.append(first);
        for(const item of data.items){const o=el('option',`${new Date(item.created_at*1000).toLocaleString()} · ${item.id.slice(0,8)} · ${item.generated_state==='ready'?'生成时有效':'生成时有阻止项'}`);o.value=item.id;select.append(o);}if(current)select.value=current.id;
    }
    async function show(id){current=await request('GET','/admin/previews/'+id);const root=$('previewResult');root.replaceChildren();$('previewHistory').value=id;
        root.append(el('h3',`预览 ${id.slice(0,8)} · ${current.state==='ready'?'当前有效（只读、未确认）':current.state==='stale'?'已过期，请重新生成':'存在阻止项'}`));
        if(current.stale_reasons.length){const warning=el('p',current.stale_reasons.join('\n'));warning.className='preview-warning';root.append(warning);}
        if(current.errors.length){const warning=el('p',current.errors.join('\n'));warning.className='preview-warning';root.append(warning);}
        const metrics=el('div');metrics.className='preview-summary';const labels={new:'新增',placeholder:'填占位',updated:'更新',slower:'其中更慢',faster:'其中更快',ordinary_mirrors:'派生普通镜像',unchanged:'无需改动',conflicts:'冲突'};
        for(const [key,label] of Object.entries(labels))metrics.append(el('span',`${label} ${current.summary[key]}`));root.append(metrics);
        const moved=current.items.filter(i=>i.review_basis_changed).length;
        if(moved){const warning=el('p',`${moved}条投稿的审核参考库与当前正式库不同。本次按正式库重新计算旧值；不能沿用旧审核作为写回确认。`);warning.className='preview-warning';root.append(warning);}
        root.append(el('p','本次来源：'+current.source.directory,'muted'));
        const t=table(['拟采纳目标','当前旧值','候选新值','分类','来源 / 原因']);
        for(const item of current.items){const desc=el('span',target(item.target||item.accepted_payload));desc.className='preview-target';const classification=(names[item.kind]||item.kind)+(item.slower?' · 更慢':item.faster?' · 更快':'');
            const tr=row(t.body,[desc,item.old,item.new,classification,`${item.submission_id.slice(0,8)} / v${item.revision}\n${item.error||item.review_reason||''}`]);if(item.slower)tr.className='slower';}
        root.append(el('h3','直接候选与无需改动'),t.wrap);
        const actual=table(['目标','模拟前','模拟后','影响来源','详情']);
        for(const effect of current.actual_changes){const desc=el('span',target(effect.target));desc.className='preview-target';const details=el('details');details.append(el('summary','条目差异'),el('pre',JSON.stringify({before:effect.before_entry,after:effect.after_entry},null,2)));
            row(actual.body,[desc,effect.old,effect.new,(effect.origin==='ordinary_mirror'?'派生普通镜像':'直接改动')+(effect.mirror_contributors?'（与高手派生镜像合并展示）':''),details]);}
        root.append(el('h3','模拟后的实际数据差异'),actual.wrap,el('p','理论/高手列表沿用现有排序与格式化；不自动同步四五区、不额外调整自动档白名单、不删除其他档位。普通/自动的明确归档候选仅表示可用性。'));
        const downloads=el('div');downloads.className='preview-downloads';
        for(const [kind,label] of [['changes','下载未确认变更清单'],['preview','下载独立预览JSON'],['manifest','下载来源与校验清单']]){
            const b=button(label,async()=>{const response=await fetchResponse('GET',`/admin/previews/${id}/download?kind=${kind}`);const blob=await response.blob();const url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download=id+'.'+(kind==='changes'?'changes.review.json':kind+'.json');document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);});b.disabled=current.state!=='ready';downloads.append(b);
        }
        root.append(downloads,el('p','下载前服务端会再次核对来源和投稿版本。清单accepted全部为false；本阶段没有确认写回或发布按钮。','warning'));
        const hashes=el('details');hashes.append(el('summary','基线与工具校验值'),el('pre',JSON.stringify({source:current.source,engine:current.engine,changes_sha256:current.changes_sha256,preview_sha256:current.preview_sha256},null,2)));root.append(hashes);
    }
    $('reloadCandidates').onclick=()=>run(async()=>{await source();await candidates();await history();if(current)await show(current.id);});
    $('clearPicks').onclick=()=>run(async()=>{picks.clear();retryRequest=null;picked();await candidates();});
    $('candidatePrevious').onclick=()=>run(async()=>{offset=Math.max(0,offset-50);await candidates();});$('candidateNext').onclick=()=>run(async()=>{offset+=50;await candidates();});
    $('generatePreview').onclick=()=>run(async()=>{if(!picks.size){notice('请先选择至少一条已采纳投稿');return;}const items=[...picks.values()].sort((a,b)=>a.id.localeCompare(b.id)),signature=JSON.stringify(items);
        if(!retryRequest||retryRequest.signature!==signature)retryRequest={signature,key:crypto.randomUUID().replaceAll('-','')};
        const result=await request('POST','/admin/previews',{request_key:retryRequest.key,items});retryRequest=null;await history();await show(result.id);notice('只读预览已生成。请查看直接变化、普通镜像及阻止项；没有写入正式库。');
    });
    $('previewHistory').onchange=()=>{if($('previewHistory').value)void run(()=>show($('previewHistory').value));};
    $('checkPreview').onclick=()=>run(async()=>{if(current)await show(current.id);else notice('请先选择或生成一个预览');});
    async function init(){const session=await request('GET','/auth/me');user=session.user;csrf=session.csrf;
        if(!user||!['admin','superadmin'].includes(user.role)){$('previewIdentity').textContent='请登录管理员账号';notice('此页面仅管理员可用');return;}
        $('previewIdentity').textContent=user.email+' · '+(user.role==='superadmin'?'超级管理员':'管理员');$('previewMain').hidden=false;if(session.writeback_lab&&user.role==='superadmin'){const a=el('a','隔离测试：逐项确认与写回');a.href='/writeback-lab';$('previewIdentity').after(a);}await source();await candidates();await history();
    }
    void init().catch(e=>notice(e.message));
})();
