'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {readScores,projectScores,readReference,projectReference}=require('../miniapp/services/public_scores');

const scope={server:'cn',zone:'五区',tier:'高手',route:'normal',big:'all',q:'',offset:0,oc:false};
const fixture=(star=6,version='fixture-version')=>({
  server:'cn',user_id:null,version,oc:false,maps:[],column_offset:0,column_total:2,column_limit:48,
  columns:['a','b'].map(car=>({car,stars:star,max_stars:6,star_options:[4,5,6]})),
  rows:[{map_id:'x',big:'地图',small:'赛道',route:'',cells:[
    {status:'filled',value:20+(6-star),visibility:'public'},{status:'empty',value:null,visibility:'public'}
  ]}]
});
function transport(reply) {
  const calls=[];
  return {calls,wx:{request(options){
    calls.push(options);
    queueMicrotask(()=>options.success({statusCode:200,data:reply(new URL(options.url))}));
    return {abort(){}};
  }}};
}
test('anonymous public queries keep exact recorded times and apply stars to the chosen column only',async()=>{
  const f=transport(url=>fixture(url.searchParams.get('stars')==='5'?5:6));
  const result=await readScores(f.wx,scope,new Map([['a',5]]),[]);
  assert.deepEqual(result.columns.map(column=>column.stars),[5,6]);
  assert.deepEqual(projectScores(result).rows[0].cells,[{id:'a',text:'21'},{id:'b',text:''}]);
  assert.deepEqual(f.calls.map(call=>[call.method,new URL(call.url).pathname,call.header]),[
    ['GET','/api/coverage',undefined],['GET','/api/coverage',undefined]
  ]);
});
test('star changes reject inconsistent revisions instead of mixing score releases',async()=>{
  const f=transport(url=>url.searchParams.get('stars')==='5'?fixture(5,'next-version'):fixture());
  await assert.rejects(readScores(f.wx,scope,new Map([['a',5]]),[]),/版本/);
});
test('an already displayed sheet changes one car through one narrow lookup and leaves other cells intact',async()=>{
  const base=fixture();
  const f=transport(url=>{
    assert.equal(url.searchParams.get('q'),'b');
    assert.equal(url.searchParams.get('offset'),'0');
    const narrow=fixture(5);
    // The first search hit is a different vehicle.
    narrow.columns[0].car='b-variant';
    narrow.rows[0].cells[1]={status:'filled',value:25.4,visibility:'public'};
    return narrow;
  });
  const result=await readScores(f.wx,scope,new Map([['b',5]]),[],base);
  assert.equal(f.calls.length,1);
  assert.deepEqual(projectScores(result).rows[0].cells,[{id:'a',text:'20'},{id:'b',text:'25.4'}]);
  assert.equal(base.columns[1].stars,6);
  assert.equal(base.rows[0].cells[1].value,null);
});
test('public reference filters trim searches, paginate columns and show actual video counts',async()=>{
  const f=transport(()=>({maps:[['地图','赛道'],['另外','空白']],cars:[['a','Alpha'],['b','Beta']],
    counts:[['地图','赛道','b',2]],column_limit:1}));
  const data=await readReference(f.wx,{server:'cn'},[]);
  const sheet=projectReference(data,{mapQuery:'',carQuery:' BETA ',only:true,offset:10});
  assert.equal(sheet.offset,0);
  assert.equal(sheet.columns[0].id,'b');
  assert.equal(sheet.rows[0].cells[0].text,'2 条');
  assert.equal(sheet.rows.length,1);
  assert.equal(new URL(f.calls[0].url).pathname,'/api/route-videos/matrix');
});

