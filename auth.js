/* Loaded only by the local account server; the static deployment does not include this script. */
(function(root) {
    let csrf = '', owner = null, store = null, applyProfile = null, known = null, busy = false;
    let box, message, accountLabel, statusLabel, authDialog;
    let authMode='login', mailToken='', mailMode='file', pendingMailLink=null, sentAction='resend';
    const $ = id => document.getElementById(id);
    const labels = {loading:'正在读取账号资料',saved:'已保存',unsaved:'有未保存修改',saving:'正在保存',conflict:'资料冲突',expired:'登录已失效，草稿已保留',error:'保存失败'};
    async function request(method,path,body) {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), path.startsWith('/auth/') ? 60000 : 10000);
        try {
            const response = await fetch('/api' + path, {
                method, credentials:'same-origin', signal:controller.signal,
                headers:{'Content-Type':'application/json','X-CSRF-Token':csrf, ...(owner ? {'X-Account-ID':owner.id} : {})},
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
        else message.textContent=text;
    }
    function clearPasswords() {
        $('accountPassword').value='';$('accountPasswordConfirm').value='';
    }
    function focusAuth() {
        if(!authDialog.open)return;
        const input=authDialog.querySelector('input:not(:disabled)');
        (input||($('accountAuthForm').hidden?$('accountAuthContinue'):$('accountAuthSubmit'))).focus();
    }
    function showAuth(mode,options={}) {
        authMode=mode;mailToken=options.token||'';clearPasswords();
        if(mode==='sent')sentAction=options.sentAction||'resend';
        $('accountAuthMessage').textContent=options.message||'';
        const titles={login:'登录账号',register:'创建账号',forgot:'找回密码',resend:'重发验证邮件',verify:'验证邮箱',reset:'设置新密码',sent:'请检查邮箱',verified:'邮箱验证完成',resetDone:'密码已重置'};
        $('accountAuthTitle').textContent=mode==='sent'?(sentAction==='forgot'?'请检查重置邮件':'请检查验证邮件'):titles[mode];
        const email=['login','register','forgot','resend'].includes(mode);
        const password=['login','register','reset'].includes(mode);
        const confirmation=['register','reset'].includes(mode);
        for(const [id,visible] of [['accountEmail',email],['accountPassword',password],['accountPasswordConfirm',confirmation]]) {
            const input=$(id);input.parentElement.hidden=!visible;input.disabled=!visible;input.required=visible;
        }
        $('accountPasswordLabel').textContent=mode==='reset'?'新密码':'密码';
        $('accountPassword').autocomplete=mode==='login'?'current-password':'new-password';
        const buttons={login:'登录',register:'注册并发送验证邮件',forgot:'发送重置邮件',resend:'重新发送验证邮件',verify:'确认验证邮箱',reset:'确认重置密码'};
        $('accountAuthForm').hidden=!buttons[mode];
        $('accountAuthSubmit').textContent=buttons[mode]||'确认';
        $('accountAuthContinue').hidden=!!buttons[mode];
        $('accountAuthContinue').textContent=mode==='resetDone'?'重新登录':'返回登录';
        $('accountAuthLinks').hidden=!['login','register','forgot','resend','sent'].includes(mode);
        $('accountSwitchRegister').hidden=mode!=='login';
        $('accountSwitchLogin').hidden=['login','sent'].includes(mode);
        $('accountForgot').hidden=mode!=='login';
        $('accountResend').hidden=!['login','sent'].includes(mode);
        $('accountResend').textContent=mode==='sent'&&sentAction==='forgot'?'重发重置邮件':'重发验证邮件';
        $('accountAuthHelp').textContent=mode==='verify'?'点击确认完成邮箱验证。打开邮件链接本身不会完成验证。':mode==='reset'?'请输入两次新密码。重置成功后，原有登录会话将失效。':mode==='login'?'登录后可同步车库和星级，提交成绩并查看审核反馈。':mode==='register'?'使用邮箱创建账号。密码为12–128字符，请勿使用邮箱本身的密码。':mode==='forgot'?'输入注册邮箱，我们会发送一次性密码重置链接。':mode==='resend'?'输入尚未验证的注册邮箱；新链接生成后，旧链接失效。':'';
        $('accountMailHelp').hidden=mode==='login'||mode==='verified'||mode==='resetDone';
        $('accountMailHelp').textContent=mailMode==='smtp'?'真实邮件测试：仅向启动时指定的邮箱发送。请在运行服务的这台电脑打开邮件链接，30分钟内有效。':'本地模拟模式：邮件在 .local-accounts/outbox，打开最新邮件文件中的链接。';
        if(!authDialog.open)authDialog.showModal();
        if(!busy)focusAuth();
    }
    function status(state) {
        statusLabel.textContent = (labels[state.status] || state.status) + (state.error ? '：' + state.error : '');
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
        known = options.known; applyProfile = options.apply;
        box = document.createElement('section'); box.className='account-panel';
        box.setAttribute('aria-label','账号');
        box.innerHTML=`<div class="account-heading"><strong id="accountLabel">账号</strong><span id="accountStatus" role="status"></span>
          <div id="accountGuestActions" class="account-guest-actions" hidden><button type="button" id="accountOpenLogin" class="account-primary">登录</button><button type="button" id="accountOpenRegister">注册</button></div></div>
        <p id="accountMessage" role="status"></p>
        <div id="accountActions" hidden>
          <button type="button" id="accountImport">导入本机游客车库</button><button type="button" id="accountRetry">重试保存</button>
          <button type="button" id="accountReload" hidden>加载账号资料</button><button type="button" id="accountOverwrite" hidden>用本窗口资料覆盖</button>
          <button type="button" id="accountLogout">退出账号</button>
        </div>`;
        document.querySelector('.card').insertBefore(box, document.querySelector('.sub').nextSibling);
        authDialog=document.createElement('dialog');authDialog.className='account-dialog';authDialog.id='accountAuthDialog';
        authDialog.setAttribute('aria-labelledby','accountAuthTitle');authDialog.setAttribute('aria-describedby','accountAuthHelp');
        authDialog.innerHTML=`<div class="account-dialog-heading"><h2 id="accountAuthTitle">登录账号</h2><button id="accountAuthClose" type="button" aria-label="关闭账号弹窗">×</button></div>
          <p id="accountAuthHelp"></p><p id="accountAuthMessage" role="alert" aria-live="polite"></p>
          <form id="accountAuthForm"><fieldset id="accountAuthFields">
            <label>邮箱<input id="accountEmail" type="email" autocomplete="username" maxlength="254" required></label>
            <label><span id="accountPasswordLabel">密码</span><input id="accountPassword" type="password" autocomplete="current-password" minlength="12" maxlength="128" required></label>
            <label>确认密码<input id="accountPasswordConfirm" type="password" autocomplete="new-password" minlength="12" maxlength="128"></label>
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
        const session = await request('GET','/auth/me'); csrf=session.csrf; owner=session.user;mailMode=session.mail_mode||'file';
        if (owner) {
            store=ProfileStore.create({request,storage:sessionStorage,userId:owner.id,notify:status});
            await store.init();
            if (current()) validate(current());
        }
        accountLabel.textContent=owner ? owner.email : '游客 · 资料保存在本机';
        $('accountGuestActions').hidden=!!owner; $('accountActions').hidden=!owner;
        if(owner) {
            const link=document.createElement('a'); link.href='/submissions'; link.className='account-link'; link.textContent='提交成绩 / 我的投稿';
            $('accountActions').append(link);
            if(owner.role==='admin') {
                const review=document.createElement('a'); review.href='/submissions#review'; review.className='account-link'; review.textContent='审核工作台';
                $('accountActions').append(review);
            }
        }
        $('accountOpenLogin').onclick=()=>showAuth('login');
        $('accountOpenRegister').onclick=()=>showAuth('register');
        $('accountSwitchRegister').onclick=()=>showAuth('register');
        $('accountSwitchLogin').onclick=()=>showAuth('login');
        $('accountForgot').onclick=()=>showAuth('forgot');
        $('accountResend').onclick=()=>showAuth(authMode==='sent'&&sentAction==='forgot'?'forgot':'resend');
        $('accountAuthContinue').onclick=()=>{if(authMode==='resetDone')location.reload();else showAuth('login');};
        $('accountAuthForm').onsubmit=e=>{
            e.preventDefault();
            if(busy||!$('accountAuthForm').reportValidity())return;
            const mode=authMode,token=mailToken;
            const email=$('accountEmail').value,password=$('accountPassword').value;
            if(['register','reset'].includes(mode)&&password!==$('accountPasswordConfirm').value){
                report('两次输入的密码不一致，请重新确认。');$('accountPasswordConfirm').focus();return;
            }
            void action(async()=>{
                if(mode==='login'){
                    if(store)await store.flush();
                    await request('POST','/auth/login',{email,password});clearPasswords();location.reload();
                }else if(mode==='register'){
                    const result=await request('POST','/auth/register',{email,password});showAuth('sent',{message:result.message,sentAction:mode});
                }else if(mode==='forgot'||mode==='resend'){
                    const result=await request('POST',mode==='forgot'?'/auth/forgot-password':'/auth/resend-verification',{email});
                    showAuth('sent',{message:result.message,sentAction:mode});
                }else if(mode==='verify'){
                    const result=await request('POST','/auth/verify-email',{token});showAuth('verified',{message:result.message});
                }else if(mode==='reset'){
                    const result=await request('POST','/auth/reset-password',{token,password});
                    if(store)await store.freeze();showAuth('resetDone',{message:result.message});
                }
            });
        };
        $('accountRetry').onclick=()=>action(()=>store.flush());
        $('accountReload').onclick=()=>action(async()=>{
            if (!await ask('放弃本窗口未保存的账号修改，加载服务器中的资料？游客车库不会被删除。')) return;
            await store.useRemote(); applyProfile(current() || {cars:[],stars:{}}); report('已加载账号资料');
        });
        $('accountOverwrite').onclick=()=>action(async()=>{
            if (!await ask('用本窗口车库和星级替换账号中最新保存的数据？')) return;
            await store.overwrite(); report('已保存本窗口资料');
        });
        $('accountImport').onclick=()=>action(async()=>{
            const cars=localStorage.getItem(APP_CONFIG.storageKeys.garage);
            if (cars===null) throw new Error('此浏览器来源没有游客车库；线上域名的本地数据不会自动出现在这里');
            const profile=validate({cars:JSON.parse(cars),stars:JSON.parse(localStorage.getItem(APP_CONFIG.storageKeys.starMap)||'{}')});
            if (!await ask(`用本机游客车库（${profile.cars.length}辆车、${Object.keys(profile.stars).length}项星级）替换当前账号资料？原游客数据会保留。`)) return;
            store.update(profile); applyProfile(profile); await store.flush(); report('导入并保存成功');
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
        openMailLink();
        addEventListener('hashchange',openMailLink);
        addEventListener('beforeunload',e=>{if(store?.state().dirty){e.preventDefault();e.returnValue='';}});
    }
    root.accountUI = {
        init, active:()=>!!store,
        garage:()=>{const p=current(); return p===null?null:appState.garage(p.cars,known);},
        stars:()=>current()?.stars || {},
        saveGarage:cars=>store.update({...current() || {stars:{}},cars:[...cars]}),
        saveStars:stars=>store.update({...current() || {cars:[]},stars})
    };
})(globalThis);
