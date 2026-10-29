'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../coverage.js'),'utf8'),html=fs.readFileSync(path.join(__dirname,'../coverage.html'),'utf8');
class Node{
 constructor(tag='div'){this.tag=tag;this.children=[];this.value='';this.dataset={};this.attrs={};this.hidden=false;this.own='';}
 set textContent(s){this.own=String(s);this.children=[];}get textContent(){return this.own+this.children.map(n=>n.textContent).join('');}
 append(...n){this.children.push(...n);if(this.tag==='select'&&!this.value)this.value=this.children[0]?.value||'';}
 replaceChildren(...n){this.children=[];this.own='';if(this.tag==='select')this.value='';this.append(...n);}
 setAttribute(k,v){this.attrs[k]=v;}showModal(){this.open=true;}close(){this.open=false;}reportValidity(){return true;}
}
function fixture({guest=false,failSubmit=false,global=false,failLoad=false}={}){
 const ids={};for(const m of html.matchAll(/id="([^"]+)"/g))ids[m[1]]=new Node(['server','map','route','star','choice'].includes(m[1])?'select':'div');
 Object.assign(ids.server,{value:global?'global':'cn'});ids.map.value='all';ids.route.value='normal';ids.star.value='all';ids.gaps.checked=false;
 const calls=[],navigations=[];let failures=failSubmit?1:0,requestId=0,user=guest?null:{id:'player',verified:true,role:'player'};
 const target={big:'测试地图',small:'道路',zone:'五区',tier:'理论',car:'恶魔',stars:null,route:''};
 const data=()=>({server:ids.server.value,user_id:user?.id||null,access:{level:0,points:0,valid:0,high:0,chosen:null},maps:[{id:'a'.repeat(24),name:'测试地图'}],column_total:3,column_offset:0,
  columns:[{car:'a',max_stars:6},{car:'b',max_stars:6},{car:'恶魔',max_stars:6}],rows:[{big:'测试地图',small:'道路',route:'',reference:{car:'a',stars:6,value:25,tier:'理论',route:'普通跑法'},cells:[{key:'public',status:'filled',value:25,public:true},{key:'hidden',status:'filled',value:null,public:false},{key:'blank',status:'empty',target:ids.server.value==='cn'?target:null}]}]});
 const document={getElementById:id=>{assert.ok(ids[id],id);return ids[id];},createElement:t=>new Node(t),querySelectorAll:()=>[]};
 const context={document,location:{search:global?'?server=global':'',origin:'http://127.0.0.1:8000',assign:url=>navigations.push(url)},URL,URLSearchParams,AbortController,setTimeout,clearTimeout,crypto:{randomUUID:()=>String(++requestId).padStart(32,'0')},
  fetch:async(url,opts)=>{calls.push({url,opts,body:opts.body?JSON.parse(opts.body):null});let value,ok=true;
   if(url==='/api/auth/me')value={user,csrf:'csrf'};
   else if(url.startsWith('/api/coverage?')){value=failLoad?{detail:'加载失败'}:data();ok=!failLoad;}
   else if(url==='/api/submissions')value={ids:['saved-submission']};
   else if(url.endsWith('/submit')){if(failures-- >0){ok=false;value={detail:'提交中断，草稿仍保留'};}else value={status:'pending'};}
   else throw Error('unexpected '+url);
   return {ok,json:async()=>value};}};
 vm.runInNewContext(source,context);const settle=async()=>{for(let i=0;i<45;i++)await Promise.resolve();};
 return {ids,calls,navigations,settle,setUser:u=>{user=u;},blank:()=>ids.body.children[0].children[5].children[0]};
}
test('grid displays literal values and masks without score buttons, while empty cells prefill the existing workflow',async()=>{
 const f=fixture();await f.settle();assert.match(f.ids.body.children[0].children[2].textContent,/普通理论 a ★6 · 25秒/);assert.equal(f.ids.body.children[0].children[3].textContent,'25');assert.equal(f.ids.body.children[0].children[4].textContent,'***');
 f.blank().onclick();assert.equal(f.ids['submit-dialog'].open,true);assert.match(f.ids.target.textContent,/测试地图 \/ 道路/);
 f.ids.time.value='26.125';f.ids.evidence.value='来源说明';await f.ids['submission-form'].onsubmit({preventDefault(){}});await f.settle();
 const created=f.calls.find(c=>c.url==='/api/submissions');assert.equal(created.body.entries[0].big,'测试地图');assert.equal(created.body.entries[0].time,'26.125');assert.equal(created.opts.headers['X-Account-ID'],'player');
 assert.equal(f.calls.filter(c=>c.url.endsWith('/submit')).length,1);assert.equal(f.ids['submit-dialog'].open,false);
});
test('failed submit retries the already saved draft, and editing it requires opening the retained draft',async()=>{
 const f=fixture({failSubmit:true});await f.settle();f.blank().onclick();f.ids.time.value='26';f.ids.evidence.value='证据';
 await f.ids['submission-form'].onsubmit({preventDefault(){}});await f.settle();assert.equal(f.ids['saved-draft'].hidden,false);assert.match(f.ids['form-error'].textContent,/草稿仍保留/);
 f.ids.time.value='27';await f.ids['submission-form'].onsubmit({preventDefault(){}});await f.settle();assert.equal(f.calls.filter(c=>c.url==='/api/submissions').length,1);assert.match(f.ids['form-error'].textContent,/草稿已保存/);
 f.ids.time.value='26';await f.ids['submission-form'].onsubmit({preventDefault(){}});await f.settle();assert.equal(f.calls.filter(c=>c.url==='/api/submissions').length,1);assert.equal(f.calls.filter(c=>c.url.endsWith('/submit')).length,2);
});
test('guest login return preserves target context; international blank never enters national submission',async()=>{
 const f=fixture({guest:true});await f.settle();f.blank().onclick();const back=new URL(f.navigations[0],'http://127.0.0.1:8000').searchParams.get('returnTo');assert.match(back,/^\/score-table\?/);assert.match(back,/pick=blank/);
 const g=fixture({global:true});await g.settle();g.blank().onclick();assert.equal(g.ids['submit-dialog'].open,undefined);assert.match(g.ids.message.textContent,/国际服投稿暂未开放/);assert.equal(g.calls.filter(c=>c.opts.method==='POST').length,0);
});
test('failed load clears previous values and changed accounts cannot submit an old target',async()=>{
 const f=fixture();await f.settle();f.blank().onclick();f.ids.time.value='26';f.ids.evidence.value='来源';f.setUser({id:'other',verified:true});await f.ids.filters.onsubmit({preventDefault(){}});await f.settle();
 await f.ids['submission-form'].onsubmit({preventDefault(){}});await f.settle();assert.match(f.ids['form-error'].textContent,/账号已变化/);assert.equal(f.calls.filter(c=>c.opts.method==='POST').length,0);
 const g=fixture({failLoad:true});await g.settle();assert.equal(g.ids.body.children.length,0);assert.match(g.ids.message.textContent,/加载失败/);
});
