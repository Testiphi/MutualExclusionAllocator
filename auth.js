/* Loaded only by the local account server; the static deployment does not include this script. */
(function(root) {
    let csrf = '', owner = null, store = null, applyProfile = null, readProfile = null, known = null, busy = false;
    let box, message, accountLabel, statusLabel, authDialog;
    let authMode='login', mailToken='', mailMode='file', pendingMailLink=null, sentAction='resend', invitesEnabled=false;
    const $ = id => document.getElementById(id);
    const labels = {loading:'正在读取账号资料',saved:'已保存',unsaved:'有未保存修改',saving:'正在保存',conflict:'资料冲突',expired:'登录已失效，草稿已保留',error:'保存失败'};
    async function request(method,path,body) {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), path.startsWith('/auth/') ? 60000 : 10000);
        try {
            const response = await fetch('/api' + path, {
                method, credentials:'same-origin', signal:controller.signal,
                headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,...(method==='PUT'&&path==='/me/profile'?{'X-Profile-Save':'explicit'}:{}), ...(owner ? {'X-Account-ID':owner.id} : {})},
                ...(body === undefined ? {} : {body:JSON.stringify(body)})
            });
            const data = await response.json();
            if (!response.ok) {
                const error = new Error(typeof data.detail === 'string' ? data.detail : '输入不符合要求，请检查邮箱和密码（12–128字符）');
                error.status = response.status; throw error;
            }
            return data;
        } catch (e) {
            if (e.name === 'AbortError') throw new Error('请求超时，操作可能仍在处理中。邮件操作请先检查收件箱和发信日志，勿立即重复申请；资料保存请核对版本后重试');
            throw e;
        } finally { clearTimeout(timeout); }
    }
    function report(text) {
        if(authDialog?.open) $('accountAuthMessage').textContent=text;
        else {message.textContent=text;if($('personalMessage'))$('personalMessage').textContent=text;}
    }
    function clearPasswords() {
        $('accountPassword').value='';$('accountPasswordConfirm').value='';$('accountInviteCode').value='';
    }
    function focusAuth() {
        if(!authDialog.open)return;
        const input=authDialog.querySelector('input:not(:disabled)');
        (input||($('accountAuthForm').hidden?$('accountAuthContinue'):$('accountAuthSubmit'))).focus();
    }
    function showAuth(mode,options={}) {
        box?.querySelectorAll('.account-hub[open]').forEach(d=>d.close());
        authMode=mode;mailToken=options.token||'';clearPasswords();
        if(mode==='sent')sentAction=options.sentAction||'resend';
        $('accountAuthMessage').textContent=options.message||'';
        const titles={login:'登录账号',register:'创建账号',forgot:'找回密码',resend:'重发验证邮件',verify:'验证邮箱',reset:'设置新密码',sent:'请检查邮箱',verified:'邮箱验证完成',resetDone:'密码已重置',invite:'兑换管理员邀请码',relogin:'权限已更新'};
        $('accountAuthTitle').textContent=mode==='sent'?(sentAction==='forgot'?'请检查重置邮件':'请检查验证邮件'):titles[mode];
        const email=['login','register','forgot','resend'].includes(mode);
        const password=['login','register','reset'].includes(mode);
        const confirmation=['register','reset'].includes(mode);
        for(const [id,visible] of [['accountEmail',email],['accountPassword',password],['accountPasswordConfirm',confirmation]]) {
            const input=$(id);input.parentElement.hidden=!visible;input.disabled=!visible;input.required=visible;
        }
        $('accountInviteCode').parentElement.hidden=!(invitesEnabled&&['register','invite'].includes(mode));
        $('accountInviteCode').disabled=!(invitesEnabled&&['register','invite'].includes(mode));
        $('accountInviteCode').required=invitesEnabled&&mode==='invite';
        $('accountPasswordLabel').textContent=mode==='reset'?'新密码':'密码';
        $('accountPassword').autocomplete=mode==='login'?'current-password':'new-password';
        const buttons={login:'登录',register:'注册并发送验证邮件',forgot:'发送重置邮件',resend:'重新发送验证邮件',verify:'确认验证邮箱',reset:'确认重置密码',invite:'激活管理员权限'};
        $('accountAuthForm').hidden=!buttons[mode];
        $('accountAuthSubmit').textContent=buttons[mode]||'确认';
        $('accountAuthContinue').hidden=!!buttons[mode];
        $('accountAuthContinue').textContent=['resetDone','relogin'].includes(mode)?'重新登录':'返回登录';
        $('accountAuthLinks').hidden=!['login','register','forgot','resend','sent'].includes(mode);
        $('accountSwitchRegister').hidden=mode!=='login';
        $('accountSwitchLogin').hidden=['login','sent'].includes(mode);
        $('accountForgot').hidden=mode!=='login';
        $('accountResend').hidden=!['login','sent'].includes(mode);
        $('accountResend').textContent=mode==='sent'&&sentAction==='forgot'?'重发重置邮件':'重发验证邮件';
        $('accountAuthHelp').textContent=mode==='verify'?'点击确认完成邮箱验证。打开邮件链接本身不会完成验证。':mode==='reset'?'请输入两次新密码。重置成功后，原有登录会话将失效。':mode==='login'?'登录后可同步车库和星级，提交成绩并查看审核反馈。':mode==='register'?(invitesEnabled?'普通玩家无需邀请码；受邀管理员请填写与本邮箱绑定的邀请码，验证邮箱后生效。密码为12–128字符。':'使用邮箱创建账号，密码为12–128字符。'):mode==='forgot'?'输入注册邮箱，我们会发送一次性密码重置链接。':mode==='resend'?'输入尚未验证的注册邮箱；新链接生成后，旧链接失效。':mode==='invite'?'邀请码必须绑定当前账号邮箱。激活后需重新登录；不能通过邀请码获得超级管理员权限。':'';
        $('accountMailHelp').hidden=['login','verified','resetDone','invite','relogin'].includes(mode);
        $('accountMailHelp').textContent=mailMode==='production'?'验证和重置邮件会发送至你的邮箱，链接30分钟内有效，请同时检查垃圾邮件。':mailMode==='smtp'?'真实邮件测试：仅向启动时指定的邮箱发送。请在运行服务的这台电脑打开邮件链接，30分钟内有效。':'本地模拟模式：邮件在 .local-accounts/outbox，打开最新邮件文件中的链接。';
        if(!authDialog.open)authDialog.showModal();
        if(!busy)focusAuth();
    }
    function status(state) {
        statusLabel.textContent = (labels[state.status] || state.status) + (state.error ? '：' + state.error : '');
        if (globalThis.dispatchEvent) globalThis.dispatchEvent(new Event('garage-save-state'));
        $('accountRetry').disabled=state.status==='saving';
        $('accountReload').hidden = !['conflict','error','expired','unsaved'].includes(state.status);
        $('accountOverwrite').hidden = state.status !== 'conflict';
    }
    function validate(profile) {
        if (!profile || !Array.isArray(profile.cars) || profile.cars.some(c => typeof c !== 'string') || !profile.stars || typeof profile.stars !== 'object' || Array.isArray(profile.stars)) throw new Error('车库或星级数据格式损坏，未导入');
        const stars = {};
        for (const [car,n] of Object.entries(profile.stars)) {
            if (known.has(car)) {
                if (!Number.isInteger(n) || n < 1 || n > 6) throw new Error('星级数据无效，未导入');
                stars[car] = n;
            }
        }
        return {cars:[...new Set(profile.cars.filter(c => known.has(c)))],stars};
    }
    async function saveNow(){if(current()===null)store.update(readProfile());return store.flush();}
    function current() { return store ? store.snapshot() : null; }
    function ask(text) {
        return new Promise(resolve => {
            const dialog=document.createElement('dialog'); dialog.className='account-confirm';
            const description=document.createElement('p'); description.textContent=text;
            const yes=document.createElement('button'); yes.type='button'; yes.textContent='确认继续';
            const no=document.createElement('button'); no.type='button'; no.textContent='取消';
            function finish(value) { dialog.close(); dialog.remove(); resolve(value); }
            yes.onclick=()=>finish(true); no.onclick=()=>finish(false);
            dialog.addEventListener('cancel',e=>{e.preventDefault();finish(false);});
            dialog.append(description,no,yes); document.body.append(dialog); dialog.showModal(); no.focus();
        });
    }
    async function action(fn) {
        if (busy) return;
        busy = true;
        box.querySelectorAll('button').forEach(b => b.disabled=true);
        authDialog.querySelectorAll('button').forEach(b => b.disabled=true);
        $('accountAuthFields').disabled=true;$('accountAuthProgress').hidden=false;
        try { await fn(); } catch(e) { report(e.message); }
        finally {
            busy=false;box.querySelectorAll('button').forEach(b => b.disabled=false);
            authDialog.querySelectorAll('button').forEach(b => b.disabled=false);
            $('accountAuthFields').disabled=false;$('accountAuthProgress').hidden=true;
            if(pendingMailLink){const link=pendingMailLink;pendingMailLink=null;showAuth(link.mode,{token:link.token});}
            else if(authDialog.open)focusAuth();
        }
    }
    async function init(options) {
        known = options.known; applyProfile = options.apply; readProfile=options.read;
        box = document.createElement('section'); box.className='account-panel';
        box.setAttribute('aria-label','账号');
        box.innerHTML=`<div class="account-heading"><strong id="accountLabel">账号</strong><span id="accountStatus" role="status"></span>
          <div id="accountGuestActions" class="account-guest-actions" hidden><button type="button" id="accountOpenLogin" class="account-primary">登录</button><button type="button" id="accountOpenRegister">注册</button></div></div>
        <nav id="accountNavigation" class="account-navigation" aria-label="主要功能"></nav>
        <p id="accountMessage" role="status"></p>
        <div class="account-recovery"><button type="button" id="accountReload" hidden>加载账号资料</button><button type="button" id="accountOverwrite" hidden>用本窗口资料覆盖</button></div>`;
        function hub(id,title,description){
            const dialog=document.createElement('dialog');dialog.id=id;dialog.className='account-dialog account-hub';dialog.setAttribute('aria-labelledby',id+'Title');
            const heading=document.createElement('div');heading.className='account-dialog-heading';const h=document.createElement('h2');h.id=id+'Title';h.textContent=title;
            const close=document.createElement('button');close.type='button';close.textContent='×';close.setAttribute('aria-label','关闭'+title);close.onclick=()=>{if(!busy)dialog.close();};heading.append(h,close);
            const p=document.createElement('p');p.className='account-help';p.textContent=description;
            const items=document.createElement('div');items.className='account-hub-items';dialog.append(heading,p,items);box.append(dialog);
            const trigger=document.createElement('button');trigger.type='button';trigger.textContent=title;trigger.setAttribute('aria-haspopup','dialog');trigger.setAttribute('aria-controls',id);trigger.onclick=()=>dialog.showModal();box.querySelector('#accountNavigation').append(trigger);
            dialog.addEventListener('cancel',e=>{if(busy)e.preventDefault();});dialog.addEventListener('close',()=>trigger.focus());
            return items;
        }
        function hubLink(items,title,href,description){
            const a=document.createElement('a');a.className='account-link account-hub-link';a.href=href;const strong=document.createElement('strong');strong.textContent=title;const small=document.createElement('small');small.textContent=description;a.append(strong,small);items.append(a);
        }
        const personal=hub('personalCenter','个人中心','管理账号与公开身份；车库保存和恢复在主页车库区操作。');
        personal.innerHTML=`<p id="personalIdentity"></p><p id="personalMessage" role="status"></p><div id="accountActions" hidden><button type="button" id="accountImport">导入本机游客车库</button><button type="button" id="accountRetry" hidden>保存车库</button><button type="button" id="accountLogout">退出账号</button></div>`;
        document.querySelector('.card').insertBefore(box, document.querySelector('.sub').nextSibling);
        authDialog=document.createElement('dialog');authDialog.className='account-dialog';authDialog.id='accountAuthDialog';
        authDialog.setAttribute('aria-labelledby','accountAuthTitle');authDialog.setAttribute('aria-describedby','accountAuthHelp');
        authDialog.innerHTML=`<div class="account-dialog-heading"><h2 id="accountAuthTitle">登录账号</h2><button id="accountAuthClose" type="button" aria-label="关闭账号弹窗">×</button></div>
          <p id="accountAuthHelp"></p><p id="accountAuthMessage" role="alert" aria-live="polite"></p>
          <form id="accountAuthForm"><fieldset id="accountAuthFields">
            <label>邮箱<input id="accountEmail" type="email" autocomplete="username" maxlength="254" required></label>
            <label><span id="accountPasswordLabel">密码</span><input id="accountPassword" type="password" autocomplete="current-password" minlength="12" maxlength="128" required></label>
            <label>确认密码<input id="accountPasswordConfirm" type="password" autocomplete="new-password" minlength="12" maxlength="128"></label>
            <label>管理员邀请码（玩家注册可留空）<input id="accountInviteCode" type="text" autocomplete="off" spellcheck="false" maxlength="128"></label>
            <button class="account-primary" type="submit" id="accountAuthSubmit">登录</button>
          </fieldset></form>
          <p id="accountAuthProgress" role="status" hidden>正在处理，请稍候…</p>
          <button id="accountAuthContinue" type="button" hidden>返回登录</button>
          <div id="accountAuthLinks" class="account-dialog-links"><button type="button" id="accountSwitchRegister">还没有账号？注册</button><button type="button" id="accountSwitchLogin">已有账号？登录</button><button type="button" id="accountForgot">忘记密码</button><button type="button" id="accountResend">重发验证邮件</button></div>
          <p class="account-help" id="accountMailHelp"></p>`;
        document.body.append(authDialog);
        $('accountAuthClose').onclick=()=>{if(!busy)authDialog.close();};
        authDialog.addEventListener('cancel',e=>{if(busy)e.preventDefault();});
        authDialog.addEventListener('close',()=>{clearPasswords();mailToken='';});
        message=$('accountMessage'); accountLabel=$('accountLabel'); statusLabel=$('accountStatus');
        const session = await request('GET','/auth/me'); csrf=session.csrf; owner=session.user;mailMode=session.mail_mode||'file';invitesEnabled=session.admin_invites===true;
        if (owner) {
            store=ProfileStore.create({request,storage:sessionStorage,userId:owner.id,notify:status});
            await store.init();
            if (current()) validate(current());
        }
        const roleLabel=owner?.role==='superadmin'?'超级管理员':owner?.role==='admin'?'管理员':'玩家';
        accountLabel.textContent=owner?'已登录 · '+roleLabel:'游客 · 资料保存在本机';
        $('personalIdentity').textContent=owner?owner.email+' · '+roleLabel:'登录后管理昵称、账号与个人贡献。';
        $('accountGuestActions').hidden=!!owner; $('accountActions').hidden=!owner;
        $('accountNavigation').querySelector('[aria-controls="personalCenter"]').hidden=!owner;
        const contributions=hub('contributionCenter','数据贡献',owner?'提交数据、查看审核进度与贡献排名。':'登录后可提交成绩；公开排行榜无需登录。');
        if(owner){
            hubLink(contributions,'提交成绩','/submissions#new','补充成绩、来源和证据');
            hubLink(contributions,'我的投稿','/submissions','查看审核结果，继续补充资料');
        }else{
            const login=document.createElement('button');login.type='button';login.textContent='登录后提交成绩';login.onclick=()=>showAuth('login');contributions.append(login);
        }
        if(session.contributions){
            hubLink(contributions,'贡献排行榜','/leaderboard','查看本月榜与总榜');
            if(owner){
                hubLink(contributions,'我的贡献','/leaderboard#mine','查看得分明细和调整记录');
                hubLink(personal,'公开昵称与匿名设置','/leaderboard#mine','设置排行榜展示身份，不公开邮箱');
                try{const mine=await request('GET','/contributions/me');if(mine.preference.nickname)accountLabel.textContent=mine.preference.nickname+' · '+roleLabel;}catch(e){report('昵称暂时无法读取，可在个人中心重试');}
            }
        }
        if(session.feedback&&owner)hubLink(personal,'问题反馈','/feedback?from=%2F','向站长反馈问题，查看处理进度');
        if(owner&&['admin','superadmin'].includes(owner.role)){
            const management=hub('managementCenter','管理工作台','按权限显示审核、发布与账号管理功能。');
            hubLink(management,'投稿审核','/submissions#review','审核玩家投稿，填写反馈与质量评分');
            if((session.score_versions||session.score_versions_lab)&&owner.role==='superadmin')hubLink(management,session.score_versions_lab?'成绩版本测试台':'正式成绩发布','/score-versions','逐项确认发布、查看批次及回滚');
            if(session.readonly_previews)hubLink(management,'变更清单预览','/data-previews','检查已采纳投稿的变更影响');
            if(owner.role==='superadmin'){
                if(session.feedback){
                    hubLink(management,'用户反馈','/admin-feedback','查看问题反馈并回复用户');
                    try{const summary=await request('GET','/admin/feedback/summary');const link=management.querySelector('a[href="/admin-feedback"] strong');link.textContent='用户反馈'+(summary.pending?'（待处理 '+summary.pending+'）':'');}catch(error){report('反馈待处理数量暂时无法读取，可进入工作台刷新');}
                }
                hubLink(management,'账号与公告管理','/admin-accounts','管理账号状态和公告内容');
                hubLink(management,'管理员与邀请码','/admin-access','查看管理员并管理邀请');
            }
        }else if(owner?.role==='player'&&invitesEnabled){
            const redeem=document.createElement('button');redeem.type='button';redeem.textContent='兑换管理员邀请码';redeem.onclick=()=>showAuth('invite');$('accountActions').append(redeem);
        }
        $('accountOpenLogin').onclick=()=>showAuth('login');
        $('accountOpenRegister').onclick=()=>showAuth('register');
        $('accountSwitchRegister').onclick=()=>showAuth('register');
        $('accountSwitchLogin').onclick=()=>showAuth('login');
        $('accountForgot').onclick=()=>showAuth('forgot');
        $('accountResend').onclick=()=>showAuth(authMode==='sent'&&sentAction==='forgot'?'forgot':'resend');
        $('accountAuthContinue').onclick=()=>{if(['resetDone','relogin'].includes(authMode))location.reload();else showAuth('login');};
        $('accountAuthForm').onsubmit=e=>{
            e.preventDefault();
            if(busy||!$('accountAuthForm').reportValidity())return;
            const mode=authMode,token=mailToken;
            const email=$('accountEmail').value,password=$('accountPassword').value,invite_code=$('accountInviteCode').value.trim();
            if(['register','reset'].includes(mode)&&password!==$('accountPasswordConfirm').value){
                report('两次输入的密码不一致，请重新确认。');$('accountPasswordConfirm').focus();return;
            }
            void action(async()=>{
                if(mode==='login'){
                    if(store?.state().dirty&&!await ask('当前有未保存的车库修改。兑换后需重新登录，草稿保留在本窗口，不会自动保存。继续？'))return;
                    await request('POST','/auth/login',{email,password});clearPasswords();location.reload();
                }else if(mode==='register'){
                    const result=await request('POST','/auth/register',{email,password,...(invitesEnabled&&invite_code?{invite_code}:{})});showAuth('sent',{message:result.message,sentAction:mode});
                }else if(mode==='forgot'||mode==='resend'){
                    const result=await request('POST',mode==='forgot'?'/auth/forgot-password':'/auth/resend-verification',{email});
                    showAuth('sent',{message:result.message,sentAction:mode});
                }else if(mode==='invite'){
                    if(store?.state().dirty&&!await ask('当前有未保存的车库修改。兑换后需重新登录，草稿保留在本窗口，不会自动保存。继续？'))return;
                    const result=await request('POST','/auth/redeem-invitation',{invite_code});
                    if(store)await store.freeze();showAuth('relogin',{message:result.message});
                }else if(mode==='verify'){
                    const result=await request('POST','/auth/verify-email',{token});showAuth('verified',{message:result.message});
                }else if(mode==='reset'){
                    const result=await request('POST','/auth/reset-password',{token,password});
                    if(store)await store.freeze();showAuth('resetDone',{message:result.message});
                }
            });
        };
        $('accountRetry').onclick=()=>action(saveNow);
        $('accountReload').onclick=()=>action(async()=>{
            if (!await ask('放弃本窗口未保存的账号修改，加载服务器中的资料？游客车库不会被删除。')) return;
            await store.useRemote(); applyProfile(current() || {cars:[],stars:{}}); report('已加载账号资料');
        });
        $('accountOverwrite').onclick=()=>action(async()=>{
            if (!await ask('用本窗口车库和星级替换账号中最新保存的数据？')) return;
            await store.overwrite(); report('已保存本窗口资料');
        });
        $('accountImport').onclick=()=>action(async()=>{
            const unified=api.guestProfile?.();
            const cars=unified?JSON.stringify(unified.cars):localStorage.getItem(APP_CONFIG.storageKeys.garage);
            if (cars===null) throw new Error('此浏览器来源没有游客车库；线上域名的本地数据不会自动出现在这里');
            const profile=validate({cars:JSON.parse(cars),stars:unified?.stars||JSON.parse(localStorage.getItem(APP_CONFIG.storageKeys.starMap)||'{}')});
            if (!await ask(`用本机游客车库（${profile.cars.length}辆车、${Object.keys(profile.stars).length}项星级）作为当前临时选择？需要点击保存车库才会更新账号，原游客数据会保留。`)) return;
            store.update(profile); applyProfile(profile); report('已导入为临时选择，尚未保存到账号');
        });
        $('accountLogout').onclick=()=>action(async()=>{
            if (store.state().dirty && !await ask('仍有未保存修改。退出后草稿仅保留在本窗口，重新登录此账号可以恢复。继续退出？')) return;
            await store.freeze();
            try { await request('POST','/auth/logout',{}); location.reload(); }
            catch (error) { store.unfreeze(); throw error; }
        });
        function openMailLink() {
            const fragment=new URLSearchParams(location.hash.slice(1));
            const purpose=fragment.get('action'),token=fragment.get('token');
            if(token&&['verify','reset'].includes(purpose)){
                history.replaceState(null,'',location.pathname);
                if(busy)pendingMailLink={mode:purpose,token};
                else showAuth(purpose,{token});
            }
        }
        if(session.community_controls&&globalThis.AnnouncementUI){try{await AnnouncementUI.init({owner,request});}catch(error){report('更新公告暂时无法读取，其他功能可继续使用');}}
        openMailLink();
        addEventListener('hashchange',openMailLink);
        addEventListener('beforeunload',e=>{
            if(!store?.state().dirty)return;
            if(globalThis.RACEPICK_SERVER_NAVIGATION?.kind==='server-switch'&&owner){
                try{
                    const key='racepick.account-draft.v1.'+owner.id,raw=sessionStorage.getItem(key),draft=JSON.parse(raw);
                    if(Number.isInteger(draft?.revision)&&JSON.stringify(draft.profile)===JSON.stringify(store.snapshot())){
                        sessionStorage.setItem(key,raw);
                        if(sessionStorage.getItem(key)===raw)return;
                    }
                }catch(error){}
                report('账号临时草稿未能缓存，请先保存或加载账号资料后再切换服务器');
            }
            e.preventDefault();e.returnValue='';
        });
    }
    root.accountUI = {
        init, active:()=>!!store,
        garage:()=>{const p=current(); return p===null?null:appState.garage(p.cars,known);},
        stars:()=>current()?.stars || {},
        saveNow, state:()=>store?.state(),
        restore:async()=>{await store.useRemote();applyProfile(current()||{cars:[...known],stars:{}});},
        saveGarage:cars=>store.update({...readProfile(),cars:[...cars]}),
        saveStars:stars=>store.update({...readProfile(),stars})
    };
})(globalThis);
