'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../submissions.js'),'utf8');
class Node{
 constructor(tag='div'){this.tag=tag;this.children=[];this.parentElement=null;this.dataset={};this.attrs={};this.value='';this.own='';this.hidden=false;this.listeners={};}
 set textContent(v){this.own=String(v);this.children=[];}get textContent(){return this.own+this.children.map(n=>n.textContent).join('');}
 get options(){return this.children;}
 append(...nodes){for(const n of nodes){if(n.parentElement)n.parentElement.children=n.parentElement.children.filter(c=>c!==n);n.parentElement=this;this.children.push(n);}if(this.tag==='select'&&this.children.length===nodes.length)this.value=this.children[0]?.value||'';}
 replaceChildren(...n){this.children=[];this.own='';if(this.tag==='select')this.value='';this.append(...n);}
 addEventListener(k,f){this.listeners[k]=f;}setAttribute(k,v){this.attrs[k]=v;}focus(){}showModal(){this.open=true;}close(){this.open=false;}
 querySelector(s){return walk(this).find(n=>s.startsWith('.')&&(n.className||'').split(' ').includes(s.slice(1)))||null;}
}
const walk=n=>[n,...n.children.flatMap(walk)];
const entry={big:'甲地图',small:'道路',zone:'五区',tier:'高手',car:'恶魔',stars:5,route:'',time:'26.125',notes:'',video_url:'',unlisted:false};
function fixture({failSubmit=false,files=[],server="cn"}={}){
 const ids={},calls=[];let serial=0,remaining=failSubmit?1:0,payload={...entry};
 const document={createElement:t=>new Node(t),getElementById:id=>ids[id]||(ids[id]=new Node())};
 const catalog={capabilities:server==='global'?{zones:['五区'],tiers:['理论'],max_stars_only:true,oc:true}:undefined,tracks:[{big:'甲地图',small:'道路'}],routes:['跳图'],cars:[{name:'恶魔',title:'Car',zones:['五区','四区'],limits:{五区:[1,6],四区:[1,2]}}]};
 class Reader{readAsDataURL(){this.result='data:image/png;base64,AQ==';this.onload();}}
 const injection=`globalThis.quick={send:sendBatch,prefill:prefillTarget,form:scoreForm,setup(mock,cat){request=mock;catalog=cat;user={id:'player',role:'player'};switchView=async()=>{};loadDetail=async()=>{};}};`;
 const context=vm.createContext({document,URLSearchParams,location:{search:server==="global"?"?server=global":""},FileReader:Reader,crypto:{randomUUID:()=>String(++serial).padStart(32,'0')},console});
 vm.runInContext(code.replace('void init().catch(e=>say(e.message));',injection),context);
 context.quick.setup(async(method,url,body)=>{calls.push({method,url,body});if(url==='/submissions')return {ids:['saved']};if(url.endsWith('/images'))return {id:'image',revision:body.revision+1};if(url.endsWith('/submit')){if(remaining-- >0)throw Error('网络失败，草稿已保存');return {status:'pending'};}throw Error('unexpected '+url);},catalog);
 const row=new Node();row.readEntry=()=>payload;row.readFiles=()=>files;document.getElementById('draftRows').append(row);
 return {api:context.quick,ids,calls,setEntry:e=>{payload=e;},document};
}
test('only a time is needed: empty optional evidence submits through the existing draft and review chain',async()=>{
 const f=fixture();await f.api.send(true);assert.equal(f.calls.length,2);assert.equal(f.calls[0].url,'/submissions');assert.equal(f.calls[0].body.entries[0].time,'26.125');assert.equal(f.calls[0].body.entries[0].notes,'');assert.equal(f.calls[0].body.entries[0].video_url,'');assert.equal(f.calls[1].url,'/submissions/saved/submit');assert.equal(f.calls[1].body.revision,1);assert.match(f.ids.message.textContent,/已提交1条/);
});
test('optional images advance revision; a failed submit retries the same saved draft without re-uploading',async()=>{
 const file={name:'fixture.png',size:10,type:'image/png',lastModified:1};const f=fixture({failSubmit:true,files:[file]});await assert.rejects(()=>f.api.send(true),/草稿已保存/);
 assert.equal(f.calls.filter(c=>c.url==='/submissions').length,1);assert.equal(f.calls.find(c=>c.url.endsWith('/submit')).body.revision,2);
 f.setEntry({...entry,time:'27'});await assert.rejects(()=>f.api.send(true),/稿件已保存/);assert.equal(f.calls.filter(c=>c.url==='/submissions').length,1);
 f.setEntry({...entry});await f.api.send(true);assert.equal(f.calls.filter(c=>c.url.endsWith('/images')).length,1);assert.equal(f.calls.filter(c=>c.url.endsWith('/submit')).length,2);assert.equal(f.calls.filter(c=>c.url==='/submissions').length,1);
});
test('missing time and invalid optional images stop before creating any draft',async()=>{
 const f=fixture();f.setEntry({...entry,time:''});await assert.rejects(()=>f.api.send(true),/填写成绩/);assert.equal(f.calls.length,0);
 const g=fixture({files:[{name:'large.png',size:3*1024*1024,type:'image/png',lastModified:1}]});await assert.rejects(()=>g.api.send(true),/图片最多3张/);assert.equal(g.calls.length,0);
});
test('prefill accepts only catalogue-bound national metadata and never imports URL times or notes',()=>{
 const f=fixture();const p=f.api.prefill({...entry,server:'cn',time:'1',notes:'not imported'});assert.equal(p.time,'');assert.equal(p.notes,'');assert.equal(p.stars,5);
 assert.throws(()=>f.api.prefill({...entry,server:'global'}),/国服/);assert.throws(()=>f.api.prefill({...entry,server:'cn',zone:'四区',stars:5}),/星级/);assert.throws(()=>f.api.prefill({...entry,server:'cn',big:'不存在'}),/目标已变化/);
});
test('known targets are collapsed, only time is required, and optional fields remain available',()=>{
 const f=fixture();const form=f.api.form({...entry,time:'',notes:'',video_url:''},'成绩1',true,true);const nodes=walk(form.node);
 const target=nodes.find(n=>n.tag==='details'&&!n.className);assert.equal(target.open,false);assert.match(target.textContent,/甲地图 \/ 道路/);
 const required=nodes.filter(n=>n.required);assert.equal(required.length,1);assert.equal(required[0].dataset.field,'time');assert.equal(form.optional.open,false);assert.ok(nodes.some(n=>n.dataset.field==='images'));
 const editor=f.api.form(entry,'编辑',true);assert.equal(walk(editor.node).filter(n=>n.dataset.field==='images').length,0);assert.equal(editor.read().notes,entry.notes);
});


test('international prefill and form retain server and OC identity while future sheets stay gated',()=>{
 const f=fixture({server:'global'}),globalEntry={...entry,server:'global',oc:true,tier:'理论',stars:null};
 const p=f.api.prefill({...globalEntry,time:'1',notes:'untrusted'});assert.equal(p.server,'global');assert.equal(p.oc,true);assert.equal(p.time,'');assert.equal(p.notes,'');
 const form=f.api.form(p,'国际服');const read=form.read();assert.equal(read.server,'global');assert.equal(read.oc,true);assert.equal(read.tier,'理论');assert.equal(read.stars,null);
 assert.throws(()=>f.api.prefill({...globalEntry,server:'cn'}),/服别/);assert.throws(()=>f.api.prefill({...globalEntry,tier:'高手',stars:5}),/目标已变化/);
});

test('international save/submit retries keep the same server-bound draft',async()=>{
 const f=fixture({server:'global',failSubmit:true});f.setEntry({...entry,server:'global',oc:false,tier:'理论',stars:null,notes:'隔离测试来源'});
 await assert.rejects(()=>f.api.send(true),/网络失败/);await f.api.send(true);
 const creations=f.calls.filter(c=>c.url==='/submissions');assert.equal(creations.length,1);assert.equal(creations[0].body.entries[0].server,'global');
});
