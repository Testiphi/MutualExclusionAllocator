'use strict';
const {create}=require('../shared/profile_store');
const {sha256,utf8}=require('../adapters/hash');
function createCloudProfile(wx,client,origin,server,notify=()=>{}) {
 const actor=client.state().actor;if(!actor)throw Error('请先登录');
 const scope='racepick.mini.account.'+sha256(utf8(origin)).slice(0,16)+'.'+server+'.';
 let intent='save',remote=null,conflict=null,pendingKey=null;
 const store=create({userId:actor.id,autoSave:false,notify,storage:{getItem:k=>{const v=wx.getStorageSync(scope+k);return v===''||v==null?null:v;},setItem:(k,v)=>wx.setStorageSync(scope+k,v),removeItem:k=>wx.removeStorageSync(scope+k)},
  request:async(method,path,data)=>{
   if(client.state().actor?.id!==actor.id)throw Object.assign(Error('账号已变化'),{status:401});
   if(method==='GET'){remote=await client.profile(server);return remote;}
   if(pendingKey)throw Error('上次车库保存结果未确定，请先核对原操作');
   try{const result=await client.saveProfile(server,data,data.revision,{intent});pendingKey=null;intent='save';return result;}
   catch(e){if(!e.status||e.status>=500||e.code==='OPERATION_UNCERTAIN')pendingKey=e.operationKey;if(e.code==='PROFILE_CONFLICT')conflict=e.body;throw e;}
  }});
 return {...store,importGuest(profile){intent='import_guest';store.update(profile);},remote:()=>remote,conflict:()=>conflict,pendingKey:()=>pendingKey,
  async recover(){if(!pendingKey)throw Error('没有待核对的车库保存');const result=await client.recoverAuth(pendingKey,'profile-save',server);pendingKey=null;intent='save';return result;}};
}
module.exports={createCloudProfile};
