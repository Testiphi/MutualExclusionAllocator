'use strict';
const {verifyProfile}=require('./account_readonly');
const {equal}=require('./account_write_acceptance');
const copy=v=>JSON.parse(JSON.stringify(v));
function verifyConflict(body,server,submitted){
 const fail=()=>{throw Object.assign(Error('冲突回执与原保存不符；保留原操作并停止'),{status:409,code:'OPERATION_UNCERTAIN'});};
 if(!body||body.code!=='PROFILE_CONFLICT'||body.server!==server||!body.current||!body.submitted||!submitted||
    !Number.isSafeInteger(body.current.revision)||body.current.revision<=submitted.revision||
    !equal(body.submitted,submitted))fail();
 for(const value of [body.current,{...body.submitted,revision:Math.max(1,body.submitted.revision)}]){
  try{verifyProfile({server,storage:'account',remote_supported:true,...value},server);}catch(_){fail();}
 }
 return copy({server,code:'PROFILE_CONFLICT',current:{revision:body.current.revision,profile:body.current.profile},submitted:{revision:body.submitted.revision,profile:body.submitted.profile}});
}
function publicConflict(body){try{return verifyConflict(body,body?.server,body?.submitted);}catch(_){return null;}}
function conflictView(body){const c=publicConflict(body);return c?{local:c.submitted.profile,remote:c.current.profile,localRevision:c.submitted.revision,remoteRevision:c.current.revision,localText:JSON.stringify(c.submitted.profile),remoteText:JSON.stringify(c.current.profile)}:null;}
module.exports={verifyConflict,publicConflict,conflictView};
