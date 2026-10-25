'use strict';
(() => {
    const $=id=>document.getElementById(id),labels={pending:'待处理',processing:'处理中',needs_info:'待补充',resolved:'已解决',closed:'已关闭'},categories={bug:'功能异常',data:'数据问题',suggestion:'使用建议',other:'其他'};
    const admin=location.pathname==='/admin-feedback';
    let unread=null;
    let user,csrf,selected=null,offset=0,busy=false,dirty=false,createAttempt=null,replyAttempt=null,detailTicket=0;
    const prefix=admin?'/admin/feedback':'/feedback';
    const node=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
    const stamp=t=>new Date(t*1000).toLocaleString();
    const key=()=>crypto.randomUUID().replaceAll('-','');
    function say(text){$('message').textContent=text;}
    async function request(method,path,body){
        const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
        try{const response=await fetch('/api'+path,{method,credentials:'same-origin',signal:controller.signal,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf||'',...(globalThis.Usage?.headers()||{}),...(user?{'X-Account-ID':user.id}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});const data=await response.json();if(!response.ok){const e=new Error(typeof data.detail==='string'?data.detail:'请检查必填内容和字数限制');e.status=response.status;throw e;}return data;}finally{clearTimeout(timeout);}
    }
    async function run(fn){if(busy)return;busy=true;$('main').inert=true;try{say('');await fn();}catch(e){say(e.name==='AbortError'?'请求超时，可保持内容重试；重复提交不会新建多份反馈。':e.message);if([401,403].includes(e.status)){$('detail').replaceChildren(node('p','会话或权限已变化，请返回主页重新登录。'));$('list').replaceChildren();$('compose').hidden=true;}}finally{busy=false;$('main').inert=false;}}
    function canLeave(){return !dirty||confirm('有未提交的内容，切换会丢弃这些修改，是否继续？');}
    async function listing(){
        const data=await request('GET',prefix+'?'+new URLSearchParams({status:$('status').value,q:$('search').value,offset:String(offset)}));$('list').replaceChildren();$('count').textContent=`共 ${data.total} 条 · 第 ${Math.floor(offset/30)+1} 页`;$('previous').disabled=!offset;$('next').disabled=offset+30>=data.total;
        if(!data.items.length)$('list').append(node('p','暂无符合条件的反馈','feedback-empty'));
        for(const item of data.items){const b=node('button');b.type='button';b.append(node('strong',item.title),node('span',`${categories[item.category]} · ${labels[item.status]}`,'feedback-meta'),node('small',stamp(item.updated_at)));b.dataset.ticketId=item.id;if(unread){unread.track(b,admin?'feedback_admin':'feedback',item.id);Unread.dot(b,item.unread===true);}b.setAttribute('aria-current',String(item.id===selected?.id));b.onclick=()=>run(async()=>{if(!canLeave())return;dirty=false;await load(item.id);});$('list').append(b);}
    }
    async function load(id){const ticket=++detailTicket,item=await request('GET',prefix+'/'+id);if(ticket!==detailTicket)return;selected=item;replyAttempt=null;for(const b of $('list').querySelectorAll('[data-ticket-id]'))b.setAttribute('aria-current',String(b.dataset.ticketId===id));render(item);if(unread)await unread.read(item,admin?'feedback_admin':'feedback');}
    function render(item){
        const root=$('detail');root.replaceChildren(node('h2',item.title),node('span',labels[item.status],'feedback-badge'),node('p',`编号 ${item.id} · ${categories[item.category]} · ${stamp(item.created_at)}`,'feedback-meta'));
        if(admin)root.append(node('p',`${item.owner_nickname||'未设置昵称'} · ${item.owner_email}`));
        for(const [label,value] of [['问题描述',item.description],['复现步骤',item.steps],['预期结果',item.expected],['实际结果',item.actual]])if(value)root.append(node('h3',label),node('p',value,'feedback-text'));
        root.append(node('p',`来源页面：${item.source_page} · 应用版本：${item.app_version}`,'feedback-meta'),node('h3','处理与补充记录'));
        for(const event of item.events){const block=node('div',undefined,'feedback-event');block.append(node('small',`${stamp(event.created_at)} · ${event.actor_role==='superadmin'?'站长':'提交人'} · ${event.from_status?labels[event.from_status]+' → ':''}${labels[event.to_status]}`));if(event.message)block.append(node('p',event.message,'feedback-text'));root.append(block);}
        if(!admin&&item.status==='closed'){root.append(node('p','此反馈已关闭。如有新情况，请新建反馈并引用上方编号。'));return;}
        const form=node('form'),label=node('label',admin?'回复 / 处理说明（用户可见）':'补充说明'),textarea=node('textarea');textarea.required=true;textarea.maxLength=4000;label.append(textarea);form.append(label);
        let state;
        if(admin){const l=node('label','处理状态');state=node('select');for(const [value,text] of Object.entries(labels)){const o=node('option',text);o.value=value;state.append(o);}state.value=item.status;l.append(state);form.append(l);}else if(['needs_info','resolved'].includes(item.status))form.append(node('p','补充后会重新进入待处理。','muted'));
        const submit=node('button',admin?'保存处理结果':'发送补充');submit.type='submit';submit.id='saveReply';form.append(submit);form.addEventListener('input',()=>{dirty=true;});
        form.onsubmit=e=>{e.preventDefault();if(!form.reportValidity())return;run(async()=>{const body={revision:item.revision,message:textarea.value,...(admin?{status:state.value}:{})};const serialized=JSON.stringify(body);if(!replyAttempt||replyAttempt.body!==serialized)replyAttempt={body:serialized,key:key()};await request('POST',prefix+'/'+item.id+(admin?'/handle':'/reply'),{...body,request_key:replyAttempt.key});dirty=false;await load(item.id);await listing();say('处理记录已保存');});};root.append(form);
    }
    async function showList(){if(!canLeave())return;dirty=false;$('compose').hidden=true;$('workspace').hidden=false;await listing();}
    $('newTicket').onclick=()=>run(async()=>{if(!canLeave())return;dirty=false;$('createForm').reset();createAttempt=null;$('compose').hidden=false;$('workspace').hidden=true;});$('myTickets').onclick=()=>run(showList);
    $('createForm').addEventListener('input',()=>{dirty=true;});
    $('createForm').onsubmit=e=>{e.preventDefault();if(!$('createForm').reportValidity())return;run(async()=>{const body=Object.fromEntries(['category','title','description','steps','expected','actual'].map(n=>[n,$(n).value]));body.source_page=source;const serialized=JSON.stringify(body);if(!createAttempt||createAttempt.body!==serialized)createAttempt={body:serialized,key:key()};const result=await request('POST','/feedback',{...body,request_key:createAttempt.key});dirty=false;$('createForm').reset();createAttempt=null;$('compose').hidden=true;$('workspace').hidden=false;offset=0;$('status').value='all';$('search').value='';await listing();await load(result.id);say('反馈已提交，可在此查看站长回复');});};
    for(const name of ['query','refresh'])$(name).onclick=()=>run(async()=>{if(!canLeave())return;dirty=false;offset=0;await listing();if(selected)await load(selected.id);});
    $('previous').onclick=()=>run(async()=>{if(!canLeave())return;dirty=false;offset=Math.max(0,offset-30);await listing();});$('next').onclick=()=>run(async()=>{if(!canLeave())return;dirty=false;offset+=30;await listing();});
    addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
    addEventListener('focus',()=>{if(!user)return;void request('GET','/auth/me').then(session=>{if(!user||session.user?.id!==user.id||session.user?.role!==user.role){++detailTicket;$('main').hidden=true;$('navigation').hidden=true;$('list').replaceChildren();$('detail').replaceChildren();$('createForm').reset();dirty=false;selected=null;user=null;$('identity').textContent='账号或权限已变化，请刷新页面重新确认身份。';}}).catch(()=>{});});
    const requested=new URLSearchParams(location.search).get('from')||'/';const source=/^\/(?:[a-z0-9_-]+)?$/.test(requested)&&requested.length<=100?requested:'/';
    run(async()=>{const session=await request('GET','/auth/me');user=session.user;csrf=session.csrf;if(!user){$('identity').textContent='请先返回选车助手登录，再提交或查看反馈。';return;}if(!session.feedback)throw Error('此环境尚未启用问题反馈');if(admin&&user.role!=='superadmin'){$('identity').textContent='仅站长可处理全部反馈。';return;}
        $('identity').textContent=user.email+(admin?' · 站长反馈管理':' · 仅你和站长可查看');$('heading').textContent=admin?'用户反馈':'问题反馈';$('navigation').hidden=admin;$('main').hidden=false;$('adminLink').hidden=admin||user.role!=='superadmin';$('newTicket').hidden=admin;$('myTickets').hidden=admin;const context=await request('GET','/feedback/context');$('context').textContent=`将附带：来源页面 ${source} · 应用版本 ${context.app_version}`;if(session.notifications){unread=Unread.create({request,user});if(!admin)unread.track($('myTickets'),'feedback');unread.track($('adminLink'),'feedback_admin');await unread.refresh();}await listing();});
})();
