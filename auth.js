/* Loaded only by the local account server; the static deployment does not include this script. */
(function(root) {
    let csrf = '', owner = null, store = null, applyProfile = null, known = null, busy = false;
    let box, message, accountLabel, statusLabel;
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
    function report(text) { message.textContent = text; }
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
        try { await fn(); } catch(e) { report(e.message); }
        finally { busy=false; box.querySelectorAll('button').forEach(b => b.disabled=false); }
    }
    async function init(options) {
        known = options.known; applyProfile = options.apply;
        box = document.createElement('section'); box.className='account-panel';
        box.setAttribute('aria-label','账号');
        box.innerHTML=`<div class="account-heading"><strong id="accountLabel">账号</strong><span id="accountStatus" role="status"></span></div>
        <p id="accountMessage" role="status"></p>
        <form id="accountForm">
          <label>邮箱 <input id="accountEmail" type="email" autocomplete="username" maxlength="254" required></label>
          <label>密码（12–128字符） <input id="accountPassword" type="password" autocomplete="current-password" minlength="12" maxlength="128" required></label>
          <button type="submit">登录</button><button type="button" id="accountRegister">注册</button><button type="button" id="accountForgot">忘记密码</button><button type="button" id="accountResend">重发验证邮件</button>
          <p class="account-help" id="accountMailHelp">本地测试邮件保存在 .local-accounts/outbox；打开最新邮件文件中的链接完成验证或重置。</p>
        </form>
        <div id="accountActions" hidden>
          <button type="button" id="accountImport">导入本机游客车库</button><button type="button" id="accountRetry">重试保存</button>
          <button type="button" id="accountReload" hidden>加载账号资料</button><button type="button" id="accountOverwrite" hidden>用本窗口资料覆盖</button>
          <button type="button" id="accountLogout">退出账号</button>
        </div>
        <form id="accountTokenForm" hidden><p id="accountTokenHelp"></p>
          <label id="accountNewPasswordLabel">新密码 <input id="accountNewPassword" type="password" autocomplete="new-password" minlength="12" maxlength="128"></label>
          <button type="submit">确认</button>
        </form>`;
        document.querySelector('.card').insertBefore(box, document.querySelector('.sub').nextSibling);
        message=$('accountMessage'); accountLabel=$('accountLabel'); statusLabel=$('accountStatus');
        const session = await request('GET','/auth/me'); csrf=session.csrf; owner=session.user;
        if(session.mail_mode==='smtp') $('accountMailHelp').textContent='真实邮件测试：仅向启动时指定的邮箱发送。请在运行服务的这台电脑打开邮件链接；链接30分钟有效。';
        if (owner) {
            store=ProfileStore.create({request,storage:sessionStorage,userId:owner.id,notify:status});
            await store.init();
            if (current()) validate(current());
        }
        accountLabel.textContent=owner ? owner.email : '游客 · 资料保存在本机';
        $('accountForm').hidden=!!owner; $('accountActions').hidden=!owner;
        if(owner) {
            const link=document.createElement('a'); link.href='/submissions'; link.className='account-link'; link.textContent='提交成绩 / 我的投稿';
            $('accountActions').append(link);
            if(owner.role==='admin') {
                const review=document.createElement('a'); review.href='/submissions#review'; review.className='account-link'; review.textContent='审核工作台';
                $('accountActions').append(review);
            }
        }
        const credentials=()=>({email:$('accountEmail').value,password:$('accountPassword').value});
        $('accountForm').addEventListener('submit',e=>{e.preventDefault(); void action(async()=>{
            await request('POST','/auth/login',credentials()); location.reload();
        });});
        $('accountRegister').onclick=()=>action(async()=>{
            if (!$('accountForm').reportValidity()) return;
            const result=await request('POST','/auth/register',credentials()); $('accountPassword').value=''; report(result.message);
        });
        $('accountForgot').onclick=()=>action(async()=>{
            if (!$('accountEmail').reportValidity()) return;
            report((await request('POST','/auth/forgot-password',{email:$('accountEmail').value})).message);
        });
        $('accountResend').onclick=()=>action(async()=>{
            if (!$('accountEmail').reportValidity()) return;
            report((await request('POST','/auth/resend-verification',{email:$('accountEmail').value})).message);
        });
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
            const purpose=fragment.get('action'), token=fragment.get('token');
            if (token && ['verify','reset'].includes(purpose)) {
                history.replaceState(null,'',location.pathname);
                $('accountTokenForm').hidden=false;
                $('accountTokenHelp').textContent=purpose==='verify'?'确认验证此邮箱':'设置新密码，成功后所有原登录会话会失效';
                $('accountNewPasswordLabel').hidden=purpose==='verify';
                $('accountNewPassword').required=purpose==='reset';
                $('accountTokenForm').onsubmit=e=>{e.preventDefault(); void action(async()=>{
                    const result=await request('POST',purpose==='verify'?'/auth/verify-email':'/auth/reset-password',
                        purpose==='verify'?{token}:{token,password:$('accountNewPassword').value});
                    $('accountTokenForm').hidden=true; $('accountNewPassword').value=''; report(result.message);
                    if (purpose==='reset') { if(store) await store.freeze(); report(result.message+'。请刷新页面。'); }
                });};
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
