/**
 * MutualExclusionAllocator — 全局配置
 * 集中管理所有可配置项，切换部署方式只需修改 dataSource / apiBaseUrl。
 */
const APP_CONFIG = (() => {
  const requestedServer = new URLSearchParams(globalThis.location?.search || '').get('server');
  const serverError = requestedServer !== null && !['cn', 'global'].includes(requestedServer) ? '未知服务器，请使用国服或国际服入口' : null;
  const server = requestedServer === 'global' ? 'global' : 'cn';
  const international = server === 'global';
  globalThis.RACEPICK_SERVER = server;
  const scoped = key => international ? key + '.global' : key;
  return {
  server,
  serverError,
  localOnly: international,
  capabilities: international ? {zones: ['zone5'], tiers: ['理论'], maxStarsOnly: true} : {zones: ['zone5', 'zone4'], tiers: ['理论', '高手', '普通', '自动'], maxStarsOnly: false},
  // ---- 版本 ----
  version: '1.1',

  // ---- 数据源模式 ----
  // 'static' → 所有数据从本地 JSON 文件 + localStorage 加载（GitHub Pages 模式）
  // 'api'    → 所有数据通过 API 加载（部署到自有服务器后切换）
  dataSource: 'static',

  // ---- API 地址（dataSource='api' 时生效）----
  apiBaseUrl: '',                // 例如 'https://your-domain.com'
  apiPrefix: '/api',             // API 路由前缀

  // ---- 静态资源路径（dataSource='static' 时生效）----
  staticPaths: {
    carsJson: international ? 'cars.global.json' : 'cars.json',
    dataJson: international ? 'gauntlet_data.global.json' : 'gauntlet_data.json',
    manifestJson: 'global-data-manifest.json',
  },

  // ---- 本地存储键名 ---- 
  storageKeys: {
    guestProfile: scoped('racepick.guest-profile.v1'),
    guestDraft: scoped('racepick.guest-draft.v1'),
    garage: scoped('garageCars'),
    zoneMode: scoped('zoneMode'),
    sortMode: scoped('sortMode'),
    starMap: scoped('starsMap'),
  },

  // ---- 算法参数 ----
  algorithm: {
    noCarPriority: 99,           // 无车优先级标记
  },
};
})();
