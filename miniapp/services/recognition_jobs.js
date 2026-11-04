'use strict';
// Task lifecycle port only. The website-owned HTTP contract is not yet delivered.
// api: upload(input), query({id,...binding}), cancel({id,...binding}); optional recover(input).
// currentBinding(): {server,version,identity,catalog:[{big,small}]} from a verified native snapshot/session.
function createRecognitionJobs({api,createKey,currentBinding,now=Date.now,wait=ms=>new Promise(r=>setTimeout(r,ms)),budgetMs=180000}) {
  let attempt=null,generation=0,phase='idle';
  const idValid=id=>typeof id==='string'&&/^[a-f0-9]{32}$/.test(id);
  const error=(message,code)=>Object.assign(Error(message),{code});
  function bind() {
    const b=currentBinding();
    if(!b||b.server!=='cn'||typeof b.identity!=='string'||!b.identity||typeof b.version!=='string'||!b.version||b.version.startsWith('local-')||!Array.isArray(b.catalog))throw error('等待已验证的原生会话和活动地图快照','binding');
    return {...b,catalog:b.catalog.map(x=>({...x}))};
  }
  function check(a,ticket) {
    if(a!==attempt||ticket!==generation)throw error('本次识别已停止','stopped');
    const b=bind();
    if(['identity','server','version'].some(k=>a.binding[k]!==b[k]))throw error('会话或地图目录已变化，请重新识别','stale');
  }
  function payload(a) {return {id:a.id,server:a.binding.server,catalog_version:a.binding.version,identity:a.binding.identity};}
  function dispose(a) {
    if(a&&a.id)Promise.resolve().then(()=>api.cancel(payload(a))).catch(()=>{}); // Server TTL remains the backstop.
  }
  function envelope(a,value) {
    if(!value||!idValid(value.id)||value.server!==a.binding.server||value.catalog_version!==a.binding.version||(a.id&&value.id!==a.id))throw error('识别任务服别或目录版本不一致','protocol');
    return value;
  }
  function result(a,job) {
    const r=job.result;
    if(!r||r.schema_version!==1||r.server!==a.binding.server||r.catalog_version!==a.binding.version||!['complete','partial','rejected'].includes(r.status)||!Array.isArray(r.slots)||r.slots.length!==5||r.slots.some((s,i)=>!s||s.slot!==i+1||!['matched','ambiguous','unresolved'].includes(s.state)))throw error('识别五槽结果格式无效','protocol');
    const slots=r.slots.map(s=>{
      if(s.state!=='matched')return null;
      if(!a.binding.catalog.some(m=>m.big===s.big&&m.small===s.small))throw error('识别地图不在当前目录中','protocol');
      return {big:s.big,small:s.small};
    });
    return {server:a.binding.server,version:a.binding.version,slots};
  }
  async function poll(a,ticket) {
    const deadline=now()+budgetMs;let interval=1000;
    while(true) {
      check(a,ticket);
      if(now()>=deadline)throw error('等待较久，可继续查询原任务','timeout');
      let job;
      try {job=await api.query(payload(a));}
      catch(e) {
        check(a,ticket);
        if(e.status!==429)throw e;
        // retryAfterMs is normalized by the future HTTP adapter, not guessed from JSON.
        const delay=Number.isFinite(e.retryAfterMs)&&e.retryAfterMs>=0?Math.max(1000,e.retryAfterMs):5000;
        if(delay>=deadline-now())throw error('服务限流，可稍后继续查询原任务','timeout');
        await wait(delay);continue;
      }
      check(a,ticket);envelope(a,job);
      if(typeof job.expires_at!=='number'||!Number.isFinite(job.expires_at))throw error('识别任务到期信息无效','protocol');
      if(job.expires_at*1000<=now())throw error('图片与识别结果已到期，请重新选择截图','expired');
      if(job.state==='succeeded'){const value=result(a,job);phase='finished';return value;}
      if(job.state==='failed'){
        if(['IMAGE_SAFETY_REJECTED','IMAGE_SAFETY_UNAVAILABLE','IMAGE_SAFETY_TIMEOUT'].includes(job.error_code))throw Object.assign(error('图片安全处理未通过，请继续手动选图','failed'),{safetyCode:job.error_code});
        throw error('识别失败，请检查截图后重试','failed');
      }
      if(job.state==='cancelled')throw error('识别任务已取消','cancelled');
      if(job.state==='expired')throw error('图片与识别结果已到期','expired');
      if(!['queued','running'].includes(job.state))throw error('未知识别任务状态','protocol');
      const delay=Math.min(interval,Math.max(0,deadline-now()));
      await wait(delay);interval=Math.min(interval+500,3000);
    }
  }
  async function run(a,{recover=false,upload=false}={}) {
    const ticket=++generation;
    try {
      check(a,ticket);
      if(!a.id) {
        phase=upload?'uploading':'recovering';
        if(!upload&&!recover)throw error('上传响应未确认，需恢复原请求','uncertain');
        if(recover&&typeof api.recover!=='function')throw error('等待服务端提供原上传请求恢复能力，请勿重复上传','uncertain');
        const input={path:a.path,size:a.size,request_key:a.key,...payload(a),isCurrent:()=>a===attempt&&ticket===generation};
        const value=await (upload?api.upload(input):api.recover(input));
        envelope(a,value);a.id=value.id;
        if(a!==attempt||ticket!==generation){if(a.cancelled)dispose(a);throw error('本次识别已停止','stopped');}
        check(a,ticket);
      }
      phase='polling';return await poll(a,ticket);
    } catch(e) {
      if(a===attempt&&ticket===generation) {
        if(['binding','stale','protocol','expired','failed','cancelled'].includes(e.code)||[401,403,409,410].includes(e.status)){
          phase='idle';attempt=null;generation++;
        } else phase='recoverable';
      }
      throw e;
    }
  }
  return {
    async start({path,size}) {
      if(attempt)throw error('请先取消当前任务，或继续查询原任务','active');
      if(typeof path!=='string'||!path||!Number.isFinite(size)||size<=0||size>8*1024*1024)throw error('请选择8MiB以内的一张截图','image');
      const binding=bind(),ticket=generation,key=await createKey();
      if(ticket!==generation)throw error('本次识别已停止','stopped');
      if(typeof key!=='string'||!/^[a-zA-Z0-9_-]{16,80}$/.test(key))throw error('请求ID无效','key');
      if(attempt)throw error('已有识别任务正在进行','active');
      attempt={path,size,binding,key,id:null,cancelled:false};return run(attempt,{upload:true});
    },
    resume() {
      if(!attempt)return Promise.reject(error('没有可恢复的识别任务','missing'));
      if(['uploading','polling','recovering'].includes(phase))return Promise.reject(error('任务正在查询，请勿重复操作','active'));
      return run(attempt,{recover:!attempt.id});
    },
    suspend() {generation++;if(attempt)phase='paused';},
    cancel() {generation++;const old=attempt;attempt=null;phase='idle';if(old){old.cancelled=true;dispose(old);}},
    state() {return {phase,id:attempt&&attempt.id,request_key:attempt&&attempt.key,server:attempt&&attempt.binding.server,version:attempt&&attempt.binding.version};}
  };
}
module.exports={createRecognitionJobs};
