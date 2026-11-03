'use strict';
// Create a local-only DevTools configuration. Existing configurations are never overwritten.
const fs=require('node:fs');
const path=require('node:path');
function setup(directory,appid){
  const target=path.join(directory,'project.config.json');
  if(fs.existsSync(target)) return {created:false,preserved:true};
  const config=JSON.parse(fs.readFileSync(path.join(directory,'project.config.example.json'),'utf8'));
  if(appid){
    if(!/^wx[0-9a-fA-F]{16}$/.test(appid)) throw new Error('RACEPICK_MINI_APP_ID must be a valid WeChat App ID');
    config.appid=appid;
  }
  fs.writeFileSync(target,JSON.stringify(config,null,2)+'\n',{flag:'wx',mode:0o600});
  return {created:true,localOnly:true};
}
module.exports={setup};
if(require.main===module){
  console.log(JSON.stringify(setup(path.resolve(__dirname,'../miniapp'),process.env.RACEPICK_MINI_APP_ID)));
}
