'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {load, open} = require('../miniapp/services/route_videos');
const {createServer, url} = require('../tools/route_video_lab.cjs');

const scope = {server:'cn', big:'实验大图', small:'实验路线', car:'f5', zone:'五区', tier:'理论', routes:[]};

test('read-only fixture uses the website contract, including both servers, tiers and route filters', async t => {
  const server = createServer();
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => server.close());
  const wx = {request: async options => {
    const requested = new URL(options.url);
    assert.equal(requested.origin, 'http://127.0.0.1:18746');
    assert.equal(options.method, 'GET');
    assert.equal(options.header, undefined);
    const response = await fetch('http://127.0.0.1:' + server.address().port + requested.pathname + requested.search);
    options.success({statusCode: response.status, data: await response.json()});
  }};
  const ids = async extra => (await load(wx, {...scope, ...extra})).map(item => item.id);
  assert.deepEqual(await ids({}), [1, 7]);
  assert.deepEqual(await ids({routes:['跳图']}), []);
  assert.deepEqual(await ids({routes:['稳定跳图']}), [4]);
  assert.deepEqual(await ids({zone:'四区', tier:'高手', routes:['跳图']}), [2]);
  assert.deepEqual(await ids({tier:'自动'}), [3]);
  assert.deepEqual(await ids({server:'global'}), [6]);
  assert.deepEqual(await ids({coverage:true, route:'稳定跳图'}), [4]);
  assert.deepEqual(await ids({coverage:true, tier:'高手', route:''}), [7]);
  assert.deepEqual(await ids({small:'不存在'}), []);
  await assert.rejects(ids({small:'故障路线'}), /读取失败/);
  assert.equal((await load(wx, scope))[0].url, url);
});

test('rejects malformed or unsafe links and distinguishes transport failure from an empty list', async () => {
  for (const data of [{}, {videos:[{title:'fake', url:'https://example.invalid'}]}]) {
    await assert.rejects(load({request: options => options.success({statusCode:200, data})}, scope), /读取失败/);
  }
  await assert.rejects(load({request: options => options.fail()}, scope), /读取失败/);
  open({navigateTo: options => assert.deepEqual(JSON.parse(decodeURIComponent(options.url.split('scope=')[1])), scope)}, scope);
});

test('HTTPS video lab sends an anonymous GET to the isolated origin', async () => {
  const origin = 'https://account-test.racepick.cn';
  let requests = 0;
  const wx = {request(options) {
    requests++;
    const requested = new URL(options.url);
    assert.equal(requested.origin, origin);
    assert.equal(requested.pathname, '/api/route-videos');
    assert.deepEqual(Object.fromEntries(requested.searchParams), {
      server: 'global', big: scope.big, small: scope.small,
    });
    assert.equal(options.method, 'GET');
    assert.equal(options.header, undefined);
    options.success({statusCode: 200, data: {videos: []}});
  }};
  assert.deepEqual(await load(wx, {...scope, server:'global'}, origin), []);
  await assert.rejects(load(wx, scope, 'https://example.invalid'), /服务地址无效/);
  assert.equal(requests, 1);
});

test('video entries carry a native target and preserve the original website link', async () => {
  const links = [
    'https://www.bilibili.com/video/BV1eQxR6jE3B/',
    'https://www.bilibili.com/video/BV194421U7AG/?p=4&t=8',
    'https://www.bilibili.com/video/av1756247929/?p=2&t=8',
  ];
  const wx = {request: options => options.success({statusCode:200,data:{videos:links.map((url,id)=>({
    id,url,title:'普通跑法',car:scope.car,part:[1,4,2][id],start:id?8:0,
  }))}})};
  const [single,share,av] = await load(wx, scope);
  assert.equal(single.aid,'117559294691612');
  assert.match(share.shortLink,/3h3vqAA34Jtx4vq$/);
  assert.equal(av.aid,'1756247929');
  assert.deepEqual([single,share,av].map(item=>item.url),links);
  assert.deepEqual([share.part,share.start,av.part,av.start],[4,8,2,8]);
});

test('top-car video groups reuse one response and a selected title opens only that video', async () => {
  let requests = 0;
  const url = 'https://www.bilibili.com/video/BV1eQxR6jE3B/';
  const wx = {request(options) {
    requests++;
    options.success({statusCode:200,data:{videos:[
      {id:1,car:'f5',title:'普通跑法一',url},
      {id:2,car:'f5',title:'普通跑法二',url},
      {id:3,car:'ssc',title:'普通跑法三',url},
      {id:4,car:'ssc',title:'四区普通跑法',url},
    ]}});
  }};
  const {loadForCars} = require('../miniapp/services/route_videos');
  const groups = await loadForCars(wx, scope, ['f5','ssc','其他车']);
  assert.equal(requests,1);
  assert.deepEqual(groups.f5.map(v=>v.id),[1,2]);
  assert.deepEqual(groups.ssc.map(v=>v.id),[3]);
  assert.deepEqual(groups['其他车'],[]);
  assert.deepEqual((await load(wx,{...scope,videoId:'2'})).map(v=>v.id),[2]);
});

test('waterfront normal videos and stable-jump aliases follow the selected route on both servers',async()=>{
  const clip={car:'f5',url};
  const wx={request:o=>o.success({statusCode:200,data:{videos:[
    {...clip,id:1,title:'河畔普通跑法'},
    {...clip,id:2,title:'河畔新跳图'},
    {...clip,id:3,title:'河畔旧跳图'}
  ]}})};
  for(const map of [{server:'cn',big:'花都疾驰',small:'河畔漂移'},{server:'global',big:'巴黎',small:'塞纳河岸'}]){
    const ids=async routes=>(await load(wx,{...scope,...map,routes})).map(v=>v.id);
    assert.deepEqual(await ids([]),[1]);
    assert.deepEqual(await ids(['稳定跳图']),[2]);
    assert.deepEqual(await ids(['旧跳图']),[3]);
  }
});
