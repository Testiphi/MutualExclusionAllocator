'use strict';
// W3 execution limits. The original ProfileStore still owns garage state.
const {sha256,utf8}=require('../adapters/hash');
const {equal}=require('./account_write_acceptance');
const {verifyConflict}=require('./profile_conflict');
const baseline=require('./account_readback_binding');
const copy=v=>JSON.parse(JSON.stringify(v));
const fail=()=>Object.assign(Error('W3步骤或回执不符，保留现场并停止'),{status:400,code:'W3_STOP'});
function createConflictAcceptance(wx,profile,actor){
 const key='racepick.conflict-acceptance.'+profile.planId+'.'+sha256(utf8(actor)).slice(0,24),raw=wx.getStorageSync(key);
 let s=raw?JSON.parse(raw):{reads:0,attempts:0,successes:0,conflicts:0,halted:'',pending:null,servers:{cn:{loaded:false,outcome:null,final:false},global:{loaded:false,outcome:null,final:false}}};
 let peerSession=null,ownSession=null,peerExpires=0;const readFlights=new Set();
 const persist=()=>wx.setStorageSync(key,JSON.stringify(s));
 const stop=reason=>{s.halted=reason;persist();throw fail();};
 function beforeRead(server){const r=s.servers[server];if(s.halted||s.pending||!r||readFlights.has(server)||s.reads>=(profile.conflictRole==='a'?4:2)||r.loaded&&(profile.conflictRole!=='a'||r.outcome!=='success'||r.final))throw fail();readFlights.add(server);s.reads++;persist();}
 function read(value,server){readFlights.delete(server);const r=s.servers[server],expected=baseline.profiles[server];if(value.revision!==expected.revision+(r.loaded?1:0)||!equal(value.profile,expected.profile))return stop('record_changed');if(r.loaded)r.final=true;else r.loaded=true;persist();return value;}
 function target(server){const p=copy(baseline.profiles[server].profile);if(profile.conflictRole==='b'){if(server==='cn')p.stars.f5=6;else p.ocMap['万达']=false;}return p;}
 function attest(own,peer){const now=Date.now()/1000,tags=['actorTag','parentTag','sessionTag'];if(!own||!peer||!Number.isSafeInteger(own.expiresAt)||!Number.isSafeInteger(peer.expiresAt)||own.expiresAt>now+3600||peer.expiresAt>now+3600||tags.some(k=>!/^[a-f0-9]{64}$/.test(own[k])||!/^[a-f0-9]{64}$/.test(peer[k]))||own.group!==profile.conflictGroup||peer.group!==own.group||own.role!=='player'||peer.role!=='player'||own.expiresAt<=now||peer.expiresAt<=now||own.actorTag!==peer.actorTag||own.parentTag===peer.parentTag||own.sessionTag===peer.sessionTag)throw fail();peerSession=peer.sessionTag;ownSession=own.sessionTag;peerExpires=peer.expiresAt;return {sameActor:true,differentParent:true,differentNativeSession:true};}
 function beforeSave(server,p,revision,options,proof){const r=s.servers[server];if(s.halted||s.pending||!peerSession||peerExpires<=Date.now()/1000||proof?.sessionTag!==ownSession||!s.servers.cn.loaded||!s.servers.global.loaded||!r||r.outcome||s.attempts>=2||revision!==baseline.profiles[server].revision||options.intent!=='save'||!options.key||!equal(p,target(server)))throw fail();s.attempts++;r.outcome='pending';s.pending={server,key:options.key,revision,profile:copy(p)};persist();}
 function success(result,server){const p=s.pending;if(profile.conflictRole!=='a'||!p||p.server!==server||result?.server!==server||result.revision!==p.revision+1){throw Object.assign(Error('W3保存结果非预期，保留原操作'),{status:200,code:'OPERATION_UNCERTAIN'});}s.servers[server].outcome='success';s.successes++;s.pending=null;s.halted='';persist();return result;}
 function acceptConflict(e,server){if(profile.conflictRole!=='b'||e.status!==409||e.code!=='PROFILE_CONFLICT'||s.pending?.server!==server)return false;const p=s.pending,body=verifyConflict(e.body,server,{revision:p.revision,profile:p.profile});if(body.current.revision!==p.revision+1||!equal(body.current.profile,baseline.profiles[server].profile))throw Object.assign(Error('W3远端冲突版本或内容非预期'),{status:409,code:'OPERATION_UNCERTAIN'});s.servers[server].outcome='conflict';s.conflicts++;s.pending=null;s.halted='';persist();return true;}
 function failed(e){readFlights.clear();s.halted=s.pending&&(!e.status||e.status>=500||e.status===200||e.code==='OPERATION_UNCERTAIN')?'uncertain':'request_failed';persist();}
 function recovery(key,server){if(s.halted!=='uncertain'||s.pending?.key!==key||s.pending.server!==server)throw fail();}
 return {beforeRead,read,beforeSave,success,acceptConflict,failed,recovery,attest,summary:()=>({role:profile.conflictRole,group:profile.conflictGroup,reads:s.reads,attempts:s.attempts,successes:s.successes,conflicts:s.conflicts,halted:s.halted,pending:!!s.pending,peerVerified:!!peerSession,servers:copy(s.servers)})};
}
module.exports={createConflictAcceptance};
