'use strict';
// W1/W2 execution limits only. Garage state remains in the original ProfileStore.
const {sha256,utf8}=require('../adapters/hash');
const copy=v=>JSON.parse(JSON.stringify(v));
const canonical=v=>JSON.stringify(v&&typeof v==='object'?Array.isArray(v)?v.map(x=>JSON.parse(canonical(x))):Object.fromEntries(Object.keys(v).sort().map(k=>[k,JSON.parse(canonical(v[k]))])):v);
const equal=(a,b)=>canonical(a)===canonical(b);
const fail=()=>Object.assign(Error('W1/W2 已停止或步骤不符；保留草稿并核对验收报告，不重试保存'),{code:'WRITE_ACCEPTANCE_STOP',status:400});
function createWriteAcceptance(wx,plan,actor){
 const key='racepick.write-acceptance.'+plan+'.'+sha256(utf8(actor)).slice(0,24);
 const raw=wx.getStorageSync(key);
 let s=raw?JSON.parse(raw):{reads:0,attempts:0,successes:0,halted:'',servers:{cn:{loaded:false,stage:0},global:{loaded:false,stage:0}}};
 const persist=()=>wx.setStorageSync(key,JSON.stringify(s));
 const stop=reason=>{s.halted=reason;persist();throw fail();};
 const readFlights=new Set();
 function beforeRead(server){const r=s.servers[server];if(s.halted||s.pending||s.reads>=6||readFlights.has(server)||r.loaded&&!r.awaiting)throw fail();readFlights.add(server);s.reads++;persist();}
 function read(value,server){readFlights.delete(server);const r=s.servers[server];if(!r.loaded){if(value.revision!==0||value.profile!==null)return stop('unexpected_initial_record');r.loaded=true;}
  else {if(!r.awaiting||value.revision!==r.awaiting.revision||!equal(value.profile,r.awaiting.profile))return stop('reload_mismatch');r.stage++;delete r.awaiting;}
  r.revision=value.revision;persist();return value;}
 function beforeSave(server,profile,revision,options){
  const r=s.servers[server];
  if(s.halted||s.pending||s.attempts>=4||!s.servers.cn.loaded||!s.servers.global.loaded||r.awaiting||r.stage>=2||revision!==r.revision||options.intent!=='save'||!options.key)throw fail();
  if(r.stage===0){if(profile.cars.length||Object.keys(profile.stars).length||server==='global'&&Object.keys(profile.ocMap).length)throw fail();}
  else {if(s.servers.cn.stage<1||s.servers.global.stage<1)throw fail();
   if(server==='cn'&&!equal(profile,{cars:['f5'],stars:{f5:5}}))throw fail();
   if(server==='global'&&(!equal([...profile.cars].sort(),['ssc','万达'].sort())||profile.ocMap['万达']!==true))throw fail();
  }
  s.attempts++;s.pending={server,key:options.key,revision,profile:copy(profile)};persist();
 }
 function success(result,server){const p=s.pending;if(!p||p.server!==server||result?.server!==server||result.revision!==p.revision+1){s.halted='uncertain';persist();throw Object.assign(Error('保存回执异常；保留原操作，仅查询原 operation'),{status:200,code:'OPERATION_UNCERTAIN'});}s.servers[server].awaiting={revision:result.revision,profile:p.profile};s.successes++;delete s.pending;s.halted='';persist();return result;}
 function failed(e){readFlights.clear();s.halted=s.pending&&(!e.status||e.status>=500||e.status===200||e.code==='OPERATION_UNCERTAIN')?'uncertain':'request_failed';persist();}
 function recovery(key,server){if(!s.pending||s.pending.server!==server||s.pending.key!==key||s.halted!=='uncertain')throw fail();}
 return {beforeRead,read,beforeSave,success,failed,recovery,summary:()=>({reads:s.reads,attempts:s.attempts,successes:s.successes,halted:s.halted,pending:!!s.pending,servers:Object.fromEntries(Object.entries(s.servers).map(([k,v])=>[k,{loaded:v.loaded,stage:v.stage,revision:v.revision??null,awaitingReload:!!v.awaiting}]))})};
}
module.exports={createWriteAcceptance,equal};
