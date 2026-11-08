'use strict';
const {publicConflict}=require('./profile_conflict');
// Whitelisted export for independent acceptance projects, never raw page/client state.
const number=v=>Number.isInteger(v)&&v>=0?v:null;
const text=v=>typeof v==='string'?v.slice(0,160):null;
function selection(value){return value?{
 cars:Array.isArray(value.cars)?value.cars.filter(v=>typeof v==='string'):[],
 stars:Object.fromEntries(Object.entries(value.stars||{}).filter(([,v])=>Number.isInteger(v))),
 ocMap:Object.fromEntries(Object.entries(value.ocMap||value.oc||{}).filter(([,v])=>typeof v==='boolean'))
}:null;}
function createAcceptanceReport({build,device={},account={},diagnostics={},ocr=null,profiles={},view={},now=Date.now()}){
 const counts=diagnostics?.counts||{},health=diagnostics?.healthDiagnostic;
 const out={kind:diagnostics?.allowCloudWrites?'racepick-mirror-account-write-report-v1':'racepick-mirror-account-readonly-report-v1',buildId:text(build?.buildId),planId:text(build?.planId),
  collectedAtUtc:new Date(now).toISOString(),device:Object.fromEntries(['model','system','platform','version','SDKVersion'].map(k=>[k,text(device[k])])),
  session:{loggedIn:!!account.actor,role:['player','admin','superadmin'].includes(account.actor?.role)?account.actor.role:null,
   expiresInSeconds:Number.isInteger(account.expires_at)?Math.floor(account.expires_at-now/1000):null,
   pendingAuth:!!account.pendingAuth,validationSource:'AccountClient install/refresh; no raw token inspected'},
  allowCloudWrites:diagnostics?.allowCloudWrites===true,connectionReady:diagnostics?.ready===true,
  health:health?{kind:text(health.kind),httpStatus:number(health.httpStatus),nativeCode:Number.isInteger(health.nativeCode)?health.nativeCode:null,errno:Number.isInteger(health.errno)?health.errno:null}:null,
  counts:Object.fromEntries(['health','guest','snapshot','login','profile','session','recovery'].map(k=>[k,number(counts[k])])),
  profiles:{},current:{server:['cn','global'].includes(view.server)?view.server:null,selectedCount:number(view.selectedCount),
   mappedSlots:number(view.mappedSlots),schemeCount:number(view.schemeCount),selection:selection(view.selection)}};
 if(build?.ocrBinding){
  out.counts.put=number(counts.put);
  out.ocr=ocr?{
   phase:text(ocr.task?.phase),catalogVersion:text(ocr.task?.version),
   appliedSlots:view.server==='cn'&&Array.isArray(view.maps)?view.maps.slice(0,5).map(m=>m?{big:text(m.big),small:text(m.small)}:null):null,
   uploads:number(ocr.network?.uploads),queries:number(ocr.network?.queries),
   recoveries:number(ocr.network?.recoveries),versions:{cn:text(ocr.versions?.cn),global:text(ocr.versions?.global)}
  }:null;
 }
 if(diagnostics?.registration){out.kind='racepick-isolated-registration-report-v1';for(const k of ['register','resend-verification','verify-email','put'])out.counts[k]=number(counts[k]);}
 if(diagnostics?.readbackAcceptance){out.kind='racepick-saved-profile-readback-report-v1';out.counts.put=number(counts.put);out.readback={enabled:true,halted:diagnostics.readbackHalted===true};}
 if(diagnostics?.conflictConfigured){out.kind='racepick-w3-conflict-report-v1';out.counts.put=number(counts.put);const c=diagnostics.conflictAcceptance;out.conflictAcceptance=c?{role:['a','b'].includes(c.role)?c.role:null,group:text(c.group),reads:number(c.reads),attempts:number(c.attempts),successes:number(c.successes),conflicts:number(c.conflicts),halted:text(c.halted),pending:c.pending===true,peerVerified:c.peerVerified===true,servers:Object.fromEntries(['cn','global'].map(k=>[k,{loaded:c.servers?.[k]?.loaded===true,outcome:['success','conflict','pending'].includes(c.servers?.[k]?.outcome)?c.servers[k].outcome:null,final:c.servers?.[k]?.final===true}]))}:null;}
 if(diagnostics?.allowCloudWrites&&!diagnostics?.conflictConfigured){out.counts.put=number(counts.put);const w=diagnostics.writeAcceptance;out.writeAcceptance=w?{reads:number(w.reads),attempts:number(w.attempts),successes:number(w.successes),halted:text(w.halted),pending:w.pending===true,servers:Object.fromEntries(['cn','global'].map(k=>[k,{loaded:w.servers?.[k]?.loaded===true,stage:number(w.servers?.[k]?.stage),revision:number(w.servers?.[k]?.revision),awaitingReload:w.servers?.[k]?.awaitingReload===true}]))}:null;}
 for(const server of ['cn','global']){const p=profiles[server];out.profiles[server]=p?{
  loaded:p.loaded===true,remote:p.remote?{revision:number(p.remote.revision),kind:['null','empty','saved'].includes(p.remote.kind)?p.remote.kind:null,
   storage:p.remote.storage==='account'?'account':null,remoteSupported:p.remote.remoteSupported===true}:null,
  dirty:p.dirty===true,pendingSave:p.pendingSave===true,hasConflict:p.hasConflict===true,draft:selection(p.draft),...(diagnostics?.conflictConfigured?{conflict:publicConflict(p.conflict),conflictHistory:(p.conflictHistory||[]).map(publicConflict).filter(Boolean)}:{})
 }:null;}
 return out;
}
module.exports={createAcceptanceReport};
