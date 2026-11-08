'use strict';
const runtime=require('../../services/runtime');
const labels={login:'登录',register:'注册', 'resend-verification':'重发验证邮件','forgot-password':'找回密码','verify-email':'验证邮箱','reset-password':'重置密码','redeem-invitation':'兑换管理员邀请',reauth:'再次验证密码'};
Page({
 data:{moreOpen:false,mode:'login',title:'登录',email:'',password:'',passwordConfirm:'',token:'',invite_code:'',busy:false,actor:null,options:Object.entries(labels).map(([value,label])=>({value,label}))},
 onLoad(o={}){this.unloaded=false;try{const policy=runtime.policy();this.actions=policy.restricted?policy.actions:Object.keys(labels);this.setData({restricted:policy.restricted,registration:policy.registration===true});this.client=runtime.account();this.pending=this.client.pendingAuth?.();this.setData({actor:this.client.state().actor,recoverable:!!this.pending});this.unwatch=this.client.subscribe(s=>this.publish({actor:s.actor}));if(o.mode&&labels[o.mode])this.changeMode({detail:{value:o.mode}});}catch(e){this.setData({error:e.message});}},
 publish(value){if(!this.unloaded)this.setData(value);},
 input(e){if(['email','password','passwordConfirm','token','invite_code'].includes(e.currentTarget.dataset.key))this.setData({[e.currentTarget.dataset.key]:e.detail.value});},
 chooseMode(e){this.changeMode({detail:{value:e.currentTarget.dataset.mode}});},
 toggleMore(){this.setData({moreOpen:!this.data.moreOpen});},
 navigate(e){if(this.data.restricted){this.publish({error:'当前服务暂未开放此功能'});return;}wx.navigateTo({url:'/pages/'+e.currentTarget.dataset.page+'/'+e.currentTarget.dataset.page});},
 changeMode(e){if(this.data.busy)return;if(!(this.actions||(this.data.restricted?['login']:Object.keys(labels))).includes(e.detail.value)){this.publish({error:'当前服务仅开放隔离账号登录'});return;}if(this.pending){this.setData({error:'上次操作结果未确定，请先查询原操作，再切换表单',recoverable:true});return;}this.setData({mode:e.detail.value,title:labels[e.detail.value],password:'',passwordConfirm:'',token:'',invite_code:'',error:'',message:'',recoverable:false});},
 async submit(){if(this.data.busy||!this.client)return;if(!(this.actions||(this.data.restricted?['login']:Object.keys(labels))).includes(this.data.mode)){this.publish({error:'当前服务仅开放隔离账号登录'});return;}if(this.pending){this.setData({error:'请先查询上次操作结果，再提交新的操作'});return;}const action=this.data.mode;if(['register','reset-password'].includes(action)&&this.data.password!==this.data.passwordConfirm){this.setData({error:'两次密码不一致，请重新确认'});return;}this.setData({busy:true,error:'',message:''});
  let fields={};if(['register','login','resend-verification','forgot-password'].includes(action))fields.email=this.data.email;
  if(['register','login','reset-password','reauth'].includes(action))fields.password=this.data.password;
  if(['verify-email','reset-password'].includes(action))fields.token=this.data.token;
  if(this.data.registration&&action==='verify-email'){
   const prefix=runtime.origin()+'/#action=verify&token=',link=fields.token.trim();
   if(!link.startsWith(prefix)||!/^[-_a-zA-Z0-9]{43}$/.test(link.slice(prefix.length))){this.publish({busy:false,token:'',error:'请粘贴隔离收件箱里的完整验证链接'});return;}
   fields.token=link.slice(prefix.length);
  }
  if((action==='register'&&!this.data.registration)||action==='redeem-invitation')fields.invite_code=this.data.invite_code;
  try{const value=await this.client.auth(action,fields);this.pending=null;this.publish({actor:this.client.state().actor,message:value.message||(['login','reauth'].includes(action)?'登录成功，可返回主页使用账号车库':'操作已完成'),recoverable:false});}
  catch(e){this.pending=this.client.pendingAuth?.()||null;this.publish({error:e.message,recoverable:!!this.pending,retryAfterMs:e.retryAfterMs||0});}
  finally{fields=null;this.publish({busy:false,password:'',passwordConfirm:'',token:'',invite_code:''});}
 },
 async recover(){if(!this.pending||this.data.busy)return;this.publish({busy:true});try{const r=await this.client.recoverAuth(this.pending.key,this.pending.action);this.pending=this.client.pendingAuth?.()||null;this.publish({actor:this.client.state().actor,error:'',message:r.message||'原操作已核对',recoverable:!!this.pending});}catch(e){this.pending=this.client.pendingAuth?.()||null;this.publish({error:e.message,recoverable:!!this.pending,retryAfterMs:e.retryAfterMs||0});}finally{this.publish({busy:false});}},
 async logout(){if(this.data.restricted){this.publish({error:'当前只读验收未开放退出操作'});return;}if(this.data.busy)return;this.publish({busy:true});try{await this.client.logout();this.publish({actor:null,message:'当前账号已退出，本机和云端车库保留'});}catch(e){this.publish({error:e.message});}finally{this.publish({busy:false});}},
 back(){wx.navigateBack();},
 onHide(){this.setData({password:'',passwordConfirm:'',token:'',invite_code:''});},onUnload(){this.unloaded=true;if(this.unwatch)this.unwatch();this.pending=null;}
});
