/**
 * MutualExclusionAllocator — 数据访问层
 * 
 * 所有数据读写统一走此接口。
 * dataSource='static' → localStorage + 本地 JSON 文件（兼容 GitHub Pages）
 * dataSource='api'    → 通过 HTTP API 读写（部署到自有服务器后切换）
 * 
 * 新增后端功能只需在此文件新增方法，前端 UI 代码不需要改。
 */

const api = (() => {
  const cfg = APP_CONFIG;

  // =======================================================================
  //  内部工具
  // =======================================================================

  /** 发起 API 请求（dataSource='api' 时使用）*/
  async function apiFetch(method, path, body = null) {
    const url = `${cfg.apiBaseUrl}${cfg.apiPrefix}${path}`;
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',   // 携带 cookie（用于 session/auth）
    };
    if (body) opts.body = JSON.stringify(body);
    const resp = await fetch(url, opts);
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    return resp.json();
  }

  // =======================================================================
  //  公开接口 — 前端 UI 只调用这些方法
  // =======================================================================

  return {
    // ---------------------------------------------------------------------
    //  车辆数据
    // ---------------------------------------------------------------------

    /** 获取车辆列表 + 昵称映射 */
    async getCars() {
      if (cfg.dataSource === 'api') {
        return apiFetch('GET', '/cars');
      }
      // static: 从本地 JSON 加载
      const resp = await fetch(cfg.staticPaths.carsJson);
      if (!resp.ok) throw new Error('cars.json 加载失败');
      return resp.json();
    },

    /** 获取赛道数据 */
    async getRaceData() {
      if (cfg.dataSource === 'api') {
        return apiFetch('GET', '/races');
      }
      const resp = await fetch(cfg.staticPaths.dataJson);
      if (!resp.ok) throw new Error('data.json 加载失败');
      return resp.json();
    },

    // ---------------------------------------------------------------------
    //  车库持久化
    // ---------------------------------------------------------------------

    /** 加载已选车辆集合 */
    async loadGarage() {
      if (cfg.dataSource === 'api') {
        return apiFetch('GET', '/garage');
      }
      try {
        const stored = localStorage.getItem(cfg.storageKeys.garage);
        return stored ? new Set(JSON.parse(stored)) : new Set();
      } catch {
        return new Set();
      }
    },

    /** 保存已选车辆集合 */
    async saveGarage(carSet) {
      if (cfg.dataSource === 'api') {
        return apiFetch('PUT', '/garage', { cars: [...carSet] });
      }
      try {
        localStorage.setItem(cfg.storageKeys.garage, JSON.stringify([...carSet]));
      } catch (e) {
        console.warn('garage 保存失败:', e.message);
      }
    },

    // ---------------------------------------------------------------------
    //  UI 偏好持久化
    // ---------------------------------------------------------------------

    /** 加载 UI 偏好 */
    loadPref(key, fallback = null) {
      try {
        const val = localStorage.getItem(key);
        return val !== null ? JSON.parse(val) : fallback;
      } catch {
        return fallback;
      }
    },

    /** 保存 UI 偏好 */
    savePref(key, value) {
      try {
        localStorage.setItem(key, JSON.stringify(value));
      } catch (e) {
        console.warn(`pref ${key} 保存失败:`, e.message);
      }
    },

    // ---------------------------------------------------------------------
    //  未来扩展 — 骨架方法（暂抛未实现异常）
    // ---------------------------------------------------------------------

    /** 登录 */
    async login(username, password) {
      if (cfg.dataSource === 'static') {
        console.warn('login: dataSource=static, 跳过');
        return null;
      }
      return apiFetch('POST', '/auth/login', { username, password });
    },

    /** 注册 */
    async register(username, password) {
      if (cfg.dataSource === 'static') {
        console.warn('register: dataSource=static, 跳过');
        return null;
      }
      return apiFetch('POST', '/auth/register', { username, password });
    },

    /** 退出登录 */
    async logout() {
      if (cfg.dataSource === 'static') return;
      return apiFetch('POST', '/auth/logout');
    },

    /** 获取当前用户信息 */
    async getUser() {
      if (cfg.dataSource === 'static') return null;
      return apiFetch('GET', '/auth/me');
    },

    /** 提交成绩（排行榜） */
    async submitScore(scoreData) {
      if (cfg.dataSource === 'static') {
        console.warn('submitScore: 未启用');
        return;
      }
      return apiFetch('POST', '/leaderboard', scoreData);
    },

    /** 获取排行榜 */
    async getLeaderboard(options = {}) {
      if (cfg.dataSource === 'static') return [];
      const q = new URLSearchParams(options).toString();
      return apiFetch('GET', `/leaderboard?${q}`);
    },
  };
})();
