'use strict';
const {requestId}=require('../adapters/id');
function createUsage(wx,client){let binding='',bootstrap=null,expires=0;const ids={};
 return {reset(){binding='';bootstrap=null;expires=0;},async visit(page,server,reason='open'){if(server==='global'&&page!=='home')return;try{const actor=client.state().actor?.id||'guest';if(binding!==actor||Date.now()>=expires){ids.visitor_id=ids.visitor_id||await requestId(wx);ids.session_id=await requestId(wx);bootstrap=await client.call('/usage/session',{method:'POST',data:ids});binding=actor;expires=Date.now()+bootstrap.expires_in*1000;}await client.call('/usage/events',{method:'POST',header:{'X-Usage-Token':bootstrap.token},data:{events:[{id:await requestId(wx),kind:'visit',page,server,reason}]}});}catch(_){/* Optional internal metrics never block business. */}}};}
module.exports={createUsage};
