'use strict';
const { requestId } = require('./id');
// exchange is injected after the backend contract is agreed. No route/secret here.
function createSession(wx, { exchange, setToken, clearToken, now = Date.now }) {
  let expiresAt = 0, generation = 0, flight = null;
  function invalidate() {
    generation++; expiresAt = 0; flight = null; clearToken();
  }
  async function ensure() {
    if (expiresAt > now() + 30000) return;
    if (flight) return flight;
    const ticket = generation;
    const work = (async () => {
      const key = await requestId(wx);
      const code = await new Promise((resolve, reject) => wx.login({ timeout: 10000,
        success(result) { result.code ? resolve(result.code) : reject(Error('微信访客验证失败')); },
        fail() { reject(Error('微信访客验证未完成')); }
      }));
      if (ticket !== generation) throw Error('访客会话已失效');
      // Contract port uses milliseconds; the future HTTP adapter normalizes units.
      const session = await exchange({ code, request_key: key });
      if (ticket !== generation) throw Error('访客会话已失效');
      if (!session || typeof session.token !== 'string' || !session.token ||
          !Number.isFinite(session.expiresAt) || session.expiresAt <= now() + 30000) throw Error('访客会话无效或已过期');
      setToken(session.token); expiresAt = session.expiresAt;
    })();
    flight = work;
    try { await work; }
    finally { if (flight === work) flight = null; }
  }
  return { ensure, invalidate };
}
module.exports = { createSession };
