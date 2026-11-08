'use strict';
// Syntax and local configuration checks only; this does not prove DNS, TLS or WeChat registration.
function validateNativeConfig(value){
 if(!value||typeof value!=='object'||Array.isArray(value))throw Error('原生配置格式无效');
 if(value.enabled===false){if(Object.keys(value).some(k=>k!=='enabled'))throw Error('关闭状态不应携带连接或凭据字段');return {enabled:false};}
 if(value.enabled!==true||!['fixture','platform'].includes(value.kind))throw Error('原生配置必须明确fixture或platform模式');
 const allowed=value.kind==='fixture'?['enabled','kind','origin','fixtureCode','fixtureKey']:['enabled','kind','origin'];
 if(Object.keys(value).some(k=>!allowed.includes(k)))throw Error('原生配置含未知字段；秘密只应留在服务端');
 if(value.kind==='fixture'){
  if(!/^http:\/\/127\.0\.0\.1:[1-9]\d{0,4}$/.test(value.origin)||Number(value.origin.split(':').pop())>65535||!/^fixture-code-[12]$/.test(value.fixtureCode)||!/^[\w-]{16,80}$/.test(value.fixtureKey))throw Error('fixture配置无效');
 }else{
  const m=typeof value.origin==='string'&&value.origin.match(/^https:\/\/([a-z0-9.-]+)(?::([1-9]\d{0,4}))?$/i);
  if(!m||m[1].length>253||!m[1].includes('.')||m[1].toLowerCase().endsWith('.localhost')||/^[\d.]+$/.test(m[1])||m[1].split('.').some(s=>!s||s.length>63||!/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/i.test(s))||(m[2]&&Number(m[2])>65535))throw Error('平台模式需要完整HTTPS域名，不接受IP、路径或查询参数');
 }
 return {...value};
}
module.exports={validateNativeConfig};
