'use strict';
const binding=require('./account_readonly_binding.js');
const {verifyNativeSnapshot}=require('../adapters/snapshot');
const {sha256,utf8}=require('../adapters/hash');
const fail=code=>Object.assign(Error(code),{code});
function verifyHealth(value,writable=false,registrationDelivery){
 function match(actual,expected){return expected&&typeof expected==='object'?actual&&Object.keys(expected).every(k=>match(actual[k],expected[k])):actual===expected;}
 const expected=registrationDelivery?{...binding.health,delivery_id:registrationDelivery,registration:true}:writable?{...binding.health,cloud_writes:true}:binding.health;
 if(!match(value,expected))throw fail('ACCOUNT_DELIVERY_MISMATCH');
 return true;
}
function verifySnapshot(value,server,identity,fixedRuntime=binding.fixed_runtime){
 const result=verifyNativeSnapshot(value,server,identity);
 if(result.version!==fixedRuntime.snapshot_versions[server])throw fail('ACCOUNT_SNAPSHOT_VERSION_MISMATCH');
 for(const [name,file] of Object.entries(value.files)){
  const expected=fixedRuntime.files[name],bytes=utf8(file.text);
  if(!expected||bytes.length!==expected.bytes||sha256(bytes)!==expected.sha256)throw fail('ACCOUNT_SNAPSHOT_BYTES_MISMATCH');
 }
 if(server==='global'&&result.cars._meta.dataset_version!==fixedRuntime.global_dataset)throw fail('ACCOUNT_GLOBAL_DATASET_MISMATCH');
 return result;
}
function verifyProfile(value,server){
 if(!value||value.server!==server||value.storage!=='account'||value.remote_supported!==true||!Number.isInteger(value.revision)||value.revision<0||!Object.hasOwn(value,'profile'))throw fail('ACCOUNT_PROFILE_INVALID');
 const p=value.profile,object=v=>!!v&&typeof v==='object'&&!Array.isArray(v);
 if(!['cn','global'].includes(server)||!Number.isSafeInteger(value.revision)||
   (p===null?value.revision!==0:!object(p)||value.revision<1||!Array.isArray(p.cars)||
   p.cars.some(c=>typeof c!=='string'||!c||c.length>160)||new Set(p.cars).size!==p.cars.length||
   !object(p.stars)||Object.values(p.stars).some(n=>!Number.isInteger(n)||n<1||n>6)||
   Object.keys(p).some(k=>!['cars','stars',...(server==='global'?['ocMap']:[])].includes(k))||
   (server==='global'&&(!object(p.ocMap)||Object.values(p.ocMap).some(v=>typeof v!=='boolean')))))throw fail('ACCOUNT_PROFILE_INVALID');
 return value;
}
module.exports={binding,verifyHealth,verifySnapshot,verifyProfile};
