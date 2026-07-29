/**
 * MutualExclusionAllocator — 全局配置
 * 集中管理所有可配置项，切换部署方式只需修改 dataSource / apiBaseUrl。
 */
const APP_CONFIG = {
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
    carsJson: 'cars.json',
    dataJson: 'gauntlet_data.json',
  },

  // ---- 本地存储键名 ---- 
  storageKeys: {
    garage: 'garageCars',
    zoneMode: 'zoneMode',
    sortMode: 'sortMode',
    starMap: 'starsMap',
  },

  // ---- 算法参数 ----
  algorithm: {
    noCarPriority: 99,           // 无车优先级标记
  },
};
