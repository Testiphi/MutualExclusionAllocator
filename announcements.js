/* Announcement content is plain text. Dismissal preferences are account scoped. */
(function(root){
 const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
 async function init({owner,request}){
  let preferences=null,latest=null,ready=false,opened=false,busy=false,page=0;
  const button=el('button','更新公告');button.type='button';button.className='account-link';document.getElementById(owner?'accountActions':'accountGuestActions').append(button);
  const dialog=el('dialog');dialog.className='account-dialog announcement-dialog';dialog.setAttribute('aria-label','更新公告');
  const header=el('header'),title=el('h2'),closeButton=el('button','×'),meta=el('p'),body=el('div'),error=el('p'),actions=el('footer'),links=el('div'),choices=el('div');
  header.className='announcement-header';closeButton.type='button';closeButton.className='announcement-close';closeButton.setAttribute('aria-label','关闭公告');
  body.className='announcement-content';meta.className='announcement-meta';error.className='announcement-error';error.setAttribute('role','alert');actions.className='announcement-actions';links.className='announcement-links';choices.className='announcement-choices';
  header.append(title,closeButton);actions.append(links,choices);dialog.append(header,meta,body,error,actions);document.body.append(dialog);
  const sessionKey=id=>'racepick.announcement.closed.'+(owner?.id||'guest')+'.'+id;
  const close=()=>{if(latest)try{sessionStorage.setItem(sessionKey(latest.id),'1');}catch(e){}dialog.close();};
  closeButton.onclick=close;
  dialog.addEventListener('cancel',e=>{e.preventDefault();if(!busy)close();});
  function action(text,fn){const b=el('button',text);b.type='button';b.onclick=async()=>{if(busy)return;busy=true;error.textContent='';try{await fn();}catch(e){error.textContent=e.message;}finally{busy=false;}};links.append(b);return b;}
  async function settings(){if(owner)preferences=await request('GET','/me/announcement-preferences');}
  async function mute(value){await settings();preferences=await request('PUT','/me/announcement-preferences',{muted:value,revision:preferences.revision});await settings();}
  function reset(){body.replaceChildren();links.replaceChildren();choices.replaceChildren();error.textContent='';body.scrollTop=0;}
  function checkbox(text,checked,save){const label=el('label'),input=el('input');input.type='checkbox';input.checked=checked;label.append(input,el('span',text));choices.append(label);
   input.onchange=async()=>{const value=input.checked;if(busy){input.checked=!value;return;}busy=true;error.textContent='';choices.querySelectorAll('input').forEach(n=>n.disabled=true);closeButton.disabled=true;
    try{await save(value);}catch(e){input.checked=!value;error.textContent=e.message;}finally{busy=false;closeButton.disabled=false;choices.querySelectorAll('input').forEach(n=>n.disabled=false);}
   };
  }
  function muteChoice(){if(owner)checkbox('以后都不自动显示',preferences.muted,async value=>{await mute(value);});}
  function content(text){for(const block of text.split(/\n\s*\n/)){const lines=block.split('\n');for(const line of lines){const heading=line.match(/^#{1,3}\s+(.+)$/);const n=el(heading?'h3':'p',heading?heading[1]:line);body.append(n);}}}
  function showItem(item){latest=item;reset();title.textContent=item.release_label||'更新公告';meta.textContent=new Date(item.published_at*1000).toLocaleDateString();body.append(el('h2',item.title));content(item.body);
   action('查看历史公告',history);
   if(owner)checkbox('本条不再提醒',preferences.ignored.includes(item.id),async value=>{await request(value?'POST':'DELETE','/me/announcements/'+item.id+'/dismiss',{});preferences.ignored=value?[...new Set([...preferences.ignored,item.id])]:preferences.ignored.filter(id=>id!==item.id);});
   muteChoice();if(!dialog.open)dialog.showModal();
  }
  async function history(){await settings();const data=await request('GET','/announcements?offset='+page);reset();title.textContent='历史公告';meta.textContent=owner?'提醒设置修改后立即保存':'登录后可设置公告提醒';
   for(const item of data.items){const row=el('button',item.title+' · '+new Date(item.published_at*1000).toLocaleDateString());row.type='button';row.className='announcement-history-item';row.onclick=()=>showItem(item);body.append(row);}
   if(!data.items.length)body.textContent='暂无已发布公告';
   if(page>0)action('上一页',async()=>{page=Math.max(0,page-20);await history();});if(page+20<data.total)action('下一页',async()=>{page+=20;await history();});muteChoice();
   if(!dialog.open)dialog.showModal();
  }
  button.onclick=()=>{page=0;history().catch(e=>{reset();title.textContent='更新公告';error.textContent=e.message;if(!dialog.open)dialog.showModal();});};
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
