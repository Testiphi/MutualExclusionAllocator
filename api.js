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
  const guestKey='racepick.guest-profile.v1';
  function guestProfile(){
    const raw=localStorage.getItem(guestKey);if(raw===null)return null;
    const p=JSON.parse(raw);
    if(!p||!Array.isArray(p.cars)||p.cars.some(c=>typeof c!=='string')||!p.stars||typeof p.stars!=='object'||Array.isArray(p.stars))throw Error('已保存的游客车库格式损坏，未覆盖');
    return p;
  }
  let versionedSnapshot;
  function scoreSnapshot() {
    if (!versionedSnapshot) versionedSnapshot = fetch('/api/scores/snapshot', {cache:'no-store'}).then(response => {
      if (!response.ok) throw new Error('成绩版本加载失败，请刷新后重试');
      return response.json();
    });
    return versionedSnapshot;
  }

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
    guestProfile,
    guestRevision:()=>localStorage.getItem(guestKey)??JSON.stringify([localStorage.getItem(cfg.storageKeys.garage),localStorage.getItem(cfg.storageKeys.starMap)]),
    saveGuestProfile(value,expected){
      if(expected!==this.guestRevision())throw Error('另一窗口已更新车库，请先恢复已保存的车库再修改');
      localStorage.setItem(guestKey,JSON.stringify({cars:value.cars,stars:value.stars}));
    },
    // ---------------------------------------------------------------------
    //  车辆数据
    // ---------------------------------------------------------------------

    /** 获取车辆列表 + 昵称映射 */
    async getCars() {
      if (globalThis.RACEPICK_VERSIONED_SCORES) return (await scoreSnapshot()).cars;
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
      if (globalThis.RACEPICK_VERSIONED_SCORES) return (await scoreSnapshot()).data;
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
    async loadGarage(knownCars) {
      if (globalThis.accountUI?.active()) return accountUI.garage();
      if (cfg.dataSource === 'api') {
        return appState.garage(await apiFetch('GET', '/garage'), knownCars);
      }
      const profile=guestProfile();if(profile)return appState.garage(profile.cars,knownCars);
      const stored = localStorage.getItem(cfg.storageKeys.garage);
      return stored !== null ? appState.garage(JSON.parse(stored), knownCars) : null;
    },

    /** 保存已选车辆集合 */
    async saveGarage(carSet) {
      if (globalThis.accountUI?.active()) return accountUI.saveGarage(carSet);
      if (cfg.dataSource === 'api') {
        return apiFetch('PUT', '/garage', { cars: [...carSet] });
      }
      localStorage.setItem(cfg.storageKeys.garage, JSON.stringify([...carSet]));
    },

    // ---------------------------------------------------------------------
    //  UI 偏好持久化
    // ---------------------------------------------------------------------

    /** 加载 UI 偏好 */
    loadPref(key, fallback = null) {
      try {
        if(key===cfg.storageKeys.starMap){const p=guestProfile();if(p)return p.stars;}
        const val = localStorage.getItem(key);
        return val !== null ? JSON.parse(val) : fallback;
      } catch {
        return fallback;
      }
    },

    /** 保存 UI 偏好 */
    savePref(key, value) {
      localStorage.setItem(key, JSON.stringify(value));
    },


  };
})();
