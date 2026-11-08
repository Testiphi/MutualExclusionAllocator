'use strict';
// User-authorized isolated Chrome test context. Observe original responses only.
// Never inspect request bodies, headers, cookies, password controls or storage state.
const crypto=require('node:crypto');
const {verifyProfile}=require('../miniapp/services/account_readonly');
const {equal}=require('../miniapp/services/account_write_acceptance');
const copy=v=>JSON.parse(JSON.stringify(v));
async function attach(context,{origin,group,expected}){
 const state={origin,group,counts:{profile:{cn:0,global:0},authMe:0,login:0,profilePut:0},profiles:{},identity:null,blocked:[],errors:[]},pending=new Set();
 await context.route('**/*',async route=>{
  const request=route.request(),u=new URL(request.url()),method=request.method(),p=u.pathname;
  const block=reason=>{state.blocked.push({method,path:p,reason});return route.abort();};
  if(u.origin!==origin)return block('outside_origin');
  if(method==='GET'&&p==='/api/me/profile'){
   const server=u.searchParams.get('server')||'cn';
   if(!['cn','global'].includes(server)||[...u.searchParams].some(([k])=>k!=='server')||[...u.searchParams].length>1||state.counts.profile[server])return block('profile_budget_or_route');
   state.counts.profile[server]++;return route.continue();
  }
  if(method==='GET'&&p==='/api/auth/me'){state.counts.authMe++;return route.continue();}
  if(method==='POST'&&p==='/api/auth/login'&&state.counts.login===0){state.counts.login++;return route.continue();}
  if(method!=='GET')return block('mutation_not_authorized');
  if(p.startsWith('/api/'))return block('unrelated_api');
  return route.continue();
 });
 context.on('response',response=>{
  const request=response.request(),u=new URL(response.url());if(u.origin!==origin||request.method()!=='GET'||!['/api/me/profile','/api/auth/me'].includes(u.pathname))return;
  const work=(async()=>{if(response.status()!==200){state.errors.push({path:u.pathname,status:response.status(),reason:'read_failed'});return;}
   if(u.pathname==='/api/auth/me'){
    const value=await response.json();
    if(value.user){if(typeof value.user.id!=='string'||value.user.role!=='player'){state.errors.push({path:u.pathname,reason:'unexpected_actor'});return;}state.identity={group,role:value.user.role,actorTag:crypto.createHash('sha256').update(origin+'|'+group+'|actor|'+value.user.id).digest('hex')};}
    return;
   }
   const server=u.searchParams.get('server')||'cn',body=await response.json();
   const value=verifyProfile({server,storage:'account',remote_supported:true,revision:body.revision,profile:body.profile},server);
   state.profiles[server]={method:'GET',path:u.pathname,query:u.search,status:response.status(),revision:value.revision,profile:copy(value.profile)};
   if(value.revision!==expected[server].revision||!equal(value.profile,expected[server].profile))state.errors.push({path:u.pathname,server,reason:'record_changed'});
  })().catch(()=>{state.errors.push({path:u.pathname,reason:'response_invalid'});}).finally(()=>pending.delete(work));
  pending.add(work);
 });
 return {async capture(){await Promise.all([...pending]);return copy(state);}};
}
module.exports={attach};
