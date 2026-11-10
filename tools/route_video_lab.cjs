'use strict';
const http = require('node:http');

const url = 'https://www.bilibili.com/video/BV1Fixture01/?p=2&t=10';
function createServer() {
  return http.createServer((request, response) => {
    const target = new URL(request.url, 'http://127.0.0.1');
    const send = (status, data) => {
      response.writeHead(status, {'Content-Type': 'application/json'});
      response.end(JSON.stringify(data));
    };
    if (request.method !== 'GET' || target.pathname !== '/api/route-videos') return send(404, {});
    const server = target.searchParams.get('server');
    const small = target.searchParams.get('small');
    if (small === '故障路线') return send(503, {});
    if (target.searchParams.get('big') !== '实验大图' || small !== '实验路线') return send(200, {videos: []});
    const item = {id: 1, car: 'f5', zone: '五区', tier: '理论', title: '本地普通样例', lap: 23, part: 2, start: 10, url};
    const videos = server === 'cn' ? [
      item,
      {...item, id: 2, tier: '高手', zone: '四区', title: '本地四区跳图样例'},
      {...item, id: 3, tier: '自动', title: '本地自动样例'},
      {...item, id: 4, title: '本地稳定跳图样例'},
      {...item, id: 5, car: 'ssc'},
      {...item, id: 7, zone: '', tier: '', title: '旧标记五区非自动样例'},
    ] : server === 'global' ? [{...item, id: 6, title: '本地国际服样例'}] : [];
    return send(200, {videos});
  });
}
if (require.main === module) createServer().listen(18746, '127.0.0.1', () => console.log('Local route video fixture ready'));
module.exports = {createServer, url};
