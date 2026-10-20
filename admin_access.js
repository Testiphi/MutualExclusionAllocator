'use strict';
(()=>{
    const $=id=>document.getElementById(id);
    let user,csrf,busy=false;
    const labels={open:'待使用',reserved:'已注册，待验证邮箱',used:'已激活',revoked:'已撤销',expired:'已过期'};
    function node(tag,text){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;}
    function notice(text){$('accessNoticeText').textContent=text;if(!$('accessNotice').open)$('accessNotice').showModal();$('accessNoticeClose').focus();}
    $('accessNoticeClose').onclick=()=>$('accessNotice').close();
    $('inviteCodeClose').onclick=()=>$('inviteCodeDialog').close();
    $('inviteCodeDialog').addEventListener('close',()=>{$('inviteCode').value='';$('inviteCopyStatus').textContent='';});
    $('inviteCopy').onclick=async()=>{try{await navigator.clipboard.writeText($('inviteCode').value);$('inviteCopyStatus').textContent='已复制';}catch{$('inviteCode').focus();$('inviteCode').select();$('inviteCopyStatus').textContent='请按Ctrl+C复制';}};
    async function request(method,path,body){
        const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);
        try{
            const response=await fetch('/api'+path,{method,credentials:'same-origin',signal:controller.signal,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf||'',...(user?{'X-Account-ID':user.id}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
            const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'请检查输入的邮箱、有效期或原因');return data;
        }catch(e){if(e.name==='AbortError')throw new Error('请求超时，操作可能已经完成。请先刷新列表核对；邀请码丢失时撤销该邀请再生成。');throw e;}finally{clearTimeout(timer);}
    }
    async function action(fn){if(busy)return;busy=true;$('accessMain').inert=true;try{await fn();}catch(e){notice(e.message);}finally{busy=false;$('accessMain').inert=false;}}
    function button(text,fn){const b=node('button',text);b.type='button';b.onclick=()=>action(fn);return b;}
    function confirm(text,reason=false){return new Promise(resolve=>{
        $('accessConfirmText').textContent=text;$('revokeReasonLabel').hidden=!reason;$('revokeReason').value='';$('accessConfirmError').textContent='';
        const finish=value=>{$('accessConfirm').close();resolve(value);};
        $('accessCancel').onclick=()=>finish(null);$('accessConfirm').oncancel=e=>{e.preventDefault();finish(null);};
        $('accessConfirmYes').onclick=()=>{const value=$('revokeReason').value.trim();if(reason&&!value){$('accessConfirmError').textContent='请填写原因';$('revokeReason').focus();return;}finish(value||true);};
        $('accessConfirm').showModal();$('accessCancel').focus();
    });}
    async function refresh(){
        const invites=await request('GET','/admin/invitations');const members=await request('GET','/admin/members');
        $('inviteList').replaceChildren();$('memberList').replaceChildren();
        for(const item of invites.items){const row=node('div');row.className='summary';row.append(node('strong',item.email),node('p',`${labels[item.status]} · 到期 ${new Date(item.expires_at*1000).toLocaleString()}`));
            if(['open','reserved'].includes(item.status))row.append(button('撤销邀请',async()=>{if(!await confirm('撤销 '+item.email+' 的邀请？已注册但尚未验证的账号将不会获得管理员权限。'))return;await request('POST',`/admin/invitations/${item.id}/revoke`,{revision:item.revision});await refresh();notice('邀请已撤销');}));$('inviteList').append(row);}
        if(!invites.items.length)$('inviteList').append(node('p','暂无邀请'));
        for(const item of members.items){const row=node('div');row.className='summary';row.append(node('strong',item.email),node('p',item.role==='superadmin'?'超级管理员 · 主号保护':'管理员'));
            if(item.role!=='superadmin')row.append(button('收回管理员权限',async()=>{const reason=await confirm('收回 '+item.email+' 的管理员权限并注销其登录？车库和投稿会保留。',true);if(reason===null)return;await request('POST',`/admin/members/${item.id}/revoke`,{reason});await refresh();notice('权限已收回，旧会话已注销');}));$('memberList').append(row);}
    }
    $('inviteForm').onsubmit=e=>{e.preventDefault();if(!$('inviteForm').reportValidity())return;void action(async()=>{
        const result=await request('POST','/admin/invitations',{email:$('inviteEmail').value,expires_hours:Number($('inviteHours').value)});
        // Display the once-only code before refreshing lists, so a list error cannot lose it.
        $('inviteCodeInfo').textContent=`绑定邮箱：${result.email}；到期：${new Date(result.expires_at*1000).toLocaleString()}`;
        $('inviteCode').value=result.code;$('inviteCopyStatus').textContent='';$('inviteCodeDialog').showModal();$('inviteCode').focus();$('inviteCode').select();
        await refresh();
    });};
    $('accessRefresh').onclick=()=>action(refresh);
    async function init(){const session=await request('GET','/auth/me');user=session.user;csrf=session.csrf;
        if(!user){$('accessIdentity').textContent='请返回首页登录超级管理员账号';notice('请先登录超级管理员账号');return;}
        $('accessIdentity').textContent=user.email+' · '+(user.role==='superadmin'?'超级管理员':'无管理邀请码权限');
        if(user.role!=='superadmin'){notice('该页面仅超级管理员可用');return;}$('accessMain').hidden=false;await refresh();
    }
    void init().catch(e=>notice(e.message));
})();
