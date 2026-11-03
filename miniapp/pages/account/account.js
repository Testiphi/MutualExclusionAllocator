'use strict';
const runtime=require('../../services/runtime');
const labels={login:'登录',register:'注册', 'resend-verification':'重发验证邮件','forgot-password':'找回密码','verify-email':'验证邮箱','reset-password':'重置密码','redeem-invitation':'兑换管理员邀请',reauth:'再次验证密码'};
Page({
 data:{moreOpen:false,mode:'login',title:'登录',email:'',password:'',passwordConfirm:'',token:'',invite_code:'',busy:false,actor:null,options:Object.entries(labels).map(([value,label])=>({value,label}))},
 onLoad(o={}){try{this.client=runtime.account();this.setData({actor:this.client.state().actor});if(o.mode&&labels[o.mode])this.changeMode({detail:{value:o.mode}});}catch(e){this.setData({error:e.message});}},
 input(e){this.setData({[e.currentTarget.dataset.key]:e.detail.value});},
 chooseMode(e){this.changeMode({detail:{value:e.currentTarget.dataset.mode}});},
 toggleMore(){this.setData({moreOpen:!this.data.moreOpen});},
 navigate(e){wx.navigateTo({url:'/pages/'+e.currentTarget.dataset.page+'/'+e.currentTarget.dataset.page});},
 changeMode(e){if(this.data.busy)return;this.pending=null;this.setData({mode:e.detail.value,title:labels[e.detail.value],password:'',passwordConfirm:'',token:'',invite_code:'',error:'',message:'',recoverable:false});},
 async submit(){if(this.data.busy||!this.client)return;if(this.pending){this.setData({error:'请先查询上次操作结果，再提交新的操作'});return;}const action=this.data.mode;if(['register','reset-password'].includes(action)&&this.data.password!==this.data.passwordConfirm){this.setData({error:'两次密码不一致，请重新确认'});return;}this.setData({busy:true,error:'',message:''});
  let fields={};if(['register','login','resend-verification','forgot-password'].includes(action))fields.email=this.data.email;
  if(['register','login','reset-password','reauth'].includes(action))fields.password=this.data.password;
  if(['verify-email','reset-password'].includes(action))fields.token=this.data.token;
  if(['register','redeem-invitation'].includes(action))fields.invite_code=this.data.invite_code;
  try{const value=await this.client.auth(action,fields);this.pending=null;this.setData({actor:this.client.state().actor,message:value.message||(['login','reauth'].includes(action)?'登录成功，可返回主页使用账号车库':'操作已完成'),recoverable:false});}
  catch(e){this.pending=e.operationKey&&(!e.status||e.status>=500||e.code==='OPERATION_UNCERTAIN')?{key:e.operationKey,action}:null;this.setData({error:e.message,recoverable:!!this.pending});}
  finally{fields=null;this.setData({busy:false,password:'',passwordConfirm:'',token:'',invite_code:''});}
 },
 async recover(){if(!this.pending)return;try{const r=await this.client.recoverAuth(this.pending.key,this.pending.action);this.pending=null;this.setData({actor:this.client.state().actor,error:'',message:r.message||'原操作已核对',recoverable:false});}catch(e){this.setData({error:e.message});}},
 async logout(){try{await this.client.logout();this.setData({actor:null,message:'当前账号已退出，本机和云端车库保留'});}catch(e){this.setData({error:e.message});}},
 back(){wx.navigateBack();},
 onHide(){this.setData({password:'',passwordConfirm:'',token:'',invite_code:''});},onUnload(){this.pending=null;}
});
