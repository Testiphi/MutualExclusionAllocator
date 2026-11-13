'use strict';

const specialPattern = /稳定跳图|旧跳图|新跳图|跳图|滑栏杆|滑雪|跳楼|跳船|挂桥/;
const videoUrl = /^https:\/\/www\.bilibili\.com\/video\/(?:BV[A-Za-z0-9]+|av[0-9]+)\/(?:\?(?:p=[0-9]+(?:&t=[0-9]+)?|t=[0-9]+))?$/;

// BV identifiers encode the numeric identifier used by the Bilibili mini-program.
const bvAlphabet = 'FcwAPNKTMug3GV5Lj7EJnHpWsx4tb8haYeviqBz6rkCy12mUSDQX9RdoZf';
function biliTarget(url) {
  const id = url.match(/\/video\/(av[0-9]+|BV1[A-Za-z0-9]{9})\//)?.[1];
  if (!id) return {};
  if (id === 'BV194421U7AG' && /[?&]p=4(?:&|$)/.test(url)) {
    return {shortLink:'#小程序://哔哩哔哩弹幕网/3h3vqAA34Jtx4vq'};
  }
  if (id.startsWith('av')) return {aid:id.slice(2)};
  if (typeof BigInt !== 'function') return {};
  let value = BigInt(0);
  for (const index of [9,7,5,6,4,8,3,10,11]) {
    const digit = bvAlphabet.indexOf(id[index]);
    if (digit < 0) return {};
    value = value * BigInt(58) + BigInt(digit);
  }
  const aid = (value & BigInt(2251799813685247)) ^ BigInt(23442827791579);
  return aid > BigInt(0) ? {aid:aid.toString()} : {};
}

function matches(video, scope) {
  if (video.car !== scope.car) return false;
  if (scope.reference===true) return true;
  const zones = [...new Set(video.title.match(/[四五]区/g) || [])];
  const zone = video.zone || (zones.length === 1 ? zones[0] : '');
  if (zone && zone !== scope.zone) return false;
  const automatic = video.tier === '自动' || (!video.tier && /(?<!非)自动/.test(video.title));
  if (automatic !== (scope.tier === '自动')) return false;
  const special = video.title.match(specialPattern)?.[0];
  if (scope.coverage) {
    if (video.tier && video.tier !== scope.tier) return false;
    return scope.route ? special === scope.route : !special;
  }
  const waterfront = (scope.server === 'cn' && scope.big === '花都疾驰' && scope.small === '河畔漂移') ||
    (scope.server === 'global' && scope.big === '巴黎' && scope.small === '塞纳河岸');
  const route = waterfront && special === '新跳图' ? '稳定跳图' : special;
  return route ? scope.routes.includes(route) : scope.routes.length === 0;
}

function fetchVideos(wx, scope, origin = 'http://127.0.0.1:18746') {
  if (!['http://127.0.0.1:18746', 'https://account-test.racepick.cn', 'https://racepick.cn'].includes(origin)) {
    return Promise.reject(Error('跑法视频服务地址无效'));
  }
  const query = ['server', 'big', 'small'].map(key => key + '=' + encodeURIComponent(scope[key])).join('&');
  return new Promise((resolve, reject) => {
    const failed = () => reject(Error('跑法视频读取失败，请重试'));
    wx.request({
      url: origin + '/api/route-videos?' + query,
      method: 'GET',
      timeout: 5000,
      success({statusCode, data}) {
        if (statusCode !== 200 || !Array.isArray(data?.videos)) return failed();
        if (data.videos.some(video => typeof video?.title !== 'string' ||
            typeof video.url !== 'string' || !videoUrl.test(video.url))) return failed();
        resolve(data.videos);
      },
      fail: failed,
    });
  });
}

function videoItem({id, title, url, tier, zone, part, start, lap}) {
  return {
    id, title, url, part, start, ...biliTarget(url),
    detail: [zone, tier, lap == null ? '' : lap + ' 秒', part > 1 ? 'P' + part : '',
      start ? '从 ' + start + ' 秒播放' : ''].filter(Boolean).join(' · '),
  };
}

async function load(wx, scope, origin) {
  const videos = await fetchVideos(wx, scope, origin);
  return videos.filter(video => matches(video, scope) &&
    (scope.videoId === undefined || String(video.id) === scope.videoId)).map(videoItem);
}

async function loadForCars(wx, scope, cars, origin) {
  const videos = await fetchVideos(wx, scope, origin);
  return Object.fromEntries(cars.map(car => [
    car, videos.filter(video => matches(video, {...scope, car})).map(videoItem),
  ]));
}

function open(wx, scope) {
  wx.navigateTo({url: '/pages/route-videos/route-videos?scope=' + encodeURIComponent(JSON.stringify(scope))});
}

module.exports = {load, loadForCars, open};
