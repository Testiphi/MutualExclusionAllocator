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

  // ---- 功能开关（未来扩展）----
  features: {
    userAccounts: false,         // 用户登录/注册
    leaderboard: false,          // 排行榜
    multiProfile: false,         // 多车库配置（不同用户/场景）
    customChallenges: false,     // 自定义挑战
    historyTracking: false,      // 历史成绩追踪
  },

  // ---- 静态资源路径（dataSource='static' 时生效）----
  staticPaths: {
    carsJson: 'cars.json',
    dataJson: 'data.json',
  },

  // ---- 本地存储键名 ---- 
  storageKeys: {
    garage: 'garageCars',
    zoneMode: 'zoneMode',
    sortMode: 'sortMode',
  },

  // ---- 算法参数 ----
  algorithm: {
    maxSchemesDisplay: 20,       // 最大展示方案数
    noCarPriority: 99,           // 无车优先级标记
  },
};
