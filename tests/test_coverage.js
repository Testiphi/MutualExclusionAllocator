'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../coverage.js'),'utf8'),html=fs.readFileSync(path.join(__dirname,'../coverage.html'),'utf8');
class Node{
 constructor(tag='div'){this.tag=tag;this.children=[];this.value='';this.dataset={};this.attrs={};this.style={setProperty:(k,v)=>this.attrs[k]=v};this.hidden=false;this.own='';}
 set textContent(s){this.own=String(s);this.children=[];}get textContent(){return this.own+this.children.map(n=>n.textContent).join('');}
 append(...n){this.children.push(...n);if(this.tag==='select'&&!this.value)this.value=this.children[0]?.value||'';}
 replaceChildren(...n){this.children=[];this.own='';if(this.tag==='select')this.value='';this.append(...n);}
 getBoundingClientRect(){return {left:120,top:200,bottom:232,width:72,height:32};}setAttribute(k,v){this.attrs[k]=v;}showModal(){this.open=true;}close(){this.open=false;}reportValidity(){return true;}
}
function fixture({guest=false,failSubmit=false,global=false,failLoad=false,columnLimit=48,columnTotal=3,expert=false}={}){
 const ids={};for(const m of html.matchAll(/id="([^"]+)"/g))ids[m[1]]=new Node(['server','map','route','star','choice'].includes(m[1])?'select':'div');
 Object.assign(ids.server,{value:global?'global':'cn'});ids.map.value='all';ids.route.value='normal';ids.gaps.checked=false;
 let now=1000;class Clock extends Date{static now(){return now;}}
 const calls=[],navigations=[];let failures=failSubmit?1:0,requestId=0,user=guest?null:{id:'player',verified:true,role:'player'};
 const target={big:'测试地图',small:'道路',zone:'五区',tier:'理论',car:'恶魔',stars:null,route:''};
 const data=(body={})=>({server:ids.server.value,user_id:user?.id||null,access:{level:0,points:0,valid:0,high:0,chosen:null},maps:[{id:'a'.repeat(24),name:'测试地图'}],column_total:columnTotal,column_offset:Number(body.offset||0),column_limit:columnLimit,
  columns:['a','b','恶魔'].map(car=>({car,max_stars:6,star_options:[4,5,6],stars:expert?(body.star_map?.[car]||6):null,coverage_count:3})),rows:[{big:'测试地图',small:'道路',route:'',reference:{car:'a',stars:6,value:25,tier:'理论',route:'普通跑法'},cells:[{key:'public',status:'filled',value:expert&&body.star_map?.a===5?26:25,public:true},{key:'hidden',status:'filled',value:null,public:false},{key:'blank',status:'empty',target:ids.server.value==='cn'?target:{...target,server:'global',oc:false}}]}]});
 const document={getElementById:id=>{assert.ok(ids[id],id);return ids[id];},createElement:t=>new Node(t),querySelectorAll:()=>[]};
 const context={Date:Clock,innerWidth:390,document,location:{search:global?'?server=global':expert?'?tier=高手':'',origin:'http://127.0.0.1:8000',assign:url=>navigations.push(url)},URL,URLSearchParams,AbortController,setTimeout,clearTimeout,crypto:{randomUUID:()=>String(++requestId).padStart(32,'0')},
  fetch:async(url,opts)=>{calls.push({url,opts,body:opts.body?JSON.parse(opts.body):null});let value,ok=true;
   if(url==='/api/auth/me')value={user,csrf:'csrf'};
   else if(url==='/api/coverage/view'){value=failLoad?{detail:'加载失败'}:data(opts.body?JSON.parse(opts.body):{});ok=!failLoad;}
   else if(url==='/api/submissions')value={ids:['saved-submission']};
   else if(url.endsWith('/submit')){if(failures-- >0){ok=false;value={detail:'提交中断，草稿仍保留'};}else value={status:'pending'};}
   else throw Error('unexpected '+url);
   return {ok,json:async()=>value};}};
 vm.runInNewContext(source,context);const settle=async()=>{for(let i=0;i<45;i++)await Promise.resolve();};
 return {ids,calls,navigations,settle,advance:ms=>{now+=ms;},setUser:u=>{user=u;},blank:()=>ids.body.children[0].children[5].children[0]};
}
test('desktop empty cells navigate to the one shared form with target only and no draft write',async()=>{
 const f=fixture();await f.settle();assert.equal(f.ids.body.children[0].children[2].textContent,'道路');assert.equal(f.ids.body.children[0].children[3].textContent,'25');assert.equal(f.ids.body.children[0].children[4].textContent,'***');
 f.blank().onclick({pointerType:'mouse',detail:1});const url=new URL(f.navigations[0],'http://127.0.0.1');assert.equal(url.pathname,'/submissions');assert.equal(url.hash,'#new');const target=JSON.parse(url.searchParams.get('prefill'));assert.equal(target.car,'恶魔');assert.equal(target.server,'cn');assert.equal(target.small,'道路');assert.equal('time' in target,false);
 assert.equal(f.calls.filter(c=>c.url==='/api/submissions').length,0);
});
test('touch movement and scroll cannot navigate; two stationary taps in the same cell do',async()=>{
 const f=fixture();await f.settle();const b=f.blank();
 b.onpointerdown({pointerType:'touch',pointerId:1,clientX:10,clientY:20});b.onpointermove({pointerId:1,clientX:40,clientY:20});b.onclick({pointerType:'touch',detail:1});assert.equal(f.navigations.length,0);
 b.onpointerdown({pointerType:'touch',pointerId:2,clientX:10,clientY:20});b.onclick({pointerType:'touch',detail:1});assert.equal(f.navigations.length,0);assert.equal(f.ids['cell-tap-hint'].hidden,false);
 f.ids['sheet-wrap'].onscroll();assert.equal(f.ids['cell-tap-hint'].hidden,true);b.onpointerdown({pointerType:'touch',pointerId:3,clientX:10,clientY:20});b.onclick({pointerType:'touch',detail:1});assert.equal(f.navigations.length,0);
 f.advance(250);b.onpointerdown({pointerType:'touch',pointerId:4,clientX:10,clientY:20});b.onclick({pointerType:'touch',detail:1});assert.equal(f.navigations.length,0);
 b.onpointerdown({pointerType:'touch',pointerId:5,clientX:10,clientY:20});b.onclick({pointerType:'touch',detail:1});assert.equal(f.navigations.length,1);assert.equal(f.ids['cell-tap-hint'].hidden,true);
 assert.equal(html.includes('cell-action-bar'),false);
});
test('guest return goes straight to the prefilled shared form; global cells never become national drafts',async()=>{
 const f=fixture({guest:true});await f.settle();f.blank().onclick({pointerType:'mouse'});const url=new URL(f.navigations[0],'http://127.0.0.1');assert.equal(url.searchParams.get('login'),'1');const back=new URL(url.searchParams.get('returnTo'),'http://127.0.0.1');assert.equal(back.pathname,'/submissions');assert.ok(back.searchParams.get('prefill'));
 const g=fixture({global:true});await g.settle();g.blank().onclick({pointerType:'mouse'});const target=new URL(g.navigations[0],'http://127.0.0.1');assert.equal(target.searchParams.get('server'),'global');assert.equal(JSON.parse(target.searchParams.get('prefill')).server,'global');assert.equal(g.calls.filter(c=>c.url==='/api/submissions').length,0);
});
test('failed reads clear old grid values',async()=>{
 const f=fixture({failLoad:true});await f.settle();assert.equal(f.ids.body.children.length,0);assert.match(f.ids.message.textContent,/加载失败/);
});

test('column paging follows the backend limit instead of hardcoded old24 columns',async()=>{
 const f=fixture({columnLimit:48,columnTotal:81});await f.settle();assert.equal(f.ids['next-columns'].disabled,false);f.ids['next-columns'].onclick();await f.settle();
 const last=f.calls.filter(c=>c.url==='/api/coverage/view').at(-1);assert.equal(last.body.offset,'48');
 f.ids['previous-columns'].onclick();await f.settle();const previous=f.calls.filter(c=>c.url==='/api/coverage/view').at(-1);assert.equal(previous.body.offset,'0');
});

test('expert header has one selector per vehicle and refreshes the chosen star without changing a garage',async()=>{
 const f=fixture({expert:true});await f.settle();assert.equal(f.ids.head.children[0].children.length,6);const select=f.ids.head.children[0].children[3].children.find(n=>n.tag==='select');assert.ok(select);assert.equal(select.value,'6');
 select.value='5';select.onchange();await f.settle();const last=f.calls.filter(c=>c.url==='/api/coverage/view').at(-1);assert.equal(last.body.star_map.a,5);assert.equal(f.ids.body.children[0].children[3].textContent,'26');assert.equal(f.ids.head.children[0].children[3].children.find(n=>n.tag==='select').value,'5');
 assert.equal(f.calls.filter(c=>c.url.includes('/me/profile')).length,0);
});
