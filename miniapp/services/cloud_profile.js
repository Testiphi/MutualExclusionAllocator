'use strict';
const {create}=require('../shared/profile_store');
const {requestId}=require('../adapters/id');
const {equal}=require('./account_write_acceptance');
const {verifyConflict}=require('./profile_conflict');
const {sha256,utf8}=require('../adapters/hash');
function createCloudProfile(wx,client,origin,server,notify=()=>{},{durable=false,strictConflicts=false}={}) {
 const actor=client.state().actor;if(!actor)throw Error('请先登录');
 const identityGeneration=client.generation?.();
 const assertCurrent=()=>{if(client.state().actor?.id!==actor.id||(identityGeneration!==undefined&&client.generation?.()!==identityGeneration))throw Object.assign(Error('账号会话已变化，原草稿已保留'),{status:401,code:'STALE_ACCOUNT_PROFILE'});};
 const scope='racepick.mini.account.'+sha256(utf8(origin)).slice(0,16)+'.'+server+'.';
 const metaKey=scope+'operation.'+actor.id;
 let intent='save',remote=null,conflict=null,pendingKey=null,submitted=null,recovered=null,readingFresh=false;let conflictHistory=[];
 if(durable){const raw=wx.getStorageSync(metaKey);if(raw){const m=JSON.parse(raw);pendingKey=m.pendingKey||null;submitted=m.submitted;remote=m.remote;conflict=m.conflict||null;conflictHistory=m.conflictHistory|| (conflict?[conflict]:[]);}}
 const persist=()=>{if(durable)wx.setStorageSync(metaKey,JSON.stringify({pendingKey,submitted,remote,conflict,conflictHistory}));};

 const captureConflict=body=>{const value=strictConflicts?verifyConflict(body,server,submitted):JSON.parse(JSON.stringify(body));conflict=value;conflictHistory.push(JSON.parse(JSON.stringify(value)));persist();};
 const store=create({userId:actor.id,autoSave:false,notify,storage:{getItem:k=>{const v=wx.getStorageSync(scope+k);return v===''||v==null?null:v;},setItem:(k,v)=>wx.setStorageSync(scope+k,v),removeItem:k=>wx.removeStorageSync(scope+k)},
  request:async(method,path,data)=>{
   assertCurrent();
   if(method==='GET'){if(conflict&&!readingFresh&&remote)return remote;if(pendingKey){if(!remote)throw Error('原保存结果未确定，保留草稿；只能查询原操作');return remote;}const value=await client.profile(server);assertCurrent();remote=value;persist();return remote;}
   if(recovered){const value=recovered;recovered=null;return value;}
   if(pendingKey)throw Error('上次车库保存结果未确定，请先核对原操作');
   const snapshot={cars:data.cars,stars:data.stars,...(server==='global'?{ocMap:data.ocMap||{}}:{})};
   const key=await requestId(wx);assertCurrent();submitted={revision:data.revision,profile:snapshot};pendingKey=key;persist();
   try{const result=await client.saveProfile(server,snapshot,data.revision,{intent,key});assertCurrent();pendingKey=null;intent='save';conflict=null;remote={...remote,revision:result.revision,profile:snapshot};persist();return result;}
   catch(e){if(!e.notSent&&(!e.status||e.status>=500||e.status===200||e.code==='OPERATION_UNCERTAIN'))pendingKey=e.operationKey||key;else pendingKey=null;if(e.code==='PROFILE_CONFLICT'){try{captureConflict(e.body);}catch(invalid){pendingKey=e.operationKey||key;persist();throw invalid;}}persist();throw e;}
  }});
 return {...store,update(profile){assertCurrent();store.update(profile);},flush(){assertCurrent();if(conflict)return Promise.reject(Error('冲突两份已保留，请先明确处理，不能再次保存'));return store.flush();},async useRemote(){assertCurrent();readingFresh=true;try{await store.useRemote();assertCurrent();conflict=null;persist();}finally{readingFresh=false;}},async overwrite(){assertCurrent();readingFresh=true;try{return await store.overwrite();}finally{readingFresh=false;}},importGuest(profile){assertCurrent();intent='import_guest';store.update(profile);},state:()=>({...store.state(),...(conflict?{status:'conflict'}:{})}),remote:()=>remote,conflict:()=>conflict,conflictHistory:()=>JSON.parse(JSON.stringify(conflictHistory)),pendingKey:()=>pendingKey,async reload(){assertCurrent();if(pendingKey)throw Error('只能查询原保存操作，不能重载或重发');return store.state().dirty?store.init():store.useRemote();},
  async recover(){assertCurrent();if(!pendingKey)throw Error('没有待核对的车库保存');let result;try{result=await client.recoverAuth(pendingKey,'profile-save',server);}catch(e){if(e.code==='PROFILE_CONFLICT'){captureConflict(e.body);pendingKey=null;persist();}throw e;}assertCurrent();
   if(!Number.isSafeInteger(result?.revision)||result.revision!==submitted.revision+1)throw Error('原保存回执无效，保留原操作');
   const later=store.snapshot(),changed=!equal(later,submitted.profile);recovered=result;
   // Feed the original acknowledgement through the original ProfileStore, without a PUT.
   await store.flush();assertCurrent();if(changed)store.update(later);
   pendingKey=null;intent='save';conflict=null;remote={...remote,revision:result.revision,profile:submitted.profile};persist();return result;}};
}
module.exports={createCloudProfile};
