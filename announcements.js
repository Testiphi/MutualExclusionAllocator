/* Announcement content is plain text. Dismissal preferences are account scoped. */
(function(root){
 const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
 async function init({owner,request}){
  let preferences=null,latest=null,ready=false,opened=false,busy=false,page=0;
  const button=el('button','更新公告');button.type='button';button.className='account-link';document.getElementById(owner?'accountActions':'accountGuestActions').append(button);
  const dialog=el('dialog');dialog.className='account-dialog announcement-dialog';dialog.setAttribute('aria-label','更新公告');
  const title=el('h2'),meta=el('p'),body=el('div'),error=el('p'),actions=el('div');error.setAttribute('role','alert');body.style.whiteSpace='pre-wrap';actions.className='announcement-actions';dialog.append(title,meta,body,error,actions);document.body.append(dialog);
  const sessionKey=id=>'racepick.announcement.closed.'+(owner?.id||'guest')+'.'+id;
  const close=()=>{if(latest)try{sessionStorage.setItem(sessionKey(latest.id),'1');}catch(e){}dialog.close();};
  dialog.addEventListener('cancel',e=>{e.preventDefault();close();});
  function action(text,fn){const b=el('button',text);b.type='button';b.onclick=async()=>{if(busy)return;busy=true;error.textContent='';try{await fn();}catch(e){error.textContent=e.message;}finally{busy=false;}};actions.append(b);return b;}
  async function settings(){if(owner)preferences=await request('GET','/me/announcement-preferences');}
  async function mute(value){await settings();preferences=await request('PUT','/me/announcement-preferences',{muted:value,revision:preferences.revision});await settings();}
  function showItem(item){latest=item;title.textContent=item.title;meta.textContent=[item.release_label,new Date(item.published_at*1000).toLocaleDateString()].filter(Boolean).join(' · ');body.textContent=item.body;error.textContent='';actions.replaceChildren();
   action('关闭',async()=>close());
   if(owner){action('本条不再提醒',async()=>{await request('POST','/me/announcements/'+item.id+'/dismiss',{});close();});action('以后都不自动显示',async()=>{await mute(true);close();});}
   action('查看公告历史与提醒设置',history);if(!dialog.open)dialog.showModal();
  }
  async function history(){await settings();const data=await request('GET','/announcements?offset='+page);title.textContent='更新公告';meta.textContent=owner?(preferences.muted?'自动弹窗已关闭':'自动弹窗已开启'):'登录后可设置公告提醒';body.replaceChildren();error.textContent='';actions.replaceChildren();
   for(const item of data.items){const row=el('button',item.title+' · '+new Date(item.published_at*1000).toLocaleDateString());row.type='button';row.style.display='block';row.onclick=()=>showItem(item);body.append(row);}
   if(!data.items.length)body.textContent='暂无已发布公告';
   action('关闭',async()=>close());if(page>0)action('上一页',async()=>{page=Math.max(0,page-20);await history();});if(page+20<data.total)action('下一页',async()=>{page+=20;await history();});
   if(owner)action(preferences.muted?'重新开启自动提醒':'关闭以后所有自动提醒',async()=>{await mute(!preferences.muted);await history();});
   if(!dialog.open)dialog.showModal();
  }
  button.onclick=()=>{page=0;history().catch(e=>{title.textContent='更新公告';body.textContent=e.message;actions.replaceChildren();action('关闭',async()=>close());if(!dialog.open)dialog.showModal();});};
  const data=await request('GET','/announcements');latest=data.items[0]||null;await settings();
  const maybeShow=()=>{if(!ready||opened||!owner||!latest||preferences?.muted||preferences?.ignored.includes(latest.id)||document.querySelector('dialog[open]'))return;
   try{if(sessionStorage.getItem(sessionKey(latest.id)))return;}catch(e){}
   opened=true;showItem(latest);
  };
  root.addEventListener('racepick-ready',()=>{ready=true;maybeShow();},{once:true});
  new MutationObserver(maybeShow).observe(document.body,{subtree:true,attributes:true,attributeFilter:['open']});
 }
 root.AnnouncementUI={init};
})(globalThis);
