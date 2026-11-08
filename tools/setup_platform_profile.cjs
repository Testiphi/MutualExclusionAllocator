'use strict';
const fs=require('node:fs'),path=require('node:path');
function setup(directory){const target=path.join(directory,'platform.profile.local.json');if(fs.existsSync(target))return {created:false,preserved:true};const bytes=fs.readFileSync(path.join(directory,'platform.profile.example.json'));fs.writeFileSync(target,bytes,{flag:'wx',mode:0o600});return {created:true,localOnly:true,enabled:false};}
module.exports={setup};if(require.main===module)console.log(JSON.stringify(setup(path.resolve(__dirname,'../miniapp'))));
