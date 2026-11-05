'use strict';
const binding=require('./account_readonly_binding.js');
const {verifyNativeSnapshot}=require('../adapters/snapshot');
const {sha256,utf8}=require('../adapters/hash');
const fail=code=>Object.assign(Error(code),{code});
function verifyHealth(value){
 function match(actual,expected){return expected&&typeof expected==='object'?actual&&Object.keys(expected).every(k=>match(actual[k],expected[k])):actual===expected;}
 if(!match(value,binding.health))throw fail('ACCOUNT_DELIVERY_MISMATCH');
 return true;
}
function verifySnapshot(value,server,identity){
 const result=verifyNativeSnapshot(value,server,identity);
 if(result.version!==binding.fixed_runtime.snapshot_versions[server])throw fail('ACCOUNT_SNAPSHOT_VERSION_MISMATCH');
 for(const [name,file] of Object.entries(value.files)){
  const expected=binding.fixed_runtime.files[name],bytes=utf8(file.text);
  if(!expected||bytes.length!==expected.bytes||sha256(bytes)!==expected.sha256)throw fail('ACCOUNT_SNAPSHOT_BYTES_MISMATCH');
 }
 if(server==='global'&&result.cars._meta.dataset_version!==binding.fixed_runtime.global_dataset)throw fail('ACCOUNT_GLOBAL_DATASET_MISMATCH');
 return result;
}
function verifyProfile(value,server){
 if(!value||value.server!==server||value.storage!=='account'||value.remote_supported!==true||!Number.isInteger(value.revision)||value.revision<0||!Object.hasOwn(value,'profile'))throw fail('ACCOUNT_PROFILE_INVALID');
 const p=value.profile;
 if(p!==null&&(!p||!Array.isArray(p.cars)||!p.stars||typeof p.stars!=='object'||Array.isArray(p.stars)||
   (server==='global'&&(!p.ocMap||typeof p.ocMap!=='object'||Array.isArray(p.ocMap)||Object.values(p.ocMap).some(v=>typeof v!=='boolean')))))throw fail('ACCOUNT_PROFILE_INVALID');
 return value;
}
module.exports={binding,verifyHealth,verifySnapshot,verifyProfile};
