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
  const international = cfg.server === 'global';
  const guestKey = cfg.storageKeys?.guestProfile || 'racepick.guest-profile.v1';
  const garageAliases = new Map();
  function normalizeGarageProfile(profile) {
    if (!international || !profile || !garageAliases.size) return profile;
    const name = key => garageAliases.get(key) || key;
    const normalizeMap = value => {
      if (!value || typeof value !== 'object' || Array.isArray(value)) return value;
      return Object.fromEntries(Object.entries(value).filter(([key]) => name(key) === key || !Object.hasOwn(value,name(key))).map(([key,value])=>[name(key),value]));
    };
    return {...profile, cars:Array.isArray(profile.cars)?[...new Set(profile.cars.map(name))]:profile.cars,
      stars:normalizeMap(profile.stars), ...(profile.ocMap!==undefined?{ocMap:normalizeMap(profile.ocMap)}:{})};
  }
  function guestProfile(){
    const raw=localStorage.getItem(guestKey);if(raw===null)return null;
    const p=JSON.parse(raw);
    if(!p||!Array.isArray(p.cars)||p.cars.some(c=>typeof c!=='string')||!p.stars||typeof p.stars!=='object'||Array.isArray(p.stars))throw Error('已保存的游客车库格式损坏，未覆盖');
    if (international && p.ocMap !== undefined && (!p.ocMap || typeof p.ocMap !== 'object' || Array.isArray(p.ocMap) || Object.values(p.ocMap).some(value => typeof value !== 'boolean'))) throw Error('已保存的国际服OC设置格式损坏，未覆盖');
    return normalizeGarageProfile(p);
  }
  const snapshots = new Map();
  // Only bootstrap GETs may retry. Never replay a profile write or submission.
  async function readBootstrap(path, options) {
    for (let attempt = 0; ; attempt++) {
      const response = await fetch(path, options);
      if (![429, 503].includes(response.status) || attempt === 2) return response;
      const retryAfter = response.headers?.get('Retry-After');
      const seconds = retryAfter === null || retryAfter === undefined ? NaN : Number(retryAfter);
      const requested = Number.isFinite(seconds) ? seconds * 1000 : Date.parse(retryAfter) - Date.now();
      const delay = Number.isFinite(requested) ? Math.max(0, requested) : 1000 * (attempt + 1);
      if (delay > 5000) return response;
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  function scoreSnapshot() {
    const key = 'cn:versioned';
    if (!snapshots.has(key)) snapshots.set(key, readBootstrap('/api/scores/snapshot', {cache:'no-store'}).then(response => {
      if (!response.ok) throw new Error(`成绩版本加载失败（HTTP ${response.status}），请稍后重试`);
      return response.json();
    }).catch(error => { snapshots.delete(key); throw error; }));
    return snapshots.get(key);
  }


  async function internationalSnapshot() {
    const key = 'global:static';
    if (!snapshots.has(key)) snapshots.set(key, (async () => {
      const paths = [cfg.staticPaths.manifestJson, cfg.staticPaths.carsJson, cfg.staticPaths.dataJson];
      const responses = await Promise.all(paths.map(path => readBootstrap(path, {cache: 'no-store'})));
      const failed = responses.find(response => !response.ok);
      if (failed) throw Error(`国际服数据加载失败（HTTP ${failed.status}），请稍后重试`);
      const bytes = await Promise.all(responses.map(response => response.arrayBuffer()));
      const [manifest, cars, data] = bytes.map(raw => JSON.parse(new TextDecoder().decode(raw)));
      const meta = manifest._meta;
      const fields = ['server_id', 'schema_version', 'dataset_version', 'catalog_payload_sha256', 'scores_payload_sha256', 'manifest_file'];
      if (!meta || meta.server_id !== 'global' || meta.schema_version !== 1 || meta.manifest_file !== 'global-data-manifest.json' ||
          fields.some(field => typeof meta[field] === 'undefined') ||
          [cars, data].some(value => !value._meta || fields.some(field => value._meta[field] !== meta[field]))) {
        throw Error('国际服车辆与成绩版本不一致，请刷新后重试');
      }
      if (!globalThis.crypto?.subtle) throw Error('此环境无法校验国际服数据，请通过HTTPS或本机localhost打开');
      for (let i = 1; i < paths.length; i++) {
        const entry = manifest.files?.[paths[i]];
        const digest = await crypto.subtle.digest('SHA-256', bytes[i]);
        const hash = [...new Uint8Array(digest)].map(value => value.toString(16).padStart(2, '0')).join('');
        const payload = i === 1 ? meta.catalog_payload_sha256 : meta.scores_payload_sha256;
        if (!entry || entry.sha256 !== hash || entry.bytes !== bytes[i].byteLength || entry.payload_sha256 !== payload) {
          throw Error('国际服数据完整性校验失败，请刷新后重试');
        }
      }
      if (!Array.isArray(cars.cars) || !Array.isArray(data.tracks)) throw Error('国际服数据结构无效');
      // Only normalize a historical name when the loaded catalogue confirms its replacement.
      if (cars.cars.some(car=>car.title==='Ultima RS'&&car.nickname==='urs') && !cars.cars.some(car=>car.nickname==='Ultima RS')) garageAliases.set('Ultima RS','urs');
      return {version: meta.dataset_version, cars, data};
    })().catch(error => { snapshots.delete(key); throw error; }));
    return snapshots.get(key);
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
    normalizeGarageProfile,
    guestRevision:()=>localStorage.getItem(guestKey)??(international ? null : JSON.stringify([localStorage.getItem(cfg.storageKeys.garage),localStorage.getItem(cfg.storageKeys.starMap)])),
    saveGuestProfile(value,expected){
      if(expected!==this.guestRevision())throw Error('另一窗口已更新车库，请先恢复已保存的车库再修改');
      localStorage.setItem(guestKey,JSON.stringify({cars:value.cars,stars:value.stars,...(international ? {ocMap: value.ocMap || {}} : {})}));
    },
    // ---------------------------------------------------------------------
    //  车辆数据
    // ---------------------------------------------------------------------

    /** 获取车辆列表 + 昵称映射 */
    async getCars() {
      if (cfg.serverError) throw Error(cfg.serverError);
      if (international) return (await internationalSnapshot()).cars;
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
      if (cfg.serverError) throw Error(cfg.serverError);
      if (international) return (await internationalSnapshot()).data;
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
      if (international) { const profile = guestProfile(); return profile ? appState.garage(profile.cars, knownCars) : null; }
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
      if (international) { const profile = guestProfile(); return this.saveGuestProfile({cars: [...carSet], stars: profile?.stars || {}, ocMap: profile?.ocMap || {}}, this.guestRevision()); }
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
