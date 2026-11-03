'use strict';
const {createAccountClient}=require('./account');
const {createUsage}=require('./usage');
let client=null,source=null,usageClient=null;
function mount(wx,config,service){if(service.api&&source!==service.api){if(client)client.clear();client=createAccountClient(wx,config,service.api);source=service.api;usageClient=createUsage(wx,client);let usageGeneration=client.generation();client.subscribe(()=>{if(client.generation()!==usageGeneration){usageGeneration=client.generation();usageClient.reset();}});}return client;}
function account(){if(!client)throw Error('请先在主页连接本地服务');return client;}
module.exports={mount,account,usage:()=>usageClient};
