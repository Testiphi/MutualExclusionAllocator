'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../submissions.js'),'utf8');
class Node {
    constructor(tag='div'){this.tag=tag;this.children=[];this.value='';this.dataset={};this.listeners={};this.hidden=false;this.isConnected=true;this.attrs={};this.own='';}
    set textContent(v){this.own=String(v);this.children=[];}
    get textContent(){return this.own+this.children.map(c=>c.textContent).join('');}
    append(...nodes){this.children.push(...nodes);if(this.tag==='select'&&this.children.length===nodes.length)this.value=this.children[0].value;}
    prepend(...nodes){this.children.unshift(...nodes);}
    replaceChildren(...nodes){this.own='';this.children=nodes;}
    addEventListener(name,fn){this.listeners[name]=fn;}
    setAttribute(k,v){this.attrs[k]=v;}
    removeAttribute(k){delete this.attrs[k];}
    focus(){}
    showModal(){this.open=true;}
    close(){this.open=false;}
}
const payload={big:'测试地图',small:'测试赛道',zone:'五区',tier:'高手',car:'恶魔',stars:5,time:'26',route:'',notes:''};
function fixture(){
    const ids={},calls=[];const document={createElement:tag=>new Node(tag),getElementById:id=>ids[id]||(ids[id]=new Node()),body:new Node()};
    const context=vm.createContext({document,console});
    const injection=`globalThis.reviewFixture={
      render(item){preview=null;renderReview($('detail'),item);},
      detail(item){selected=item;user={id:'player',role:'player'};renderDetail();},
      quality:qualityForm,setPreview(value){preview=value;},
      setup(mock){request=mock;refreshItem=async()=>{};ask=async()=>true;scoreForm=value=>({node:el('form'),read:()=>value});}
    };`;
    assert.ok(code.includes('void init().catch(e=>say(e.message));'));
    vm.runInContext(code.replace('void init().catch(e=>say(e.message));',injection),context);
    context.reviewFixture.setup(async(method,url,body)=>{calls.push({method,url,body});return {};});
    const item={id:'s1',owner_id:'player',revision:2,status:'pending',payload,comparison:{kind:'new'},images:[],events:[],same_target:[],contribution_info:{eligible:true,contribution:null,events:[]}};
    const walk=n=>[n,...n.children.flatMap(walk)];
    return {api:context.reviewFixture,root:document.getElementById('detail'),calls,item,
      nodes:tag=>walk(document.getElementById('detail')).filter(n=>n.tag===tag),
      message:()=>document.getElementById('message').textContent,
      click:async text=>{const button=walk(document.getElementById('detail')).find(n=>n.tag==='button'&&n.own===text);assert.ok(button,text);await button.onclick();}};
}
function grade(f,values=['3','4','2']){
    const group=f.nodes('fieldset')[0];group.children.filter(n=>n.tag==='label').forEach((label,i)=>{label.children.find(n=>n.tag==='select').value=values[i];});
}
test('one opinion is used for both acceptance and quality without changing scores',async()=>{
    const f=fixture();f.api.render(f.item);assert.equal(f.nodes('textarea').length,1);
    const reason=f.nodes('textarea')[0];assert.equal(reason.maxLength,1000);reason.value='  视频完整，成绩可核验  ';grade(f);
    f.api.setPreview({candidate:payload,basis:{data:'pin'},comparison:{kind:'new'}});await f.click('确认采纳');
    assert.equal(f.calls.length,1);const body=f.calls[0].body;assert.equal(body.reason,'视频完整，成绩可核验');assert.equal(body.quality.reason,body.reason);
    assert.equal(body.quality.completeness+body.quality.evidence+body.quality.value,9);
});
test('requesting more information does not validate or settle partially filled scores',async()=>{
    const f=fixture();f.api.render(f.item);f.nodes('textarea')[0].value='请补充改装截图';grade(f,['3','','']);await f.click('要求补充');
    assert.equal(f.calls.length,1);assert.equal(f.calls[0].body.action,'needs_info');assert.equal(f.calls[0].body.quality,null);assert.equal(f.calls[0].body.reason,'请补充改装截图');
});
test('scored decisions need a complete rating and an opinion; oversized text is not truncated',async()=>{
    const f=fixture();f.api.render(f.item);grade(f,['3','','']);f.nodes('textarea')[0].value='说明';await f.click('忽略本条');assert.equal(f.calls.length,0);assert.match(f.message(),/完成三项/);
    grade(f);f.nodes('textarea')[0].value='';f.api.setPreview({candidate:payload,comparison:{kind:'new'}});await f.click('确认采纳');assert.equal(f.calls.length,0);assert.match(f.message(),/审核意见/);
    f.nodes('textarea')[0].value='字'.repeat(1001);await f.click('忽略本条');assert.equal(f.calls.length,0);assert.equal(f.nodes('textarea')[0].value.length,1001);assert.match(f.message(),/最多1000字/);
});
test('unchanged unscored acceptance remains optional; ignore still needs an opinion',async()=>{
    const f=fixture();f.api.render(f.item);await f.click('忽略本条');assert.equal(f.calls.length,0);
    f.api.setPreview({candidate:payload,comparison:{kind:'new'}});await f.click('确认采纳');assert.equal(f.calls.length,1);assert.equal(f.calls[0].body.reason,'');assert.equal(f.calls[0].body.quality,null);
});
test('legacy zero score needs an opinion and retains its existing 2000-character limit',async()=>{
    const f=fixture();f.api.render({...f.item,contribution_info:{eligible:false}});f.nodes('select')[0].value='0';f.api.setPreview({candidate:payload,comparison:{kind:'new'}});
    await f.click('确认采纳');assert.equal(f.calls.length,0);
    f.nodes('textarea')[0].value='旧'.repeat(1500);await f.click('确认采纳');assert.equal(f.calls[0].body.review_score,0);assert.equal(f.calls[0].body.reason.length,1500);
});
test('identical current opinions display once; distinct historical explanations remain visible',()=>{
    const f=fixture();const item={...f.item,status:'accepted',decision_reason:'已核验',contribution_info:{eligible:true,events:[],contribution:{quality_points:9,bonus:0,quality:JSON.stringify({reason:'已核验'})}}};
    f.api.detail(item);assert.equal(f.root.children.filter(n=>n.own==='审核意见：已核验').length,1);assert.equal(f.root.children.filter(n=>n.own.startsWith('评分说明：')).length,0);
    item.decision_reason='旧'.repeat(1500);f.api.detail(item);assert.ok(f.root.children.some(n=>n.own==='审核意见：'+item.decision_reason));assert.ok(f.root.children.some(n=>n.own==='评分说明：已核验'));
});
test('standalone rating keeps its own adjustment explanation and rejects blank/overlong text',()=>{
    const f=fixture();const q=f.api.quality(f.root,{completeness:3,evidence:4,value:2,reason:'原说明'});
    assert.ok(f.nodes('label').some(n=>n.own==='评分调整说明（投稿人可见）'));f.nodes('textarea')[0].value='复核后调整分数';assert.equal(q.read().reason,'复核后调整分数');
    f.nodes('textarea')[0].value=' ';assert.throws(()=>q.read(),/调整说明/);f.nodes('textarea')[0].value='字'.repeat(1001);assert.throws(()=>q.read(),/最多1000字/);
});
