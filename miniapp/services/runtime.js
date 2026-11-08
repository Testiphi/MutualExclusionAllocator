'use strict';
const {createAccountClient}=require('./account');
const {createUsage}=require('./usage');
const {createCloudProfile}=require('./cloud_profile');
const {createAccountConnection,validateAccountProfile}=require('./account_connection');
let client=null,source=null,usageClient=null,unwatchParent=null,connection=null,accountOrigin='',planScope='';const profiles=new Map();
function mount(wx,config,service,accountProfile={enabled:false}){
 const profile=validateAccountProfile(accountProfile);
 if(profile.enabled){const key=profile.origin+'|'+profile.planId;if(source!==key){if(unwatchParent)unwatchParent();if(connection)connection.dispose();else if(client)client.clear();profiles.clear();connection=createAccountConnection(wx,profile);client=connection.client;source=key;accountOrigin=connection.origin;planScope=connection.planId;usageClient=null;unwatchParent=null;}return client;}
 if(connection){connection.dispose();connection=null;client=null;source=null;planScope='';accountOrigin='';}
 if(!service.api||config.kind==='platform'){if(client)client.clear();client=null;source=null;usageClient=null;profiles.clear();return null;}
 if(service.api&&source!==service.api){profiles.clear();accountOrigin=config.origin;if(unwatchParent)unwatchParent();if(client)client.clear();client=createAccountClient(wx,config,service.api);source=service.api;usageClient=createUsage(wx,client);let usageGeneration=client.generation();client.subscribe(()=>{if(client.generation()!==usageGeneration){usageGeneration=client.generation();usageClient.reset();}});if(source.session?.subscribe){let parent=source.session.current().identity;const ownedClient=client;unwatchParent=source.session.subscribe(s=>{if(s.identity!==parent){parent=s.identity;ownedClient.clear();}});}}return client;}
function account(){if(!client)throw Error('请先在主页连接本地服务');return client;}
function storageWx(wx,scope=planScope){
 if(!scope)return wx;
 const prefix='racepick.mirror.acceptance.'+scope+'.';
 return {
  getStorageSync:key=>wx.getStorageSync(prefix+key),
  setStorageSync:(key,value)=>wx.setStorageSync(prefix+key,value),
  removeStorageSync:key=>wx.removeStorageSync(prefix+key),
  getRandomValues:typeof wx.getRandomValues==='function'?options=>wx.getRandomValues(options):undefined
 };
}
function cloudProfile(wx,server,notify,{reload=false}={}){const c=account(),id=c.state().actor?.id;if(!id)throw Error('请先登录');const key=accountOrigin+'|'+id+'|'+c.generation()+'|'+server;let entry=profiles.get(key);if(reload&&entry){if(entry.store.pendingKey())throw Object.assign(Error('上次保存结果未确定，请先核对原操作'),{code:'PROFILE_RECOVERY_REQUIRED'});entry=null;}if(!entry){entry={notify,loaded:false,flight:null};entry.store=createCloudProfile(storageWx(wx),c,accountOrigin,server,s=>entry.notify?.(s),{durable:connection?.policy.productionAccount===true||connection?.policy.writeAcceptance===true||connection?.policy.conflictAcceptance===true,strictConflicts:connection?.policy.conflictAcceptance===true||connection?.policy.productionAccount===true});const init=entry.store.init;entry.store.init=async()=>{if(entry.loaded)return;if(entry.flight)return entry.flight;const work=init().then(()=>{entry.loaded=true;}).finally(()=>{if(entry.flight===work)entry.flight=null;});entry.flight=work;return work;};profiles.set(key,entry);}entry.notify=notify;return entry.store;}
function profileStates(){const actor=client?.state().actor,out={cn:null,global:null};if(!actor)return out;for(const server of ['cn','global']){const entry=profiles.get(accountOrigin+'|'+actor.id+'|'+client.generation()+'|'+server);if(!entry)continue;const store=entry.store,r=store.remote();out[server]={loaded:entry.loaded,remote:r?{revision:r.revision,kind:r.profile===null?'null':r.profile.cars.length?'saved':'empty',storage:r.storage,remoteSupported:r.remote_supported}:null,dirty:store.state().dirty,pendingSave:!!store.pendingKey(),hasConflict:!!store.conflict(),conflict:store.conflict(),conflictHistory:store.conflictHistory(),draft:store.snapshot()};}return out;}
module.exports={mount,account,cloudProfile,profileStates,usage:()=>usageClient,origin:()=>accountOrigin,scope:()=>planScope,policy:()=>connection?connection.policy:{restricted:false,allowCloudWrites:true},diagnostics:()=>connection?connection.diagnostics():null,storageWx};
