'use strict';
const {createOcrProbe}=require('./ocr_probe');
function createPhoneOcrPage(wx,{config,expected,permission,probeId}){
 if(!permission.phoneOnly)throw Error('手机检查工程配置无效');
 return {data:{phoneOnly:true,buildId:probeId,busy:false,view:null,diagnostic:'',safeReport:'',dropdown:null,message:'手机单次相册验收：先取消/拒绝，再选原图；不会自动上传'},
  onLoad(){this.actionEpoch=0;this.probe=createOcrProbe(wx,config,expected,permission);this.refresh();},
  refresh(){if(this.unloaded||!this.probe)return;const view=this.probe.report(),{maps,applied,pending,...safe}=view;this.setData({view,safeReport:JSON.stringify({buildId:probeId,...safe,pending,applied},null,2)});},
  async action(name){if(this.data.busy)return;const ticket=++this.actionEpoch;this.setData({busy:true,diagnostic:''});try{await this.probe[name]();if(!this.unloaded&&ticket===this.actionEpoch)this.setData({message:name==='connect'?'已核对固定快照与目录，请按步骤检查相册':'操作完成，识别结果需确认'});}catch(e){if(!this.unloaded&&ticket===this.actionEpoch)this.setData({diagnostic:e.safetyCode||e.code||'REQUEST_NOT_COMPLETED',message:'本次未完成，保留手选；不再次上传'});}finally{if(!this.unloaded&&ticket===this.actionEpoch){this.setData({busy:false});this.refresh();}}},
  connect(){return this.action('connect');},recognize(){return this.action('recognize');},resume(){return this.action('resume');},confirm(){return this.action('confirm');},
  async choose(){if(this.data.busy)return;this.setData({diagnostic:''});try{await this.probe.choose();}catch(e){if(!this.unloaded)this.setData({diagnostic:e.code||'ALBUM_NOT_AVAILABLE'});}finally{this.refresh();}},
  cancel(){if(this.data.busy)return;this.probe.cancel();this.refresh();},consent(e){this.probe.setConsent(e.detail.value.length>0);this.refresh();},
  open(e){if(this.data.busy)return;this.setData({dropdown:{index:Number(e.currentTarget.dataset.index),pending:e.currentTarget.dataset.pending==='yes'}});},
  pick(e){const d=this.data.dropdown;if(!d)return;try{this.probe.setMap(d.index,this.data.view.maps[Number(e.currentTarget.dataset.map)],d.pending);this.setData({dropdown:null,diagnostic:''});}catch(err){this.setData({diagnostic:err.code||'MAP_INVALID'});}this.refresh();},close(){this.setData({dropdown:null});},
  onHide(){this.actionEpoch++;this.probe.hide();this.setData({busy:false,dropdown:null});this.refresh();},onShow(){if(this.probe){this.probe.show();this.refresh();}},onUnload(){this.unloaded=true;this.actionEpoch++;if(this.probe)this.probe.dispose();}
 };
}
module.exports={createPhoneOcrPage};
