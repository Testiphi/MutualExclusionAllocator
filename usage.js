/* No input values, generic clicks, resource requests or unread polls are uploaded. */
(function(root) {
    'use strict';
    if (!root.RACEPICK_USAGE_ENABLED) return;
    const page = {'/':'home','/submissions':'submissions','/feedback':'feedback','/leaderboard':'leaderboard'}[location.pathname];
    if (!page) return; // Administration/statistics pages never collect their own use.
    const server = page==='home' && new URLSearchParams(location.search).get('server')==='global' ? 'global' : 'cn';
    const uuid = () => crypto.randomUUID().replaceAll('-','');
    let visitor, context, token='', identity='', issued=0, boot=null, sending=false, retry=null, featureFlush=null;
    let lastMinute=-1, lastResume=Date.now(), lastGesture=0, opened=false;
    const queue=[];
    const get=(storage,key)=>{try{return storage.getItem(key);}catch{return null;}};
    const put=(storage,key,value)=>{try{storage.setItem(key,value);}catch{/* Keep an ephemeral identity if storage is unavailable. */}};
    try { visitor=get(localStorage,'racepick.usage.visitor.v1'); } catch {}
    if (!/^[a-f0-9]{32}$/.test(visitor||'')) {
        visitor=uuid();try{put(localStorage,'racepick.usage.visitor.v1',visitor);}catch{}
    }
    function session() {
        const now=Date.now();
        if(!context)try{context=JSON.parse(get(sessionStorage,'racepick.usage.session.v1'));}catch{}
        if(!context || !/^[a-f0-9]{32}$/.test(context.id||'') || !Number.isFinite(context.last) || now-context.last>1800000 || context.last>now+60000) {
            context={id:uuid(),last:now};token='';lastMinute=-1;
        }
        context.last=now;try{put(sessionStorage,'racepick.usage.session.v1',JSON.stringify(context));}catch{}
        return context.id;
    }
    async function post(path, body, headers={}) {
        const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),4000);
        try {
            const r=await fetch('/api/usage/'+path,{method:'POST',credentials:'same-origin',signal:controller.signal,
                headers:{'Content-Type':'application/json',...headers},body:JSON.stringify(body)});
            if(!r.ok){const e=new Error('Usage unavailable');e.status=r.status;throw e;}
            return await r.json();
        } finally {clearTimeout(timer);}
    }
    async function prepare() {
        if(token && Date.now()-issued<1500000)return;
        if(!boot)boot=post('session',{visitor_id:visitor,session_id:session()}).then(data=>{
            if(identity && identity!==data.identity)lastMinute=-1;
            identity=data.identity;token=data.token;issued=Date.now();
        }).finally(()=>{boot=null;});
        await boot;
    }
    function enqueue(kind, fields={}) {
        session();queue.push({id:uuid(),kind,page,server,...fields,_queued:Date.now()});
        while(queue.length>20)queue.shift();
        if(kind==='feature'){
            if(!featureFlush)featureFlush=setTimeout(()=>{featureFlush=null;void flush();},1000);
        }else void flush();
    }
    async function flush() {
        if(sending || !queue.length)return;
        sending=true;
        const batch=queue.splice(0,20).filter(e=>Date.now()-e._queued<30000);
        try {
            if(!batch.length)return;
            await prepare();
            await post('events',{events:batch.map(({_queued,...e})=>e)},{'X-Usage-Token':token});
        } catch(error) {
            if(error.status===409){token='';issued=0;}
            if(![400,401,403,422].includes(error.status)) {
                queue.unshift(...batch.filter(e=>Date.now()-e._queued<25000));
                queue.splice(20);
                if(!retry)retry=setTimeout(()=>{retry=null;void flush();},5000);
            }
        } finally {
            sending=false;
            if(queue.length && !retry && !featureFlush)void flush();
        }
    }
    function interaction(event) {
        if(document.hidden || !event.isTrusted)return;
        lastGesture=Date.now();session();
        const minute=Math.floor(Date.now()/60000);
        if(minute!==lastMinute){lastMinute=minute;enqueue('active');}
    }
    function feature(name, result) {
        if(document.hidden || Date.now()-lastGesture>30000)return;
        if(!['generate','garage_save_account','garage_save_local','server_switch'].includes(name) || !['success','empty','failed'].includes(result))return;
        enqueue('feature',{feature:name,result});
    }
    function visibility() {
        if(document.hidden || !opened)return;
        if(Date.now()-lastResume>=30000){lastResume=Date.now();enqueue('visit',{reason:'resume'});}
        void flush();
    }
    function switchIntent(event) {
        if(!event.isTrusted || event.defaultPrevented || document.hidden)return;
        const link=event.target.closest?.('a');
        if(!link || !['serverCnLink','serverGlobalLink'].includes(link.id))return;
        const target=link.id==='serverGlobalLink'?'global':'cn';
        if(target===server)return;
        try{put(sessionStorage,'racepick.usage.switch.v1',JSON.stringify({target,at:Date.now()}));}catch{}
    }
    function start() {
        for(const name of ['pointerdown','click','keydown','input','wheel','touchstart']) document.addEventListener(name,interaction,{capture:true,passive:true});
        document.addEventListener('click',switchIntent);
        document.addEventListener('visibilitychange',visibility);
        root.addEventListener('online',flush);
        if(!document.hidden){opened=true;enqueue('visit',{reason:'open'});}
        else {
            const open=()=>{if(!document.hidden){document.removeEventListener('visibilitychange',open);opened=true;lastResume=Date.now();enqueue('visit',{reason:'open'});}};
            document.addEventListener('visibilitychange',open);
        }
        try{
            const pending=JSON.parse(get(sessionStorage,'racepick.usage.switch.v1'));
            if(pending?.target===server && Date.now()-pending.at<30000){
                sessionStorage.removeItem('racepick.usage.switch.v1');
                // Arrival confirms the navigation. It is not a fresh interaction minute.
                enqueue('feature',{feature:'server_switch',result:'success'});
            }
        }catch{}
    }
    root.Usage={feature,headers:()=>token?{'X-Usage-Token':token}:{}};
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})(globalThis);
