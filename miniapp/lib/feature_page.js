'use strict';
const runtime=require('../services/runtime');
function install(page){page.client=runtime.account();page.lastActor=page.client.state().actor?.id||'';page.setData({actor:page.client.state().actor});page.unwatch=page.client.subscribe(s=>{if((s.actor?.id||'')!==page.lastActor){page.lastActor=s.actor?.id||'';page.lastOperation=null;page.setData({actor:s.actor,detail:null,items:[],matrix:null,pictures:[],entries:[],composeRows:[],form:{},preferences:null,me:null,notifications:null,password:'',invitationCode:'',reply:'',reason:'',reviewEntry:null,detailFacts:[],previewFacts:[],summaryFacts:[],positionFacts:[],contributionFacts:[],batchFacts:[],batches:[],batch:null,preview:null,approvals:[],quality:{completeness:0,evidence:0,value:0,reason:''},error:'账号已变化，请重新加载'});}else page.setData({actor:s.actor});});}
async function run(page,fn){if(page.data.busy)return;page.setData({busy:true,error:'',message:''});try{return await fn();}catch(e){page.lastOperation=e.operationKey||null;page.setData({error:e.message,uncertain:!!page.lastOperation});}finally{page.setData({busy:false});}}
function cleanup(page){if(page.unwatch)page.unwatch();page.lastOperation=null;}
async function recover(page){if(!page.lastOperation)return;return run(page,async()=>{await page.client.recover(page.lastOperation);page.lastOperation=null;page.setData({uncertain:false,message:'原操作已完成，请刷新查看最新内容'});});}
const options=(values,labels={})=>values.map(value=>({value,label:labels[value]||value}));
const statuses={draft:'草稿',pending:'待处理',needs_info:'需要补充',accepted:'已采纳',ignored:'未采纳',processing:'处理中',resolved:'已解决',closed:'已关闭',published:'已发布',withdrawn:'已撤回'};
module.exports={install,run,cleanup,recover,options,statuses};
