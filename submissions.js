'use strict';
(() => {
    const $=id=>document.getElementById(id);
    const statuses={draft:'草稿',pending:'待审核',needs_info:'需要补充',accepted:'已采纳，待应用',ignored:'未采纳'};
    const kinds={new:'新增成绩',placeholder:'填入已有占位',same:'与参考库一致',faster:'比当前更快',slower:'比当前更慢',rule_needed:'需要维护规则',invalid:'暂不能比较',availability_existing:'该档已收录可用性',availability_new:'新增可用性归档建议'};
    const actions={created:'保存草稿',edited:'补充或编辑',submitted:'提交审核',image_added:'补充图片',image_removed:'移除当前证据（历史保留）',accept:'采纳',needs_info:'要求补充',ignore:'忽略',reopened:'重新审核'};
    let user,csrf,catalog,scope='mine',offset=0,selected=null,busy=false,preview=null,formSerial=0;
    let listTicket=0,detailTicket=0,activeForm=null,batchRequest=null,unsaved=false;
    function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
    let actionFocus=null,noticeFocus=null;
    $('noticeClose').onclick=()=>$('noticeDialog').close();
    $('noticeDialog').addEventListener('close',()=>{
        if(noticeFocus?.isConnected&&!noticeFocus.disabled)noticeFocus.focus();
        noticeFocus=null;
    });
    function say(text,focusTarget=null){
        $('message').textContent=text;
        $('noticeText').textContent=text;
        noticeFocus=focusTarget||actionFocus;
        const dialog=$('noticeDialog');
        if(!dialog.open)dialog.showModal();
        $('noticeClose').focus();
    }
    async function request(method,path,body){
        const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),15000);
        try{
            const response=await fetch('/api'+path,{method,credentials:'same-origin',signal:controller.signal,
                headers:{'Content-Type':'application/json','X-CSRF-Token':csrf||'',...(user?{'X-Account-ID':user.id}:{})},
                ...(body===undefined?{}:{body:JSON.stringify(body)})});
            const data=await response.json().catch(()=>{throw new Error('服务器返回了无法识别的响应，请稍后重试；若刚才进行了保存，请先刷新列表核对结果。');});
            if(!response.ok){const e=new Error(typeof data.detail==='string'?data.detail:'字段格式不正确，请检查星级、成绩和文字长度');e.status=response.status;throw e;}
            return data;
        }catch(e){if(e.name==='AbortError')throw new Error('请求超时；草稿可能已保存，请重试或刷新列表核对，不要反复新建。');if(e instanceof TypeError)throw new Error('网络连接失败，请检查本地服务是否运行。若刚才进行了保存，请先刷新列表核对结果。');throw e;}
        finally{clearTimeout(timer);}
    }
    async function run(fn){
        if(busy)return;actionFocus=document.activeElement;busy=true;document.body.setAttribute('aria-busy','true');
        $('compose').inert=true;$('workspace').inert=true;$('navigation').inert=true;
        try{await fn();}catch(e){say(e.message+(e.status===401?'。请返回首页重新登录，再刷新本页。':''));}
        finally{busy=false;document.body.removeAttribute('aria-busy');$('compose').inert=false;$('workspace').inert=false;$('navigation').inert=false;}
    }
    function ask(text){return new Promise(resolve=>{
        const dialog=$('confirmDialog');$('confirmText').textContent=text;
        function finish(result){dialog.close();resolve(result);}
        $('confirmYes').disabled=false;$('confirmCancel').disabled=false;
        $('confirmYes').onclick=()=>finish(true);$('confirmCancel').onclick=()=>finish(false);
        dialog.oncancel=e=>{e.preventDefault();finish(false);};dialog.showModal();$('confirmCancel').focus();
    });}
    function option(select,value,text){const n=el('option',text);n.value=value;select.append(n);}
    function field(container,label,name,type='text'){
        const wrapper=el('label',label),input=el(type==='select'?'select':type==='textarea'?'textarea':'input');
        if(type!=='select'&&type!=='textarea')input.type=type;input.dataset.field=name;
        wrapper.append(input);container.append(wrapper);return input;
    }
    function scoreForm(initial={},title='成绩条目'){
        const node=el('section',undefined,'score-form');node.append(el('h3',title));const fields=el('div',undefined,'fields');node.append(fields);
        const zone=field(fields,'分区','zone','select');['五区','四区'].forEach(v=>option(zone,v,v));zone.value=initial.zone||'五区';
        const tier=field(fields,'建议档位','tier','select');['高手','理论','普通','自动'].forEach(v=>option(tier,v,v));tier.value=initial.tier||'高手';
        const big=field(fields,'大地图','big','select');option(big,'','请选择');[...new Set(catalog.tracks.map(t=>t.big))].forEach(v=>option(big,v,v));big.value=initial.big||'';
        const small=field(fields,'小地图','small','select');
        const car=field(fields,'车辆（昵称或真名）','car');car.maxLength=150;car.value=initial.car||'';
        const suggestions=el('datalist');suggestions.id='cars-'+(++formSerial);car.setAttribute('list',suggestions.id);fields.append(suggestions);
        const stars=field(fields,'实际星级（高手必选）','stars','select');
        const route=field(fields,'跑法','route','select');option(route,'','普通跑法');catalog.routes.forEach(v=>option(route,v,v));route.value=initial.route||'';
        const time=field(fields,'成绩（秒或分:秒）','time');time.maxLength=24;time.placeholder='例如 26.52 或 1:02.345';time.value=initial.time||'';
        const url=field(fields,'视频 / 来源链接（可选）','video_url','url');url.maxLength=1000;url.value=initial.video_url||'';
        const notes=field(fields,'说明、来源或需要补充的资料','notes','textarea');notes.maxLength=2000;notes.value=initial.notes||'';notes.parentElement.className='wide';
        const unlisted=field(fields,'车辆、地图或跑法尚未收录（填写详细说明）','unlisted','checkbox');unlisted.checked=!!initial.unlisted;unlisted.parentElement.className='check wide';
        function maps(){const previous=small.value;small.replaceChildren();option(small,'','请选择');catalog.tracks.filter(t=>t.big===big.value).forEach(t=>option(small,t.small,t.small));small.value=previous;}
        function cars(){suggestions.replaceChildren();catalog.cars.filter(c=>c.zones.includes(zone.value)).forEach(c=>option(suggestions,c.name,c.title));}
        function starOptions(current){const c=catalog.cars.find(c=>c.name===car.value||c.title===car.value);stars.replaceChildren();option(stars,'','请选择 / 无星级条目');const bounds=c?.limits[zone.value]||[1,6];for(let i=bounds[0];i<=bounds[1];i++)option(stars,String(i),String(i)+'星');if(current&&!Array.from(stars.options).some(o=>o.value===current))option(stars,current,current+'星（不符合当前规则）');stars.value=current||'';}
        maps();small.value=initial.small||'';cars();starOptions(initial.stars===null||initial.stars===undefined?'':String(initial.stars));
        big.onchange=maps;zone.onchange=()=>{cars();starOptions(stars.value);};car.onchange=()=>starOptions(stars.value);
        node.append(el('p','普通/自动档采纳后仅形成可用性归档建议，投稿成绩仍保留，不自动改写其他档位。','muted'));
        const read=()=>({big:big.value,small:small.value,zone:zone.value,tier:tier.value,car:car.value.trim(),stars:stars.value?Number(stars.value):null,route:route.value,time:time.value.trim(),notes:notes.value.trim(),video_url:url.value.trim(),unlisted:unlisted.checked});
        return {node,read};
    }
    function summary(value){if(!value)return '未采纳';if(value.unlisted)return '未收录资料建议\n'+value.notes;return `${value.zone} / ${value.tier}\n${value.big} · ${value.small}\n${value.car} ${value.stars===null?'无星级':'★'+value.stars} / ${value.route||'普通跑法'}\n成绩：${value.time} 秒\n${value.notes||''}`;}
    function column(title,text){const node=el('div',undefined,'summary');node.append(el('strong',title),el('span',text));return node;}
    function compareText(c){return `${kinds[c?.kind]||'未比较'}${c?.old!==null&&c?.old!==undefined?'\n当前记录：'+c.old+(String(c.kind).startsWith('availability')?'':' 秒'):''}${c?.delta!==null&&c?.delta!==undefined?'\n变化：'+c.delta+' 秒':''}\n${c?.effect||''}`;}
    function button(text,fn){const n=el('button',text);n.type='button';n.onclick=()=>run(fn);return n;}
    function newRow(){
        if($('draftRows').children.length>=20){say('一批最多20条');return;}
        const form=scoreForm({},'成绩 '+($('draftRows').children.length+1));
        form.node.readEntry=form.read;form.node.addEventListener('input',()=>{unsaved=true;});
        form.node.append(button('移除此行',async()=>{if(await ask('移除此行尚未保存的输入？')){form.node.remove();unsaved=true;}}));
        $('draftRows').append(form.node);
    }
    async function switchView(view){
        if(unsaved){if(!await ask('离开前尚有未保存的输入。确认放弃这些输入？'))return;if(!$('compose').hidden)$('draftRows').replaceChildren();}
        unsaved=false;detailTicket++;selected=null;preview=null;
        $('compose').hidden=view!=='new';$('workspace').hidden=view==='new';
        if(view==='new'){if(!$('draftRows').children.length)newRow();return;}
        scope=view==='review'?'review':'mine';offset=0;
        $('listTitle').textContent=scope==='review'?'审核工作台':'我的投稿';$('statusFilter').value=scope==='review'?'pending':'';
        $('detail').replaceChildren(el('p','选择一条投稿查看内容。'));await loadList();
    }
    async function loadList(){
        const ticket=++listTicket;
        const query=new URLSearchParams({scope,status:$('statusFilter').value,q:$('search').value,offset:String(offset)});
        const data=await request('GET','/submissions?'+query);
        if(ticket!==listTicket)return;
        $('count').textContent=`共 ${data.total} 条 · 当前 ${data.items.length} 条`;
        $('list').replaceChildren();
        for(const item of data.items){
            const p=item.payload,n=button(`${p.unlisted?'资料补充建议':(p.small||'未选地图')+' · '+(p.car||'未选车辆')}`,async()=>{
                if(unsaved&&!await ask('当前修改未保存，确认切换投稿？'))return;
                unsaved=false;await loadDetail(item.id);
            });
            n.className='queue-item';n.setAttribute('aria-current',String(item.id===selected?.id));
            n.append(el('small',`${statuses[item.status]} · ${item.review_score===null?'未评分':item.review_score+'/5分'} · ${p.zone}/${p.tier} · ${p.time||'未填'}秒`),el('small',new Date(item.updated_at*1000).toLocaleString()));
            $('list').append(n);
        }
        if(!data.items.length)$('list').append(el('p','暂无符合条件的投稿。','muted'));
        $('previous').disabled=offset===0;$('next').disabled=offset+50>=data.total;
    }
    async function loadDetail(id){
        const ticket=++detailTicket;
        const item=await request('GET','/submissions/'+id);
        if(ticket!==detailTicket)return;
        selected=item;preview=null;activeForm=null;renderDetail();
        document.querySelectorAll('.queue-item').forEach(n=>n.removeAttribute('aria-current'));
    }
    function renderDetail(){
        const item=selected,root=$('detail');root.replaceChildren();
        root.append(el('h2',item.payload.unlisted?'资料补充建议':item.payload.small+' · '+item.payload.car),el('span',statuses[item.status],'badge'));
        root.append(el('p',item.review_score===null?'质量评分：暂未评分':`质量评分：${item.review_score} / 5`));
        root.append(el('p',`投稿 ${item.id.slice(0,8)} · 版本 ${item.revision} · 投稿人 ${item.owner_id.slice(0,8)}`,'muted'));
        if(item.decision_reason)root.append(el('p','审核反馈：'+item.decision_reason,'warning'));
        const grid=el('div',undefined,'comparison-grid');grid.append(column('玩家提交（当前版本）',summary(item.payload)),column('参考库对比',compareText(item.comparison)),column('拟采纳 / 已采纳',summary(item.accepted_payload)));root.append(grid);
        if(item.baseline)root.append(el('p',`记录的参考数据 ${item.baseline.data.slice(0,12)} / 规则 ${item.baseline.cars.slice(0,12)}`,'muted'));
        root.append(el('h3','证据'));
        if(item.payload.video_url){const a=el('a','打开玩家提供的来源链接（外部网站）');a.href=item.payload.video_url;a.target='_blank';a.rel='noopener noreferrer';root.append(a);}
        const images=el('div',undefined,'evidence');for(const img of item.images){const a=el('a');a.href=img.url;a.target='_blank';a.rel='noopener';const image=el('img');image.src=img.url;image.alt='投稿证据图片';image.onerror=()=>{if(image.isConnected)say('证据图片加载失败，请检查登录状态和网络连接，再刷新详情重试。');};a.append(image);const card=el('div');card.append(a);
            if(item.owner_id===user.id&&['draft','needs_info'].includes(item.status))card.append(button('移除此图片',async()=>{
                if(unsaved){say('请先保存条目修改。');return;}
                if(!await ask('从本次投稿中移除此图片？已产生的历史记录仍会保留。'))return;
                await request('DELETE',`/submissions/${item.id}/images/${img.id}`,{revision:item.revision});await refreshItem(item.id);say('已移除当前证据，历史记录保留。');
            }));images.append(card);}root.append(images);
        if(item.owner_id===user.id&&['draft','needs_info'].includes(item.status))renderEdit(root,item);
        if(['admin','superadmin'].includes(user.role)&&item.status==='pending')renderReview(root,item);
        if(['admin','superadmin'].includes(user.role)&&['accepted','ignored'].includes(item.status)){
            const label=el('label','重新审核原因'),reason=el('textarea');reason.maxLength=2000;label.append(reason);root.append(label,button('重新打开审核',async()=>{
                if(!reason.value.trim()){say('请填写重新审核原因。',reason);return;}
                if(!await ask('撤回当前决定并重新进入待审核？原决定会保留在历史中。'))return;
                await request('POST',`/admin/submissions/${item.id}/review`,{revision:item.revision,action:'reopen',reason:reason.value});await refreshItem(item.id);say('已重新打开审核');
            }));
        }
        if(item.same_target.length){root.append(el('h3','其他同目标投稿'));for(const other of item.same_target)root.append(button(`${other.id.slice(0,8)} · ${statuses[other.status]}`,()=>loadDetail(other.id)));}
        const history=el('details');history.append(el('summary','投稿与审核历史（'+item.events.length+'条）'));
        for(const event of item.events){const row=el('div',undefined,'audit');row.append(el('strong',`v${event.revision} ${actions[event.action]||event.action} · ${new Date(event.created_at*1000).toLocaleString()}`));row.append(el('p',(event.snapshot.review_score===null||event.snapshot.review_score===undefined?'未评分':event.snapshot.review_score+'/5分')+' · '+(event.snapshot.reason||''),'muted'));const details=el('details');details.append(el('summary','查看此版本内容'),el('pre',JSON.stringify(event.snapshot,null,2)));for(const [index,iid] of (event.snapshot.images||[]).entries()){const link=el('a','查看此版本证据 '+(index+1));link.href=`/api/submissions/${item.id}/images/${iid}`;link.target='_blank';link.rel='noopener';const paragraph=el('p');paragraph.append(link);details.append(paragraph);}row.append(details);history.append(row);}root.append(history);
    }
    async function refreshItem(id){unsaved=false;await loadList();await loadDetail(id);}
    function renderEdit(root,item){
        activeForm=scoreForm(item.payload,'修改草稿 / 补充资料');root.append(activeForm.node);activeForm.node.addEventListener('input',()=>{unsaved=true;});
        const fileLabel=el('label','证据图片：PNG/JPEG/WebP，每张≤2MB，最多3张'),file=el('input');file.type='file';file.accept='image/png,image/jpeg,image/webp';fileLabel.append(file);root.append(fileLabel);
        root.append(button('上传证据图片',async()=>{
            if(unsaved){say('请先保存条目修改，再上传图片。');return;}
            const picture=file.files[0];if(!picture){say('请选择图片');return;}if(picture.size>2*1024*1024){say('图片不能超过2MB');return;}
            const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(new Error('本地图片读取失败，请重新选择图片后重试。'));reader.onabort=()=>reject(new Error('图片读取已中断，请重新选择图片。'));reader.readAsDataURL(picture);});
            await request('POST',`/submissions/${item.id}/images`,{revision:item.revision,data});await refreshItem(item.id);say('图片已保存；转换为JPEG并移除元数据。');
        }));
        const buttons=el('div',undefined,'actions');buttons.append(button('保存修改',async()=>{
            await request('PUT','/submissions/'+item.id,{revision:item.revision,entry:activeForm.read()});await refreshItem(item.id);say('草稿已保存');
        }),button('预览并提交审核',async()=>{
            if(unsaved){say('请先保存修改，再预览提交。');return;}
            if(!await ask(summary(item.payload)+'\n\n提交后不能直接修改，需等待审核反馈。确认提交？'))return;
            await request('POST',`/submissions/${item.id}/submit`,{revision:item.revision});await refreshItem(item.id);say('已提交，等待审核');
        }));root.append(buttons);
    }
    function renderReview(root,item){
        const form=scoreForm(item.payload,'拟采纳内容（不会覆盖玩家原始投稿）');root.append(form.node);
        const reasonLabel=el('label','审核理由 / 给玩家的反馈'),reason=el('textarea');reason.maxLength=2000;reasonLabel.append(reason);root.append(reasonLabel);
        const scoreLabel=el('label','质量评分（与是否采纳分开）'),score=el('select');option(score,'','暂不评分');for(let i=0;i<=5;i++)option(score,String(i),i+' / 5');scoreLabel.append(score);root.append(scoreLabel);
        const result=el('div',undefined,'summary');result.textContent='先预览拟采纳内容，再确认采纳。';root.append(result);
        const slowerLabel=el('label','我已核对并确认采纳这个更慢的成绩','check'),slower=el('input');slower.type='checkbox';slowerLabel.prepend(slower);slowerLabel.hidden=true;root.append(slowerLabel);
        const accept=button('确认采纳',async()=>{
            if(!preview){say('请先预览拟采纳内容');return;}
            if(preview.comparison.kind==='slower'&&!slower.checked){say('请逐条勾选确认较慢成绩');return;}
            if(!await ask('采纳以下内容，仅保存审核决定，尚不写入正式库：\n'+summary(preview.candidate)))return;
            await request('POST',`/admin/submissions/${item.id}/review`,{revision:item.revision,action:'accept',entry:preview.candidate,basis:preview.basis,reason:reason.value,slower_confirmed:slower.checked,review_score:score.value===''?null:Number(score.value)});
            await refreshItem(item.id);say('已采纳，等待后续应用到正式数据。');
        });accept.disabled=true;
        form.node.addEventListener('input',()=>{preview=null;accept.disabled=true;slower.checked=false;unsaved=true;result.textContent='拟采纳内容已变化，请重新预览。';});
        reason.addEventListener('input',()=>{unsaved=true;});score.addEventListener('change',()=>{unsaved=true;});
        const buttons=el('div',undefined,'actions');buttons.append(button('预览拟采纳内容',async()=>{
            preview=await request('POST',`/admin/submissions/${item.id}/preview`,{revision:item.revision,entry:form.read()});
            result.textContent=summary(preview.candidate)+'\n\n'+compareText(preview.comparison);slowerLabel.hidden=preview.comparison.kind!=='slower';slower.checked=false;
            accept.disabled=preview.comparison.kind==='rule_needed';
            say('预览已更新。修改后采纳或更慢成绩需要审核原因。');
        }),accept,button('要求补充',async()=>decision('needs_info')),button('忽略本条',async()=>decision('ignore')));root.append(buttons);
        async function decision(action){if(!reason.value.trim()){say('请填写给玩家的反馈原因，再选择要求补充或忽略。',reason);return;}if(!await ask(action==='ignore'?'忽略此投稿，不修改正式成绩；历史会保留。':'要求玩家补充资料后重新提交？'))return;
            await request('POST',`/admin/submissions/${item.id}/review`,{revision:item.revision,action,reason:reason.value,review_score:score.value===''?null:Number(score.value)});await refreshItem(item.id);say(action==='ignore'?'已忽略并保存原因':'已要求补充');}
    }
    async function init(){
        const session=await request('GET','/auth/me');user=session.user;csrf=session.csrf;
        if(!user){const text='请先返回选车助手注册或登录，再进入投稿页。';$('identity').textContent=text;say(text);return;}
        $('identity').textContent=`${user.email} · ${user.role==='superadmin'?'超级管理员':user.role==='admin'?'管理员':'玩家'}`;
        catalog=await request('GET','/submissions/catalog');$('reference').textContent=catalog.reference_label+' · '+catalog.basis.data.slice(0,12);
        $('navigation').hidden=false;$('reviewTab').hidden=!['admin','superadmin'].includes(user.role);
        $('newTab').onclick=()=>run(()=>switchView('new'));$('mineTab').onclick=()=>run(()=>switchView('mine'));$('reviewTab').onclick=()=>run(()=>switchView('review'));
        $('addRow').onclick=newRow;
        $('saveBatch').onclick=()=>run(async()=>{
            const entries=[...$('draftRows').children].map(n=>n.readEntry());if(!entries.length){say('请先添加至少一条');return;}
            const text=JSON.stringify(entries);if(!batchRequest||batchRequest.text!==text)batchRequest={text,key:crypto.randomUUID().replaceAll('-','')};
            const saved=await request('POST','/submissions',{entries,request_key:batchRequest.key});unsaved=false;$('draftRows').replaceChildren();batchRequest=null;
            await switchView('mine');await loadDetail(saved.ids[0]);say(`已保存 ${saved.ids.length} 条草稿。可逐条补图片或视频来源，预览后提交审核。`);
        });
        for(const id of ['searchBtn','refresh'])$(id).onclick=()=>run(async()=>{if(unsaved&&!await ask('刷新会丢弃未保存的编辑，继续？'))return;unsaved=false;offset=0;await loadList();if(selected)await loadDetail(selected.id);});
        $('statusFilter').onchange=()=>run(async()=>{offset=0;await loadList();});
        $('previous').onclick=()=>run(async()=>{offset=Math.max(0,offset-50);await loadList();});$('next').onclick=()=>run(async()=>{offset+=50;await loadList();});
        addEventListener('beforeunload',e=>{if(unsaved){e.preventDefault();e.returnValue='';}});
        await switchView(location.hash==='#review'&&['admin','superadmin'].includes(user.role)?'review':'mine');
    }
    void init().catch(e=>say(e.message));
})();
