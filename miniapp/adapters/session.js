'use strict';
const { requestId } = require('./id');
// exchange is injected after the backend contract is agreed. No route/secret here.
function createSession(wx, { exchange, setToken, clearToken, now = Date.now,credentials,autoRenew=true }) {
  let expiresAt = 0, generation = 0, flight = null,identity=null,pendingCredentials=null,retryAt=0,requiresNewCode=false;
  const listeners=new Set();
  const current=()=>({identity,expiresAt,pending:!!pendingCredentials,requiresNewCode,retryAt});
  const emit=()=>{for(const fn of listeners)fn(current());};
  function invalidate() {
    generation++; expiresAt = 0; flight = null;identity=null;pendingCredentials=null;retryAt=0;requiresNewCode=false;clearToken();emit();
  }
  async function ensure() {
    if (expiresAt > now() + 30000) return;
    if(retryAt>now())throw Object.assign(Error('服务要求稍后再试，原登录请求已保留'),{status:429,code:'SESSION_RETRY_WAIT',retryAfterMs:retryAt-now()});
    if(requiresNewCode)throw Object.assign(Error('原登录代码已失效，请明确重新连接获取新代码'),{status:401,code:'SESSION_NEW_CODE_REQUIRED'});
    if(identity&&!autoRenew)throw Object.assign(Error('访客会话已过期，请重新连接'),{status:401,code:'SESSION_EXPIRED'});
    if (flight) return flight;
    const ticket = generation;
    const work = (async () => {
      if(!pendingCredentials) {
      const key = credentials?null:await requestId(wx);
      const code = credentials?null:await new Promise((resolve, reject) => wx.login({ timeout: 10000,
        success(result) { result.code ? resolve(result.code) : reject(Error('微信访客验证失败')); },
        fail() { reject(Error('微信访客验证未完成')); }
      }));
      const chosen=credentials?await credentials():{code,request_key:key};
      if(ticket!==generation)throw Error('访客会话已失效');pendingCredentials=chosen;
      }
      if (ticket !== generation) throw Error('访客会话已失效');
      // Contract port uses milliseconds; the future HTTP adapter normalizes units.
      let session;
      try{session=await exchange(pendingCredentials);}
      catch(e){
        if(ticket===generation){
          if(Number.isFinite(e.retryAfterMs)&&e.retryAfterMs>0)retryAt=now()+e.retryAfterMs;
          if(['PLATFORM_CODE_REJECTED','PLATFORM_UNAVAILABLE','PLATFORM_RATE_LIMITED','CODE_EXCHANGE_UNCERTAIN','CODE_ALREADY_CLAIMED','REQUEST_KEY_CONFLICT','SESSION_EXPIRED'].includes(e.code))requiresNewCode=true;
          emit();
        }
        throw e;
      }
      if (ticket !== generation) throw Error('访客会话已失效');
      if (!session || typeof session.token !== 'string' || !session.token ||
          !Number.isFinite(session.expiresAt) || session.expiresAt <= now() + 30000) throw Error('访客会话无效或已过期');
      setToken(session.token); expiresAt = session.expiresAt;identity=session.identity||null;pendingCredentials=null;retryAt=0;requiresNewCode=false;emit();
    })();
    flight = work;
    try { await work; }
    finally { if (flight === work) flight = null; }
  }
  return { ensure, invalidate,current,subscribe:fn=>{listeners.add(fn);return()=>listeners.delete(fn);} };
}
module.exports = { createSession };
