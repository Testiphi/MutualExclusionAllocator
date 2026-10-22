'use strict';
(() => {
    const $=id=>document.getElementById(id);
    let user=null,csrf='',period='month',revision=0,ticket=0;
    function node(tag,text){const n=document.createElement(tag);n.textContent=text;return n;}
    function message(text){$('message').textContent=text;}
    async function request(method,path,body){
        const response=await fetch('/api'+path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,...(user?{'X-Account-ID':user.id}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
        const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'输入不符合要求');return data;
    }
    const actions={quality_set:'质量评分',quality_suspended:'重新审核，质量分暂停',adopted:'正式采用 +10',adoption_revoked:'采用奖励撤销'};
    function details(items){
        const root=$('details');root.replaceChildren();if(!items.length)root.append(node('p','暂无已结算贡献。未审核投稿请在“我的投稿”查看。'));
        for(const item of items){
            const d=document.createElement('details'),source=item.sources[0],p=source?JSON.parse(source.payload):{};
            d.append(node('summary',`${p.big||''} / ${p.small||''} · ${p.zone||''}/${p.tier||''} · ${p.car||''} ${p.stars?'★'+p.stars:''} ${p.route||''} — 质量 ${item.quality_points} + 采用 ${item.bonus}`));
            if(item.quality){const q=JSON.parse(item.quality);d.append(node('p',`最近评分：完整性 ${q.completeness}/3，证据 ${q.evidence}/4，参考价值 ${q.value}/3。依据：${q.reason}`));}
            for(const s of item.sources){const a=node('a','查看关联投稿');a.href='/submissions#'+s.id;d.append(a);if(s.status==='accepted'&&!s.publication_state&&!item.bonus)d.append(node('p','待发布奖励 +10（尚未到账）'));}
            for(const event of item.events){const snap=JSON.parse(event.snapshot),line=node('p',`${new Date(event.created_at*1000).toLocaleString()} · ${actions[event.action]||event.action} · 质量 ${snap.quality_points} / 采用 ${snap.bonus}${snap.reason?' · '+snap.reason:''}`);line.className='event';d.append(line);}root.append(d);
        }
    }
    async function refresh(){
        const id=++ticket;message('');const session=await request('GET','/auth/me');if(id!==ticket)return;user=session.user;csrf=session.csrf;
        $('personal').hidden=true;$('details').replaceChildren();$('nickname').value='';$('loginHint').hidden=!!user;
        const board=await request('GET','/contributions/leaderboard?period='+encodeURIComponent(period));if(id!==ticket)return;
        $('period').textContent=board.period==='all'?'累计贡献总榜':board.period+' 月榜';$('month').setAttribute('aria-pressed',String(period==='month'));$('all').setAttribute('aria-pressed',String(period==='all'));
        $('updated').textContent='规则启用：'+new Date(board.enabled_at*1000).toLocaleString()+' · 数据更新：'+new Date(board.as_of*1000).toLocaleString();$('rows').replaceChildren();
        for(const row of board.items){const tr=document.createElement('tr');for(const key of ['rank','nickname','total','quality','adoption','effective_count','adopted_count'])tr.append(node('td',String(row[key])));$('rows').append(tr);}
        if(!board.items.length){const tr=document.createElement('tr'),td=node('td','本期暂无有效贡献');td.colSpan=7;tr.append(td);$('rows').append(tr);}
        if(user){const mine=await request('GET','/contributions/me?period='+encodeURIComponent(period));if(id!==ticket)return;$('personal').hidden=false;revision=mine.preference.revision;$('nickname').value=mine.preference.nickname;$('anonymous').checked=!!mine.preference.anonymous;
            const selected=mine.positions[board.period],all=mine.positions.all;$('position').textContent=`当前榜：${selected?'第'+selected.rank+'名，'+selected.total+'分':'暂无排名'} · 累计 ${all?.total||0} 分`;details(mine.items);}
    }
    async function run(fn){try{await fn();}catch(error){message(error.message);}}
    $('month').onclick=()=>run(async()=>{period='month';await refresh();});$('all').onclick=()=>run(async()=>{period='all';await refresh();});$('history').onclick=()=>run(async()=>{if(!$('historyMonth').value)throw new Error('请选择月份');period=$('historyMonth').value;await refresh();});$('refresh').onclick=()=>run(refresh);
    $('preferences').onsubmit=event=>{event.preventDefault();run(async()=>{await request('PUT','/contributions/preferences',{revision,nickname:$('nickname').value,anonymous:$('anonymous').checked});await refresh();message('昵称与展示设置已保存');});};
    window.addEventListener('focus',()=>run(refresh));run(refresh);
})();
