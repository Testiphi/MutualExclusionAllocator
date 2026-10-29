'use strict';
(() => {
    const $=id=>document.getElementById(id),el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
    let owner=null,busy=false;
    const names={generate:'生成方案',server_switch:'切换服别',garage_save_account:'保存账号车库',garage_save_local:'保存本机车库',submission_submit:'提交成绩',feedback_submit:'新建问题反馈'};
    const resultNames={success:'成功',empty:'无可用方案 / 未选地图',failed:'失败'};
    function clear(){ $('main').hidden=true;for(const id of ['windows','heatmaps','features','proportions'])$(id).replaceChildren(); }
    async function request(path){
        const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
        try{
            const r=await fetch('/api'+path,{credentials:'same-origin',signal:controller.signal,headers:owner?{'X-Account-ID':owner.id}:{}});
            const data=await r.json();if(!r.ok){const e=new Error(typeof data.detail==='string'?data.detail:'查询失败');e.status=r.status;throw e;}return data;
        }finally{clearTimeout(timer);}
    }
    async function authorize(){
        const session=await request('/auth/me');
        if(!session.user || session.user.role!=='superadmin' || !session.user.verified || !session.usage || (owner && session.user.id!==owner.id)){
            clear();throw Error('仅已登录的超级管理员可查看启用的使用统计；账号变化后请刷新。');
        }
        owner=session.user;$('identity').textContent=owner.email+' · 仅超级管理员可见'+(session.mail_mode==='production'?'':' · 本地环境，非线上用户数据');
    }
    async function run(fn){
        if(busy)return;busy=true;$('main').inert=true;
        try{$('message').textContent='';await authorize();await fn();}
        catch(e){if([401,403].includes(e.status))clear();$('message').textContent=e.name==='AbortError'?'查询超时，可稍后重试':e.message;}
        finally{busy=false;$('main').inert=false;}
    }
    function row(parent,values){const tr=el('tr');for(const value of values)tr.append(el('td',String(value)));parent.append(tr);}
    function empty(parent,columns){const tr=el('tr'),td=el('td','暂无统计记录');td.colSpan=columns;td.className='empty';tr.append(td);parent.append(tr);}
    function render(data){
        $('start').value=data.start;$('end').value=data.end;$('asof').textContent='滚动窗口截至 '+data.rolling_windows_as_of+' · 北京时间';
        $('windows').replaceChildren();
        for(const [kind,label] of [['account','登录账号'],['guest','匿名游客（近似）']]){
            const card=el('div');card.className='metric';card.append(el('strong',label));const p=el('p');
            for(const [key,text] of [['dau','日活'],['wau','周活'],['mau','月活']]){const span=el('span',text+' ');span.append(el('b',data.windows[kind][key]));p.append(span);}card.append(p);$('windows').append(card);
        }
        $('heatmaps').replaceChildren();
        for(const [kind,label] of [['account','登录账号'],['guest','匿名游客（近似）']]){
            $('heatmaps').append(el('h3',label));const wrap=el('div');wrap.className='table-wrap';const table=el('table');table.className='heatmap';table.setAttribute('aria-label',label+'北京时间累计活跃分钟热力图');
            const header=el('tr');header.append(el('th','星期 / 时'));for(let h=0;h<24;h++)header.append(el('th',String(h)));table.append(header);
            const max=Math.max(1,...data.heatmap[kind].flat());
            data.heatmap[kind].forEach((hours,day)=>{const tr=el('tr');tr.append(el('th',['一','二','三','四','五','六','日'][day]));hours.forEach((value,h)=>{const td=el('td',value||'');td.style.backgroundColor=value?`rgba(88,166,255,${.15+.75*value/max})`:'#21262d';td.title=`星期${['一','二','三','四','五','六','日'][day]} ${h}:00–${h}:59：${value} 活跃分钟`;tr.append(td);});table.append(tr);});wrap.append(table);$('heatmaps').append(wrap);
        }
        $('proportions').replaceChildren();const total=data.server_proportions.reduce((sum,r)=>sum+r.opens,0);
        for(const server of ['cn','global']){const r=data.server_proportions.find(r=>r.server===server)||{opens:0,resumes:0,active_minutes:0};row($('proportions'),[server==='cn'?'国服':'国际服',r.opens,total?(100*r.opens/total).toFixed(1)+'%':'—',r.resumes,r.active_minutes]);}
        $('features').replaceChildren();for(const r of data.features)row($('features'),[names[r.feature]||r.feature,resultNames[r.result]||r.result,r.account.uses,r.account.people,r.guest.uses,r.guest.people]);if(!data.features.length)empty($('features'),6);
        $('main').hidden=false;
    }
    async function overview(){render(await request('/admin/usage?'+new URLSearchParams({start:$('start').value,end:$('end').value,server:$('server').value})));}
    $('filters').onsubmit=e=>{e.preventDefault();if($('filters').reportValidity())void run(overview);};
    addEventListener('focus',()=>{if(owner)void run(async()=>{});});
    void run(async()=>{await overview();});
})();
