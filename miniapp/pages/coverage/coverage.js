'use strict';
const ui=require('../../lib/feature_page');
const query=x=>Object.entries(x).map(([k,v])=>k+'='+encodeURIComponent(v)).join('&');
Page({data:{server:'cn',zone:'五区',tier:'理论',route:'normal',big:'all',stars:'all',q:'',offset:0,oc:false,gaps:false,star_map:{},busy:false,
 servers:ui.options(['cn','global'],{cn:'国服',global:'国际服'}),zones:ui.options(['五区','四区']),tiers:ui.options(['理论','高手']),routes:ui.options(['normal','special'],{normal:'普通跑法',special:'特殊跑法'}),starOptions:ui.options(['all','1','2','3','4','5','6'],{all:'全部星级'}),bigOptions:[{value:'all',label:'全部地图'}]},
 onLoad(o){try{ui.install(this);this.setData({server:o.server==='global'?'global':'cn'});this.load();}catch(e){this.setData({error:e.message});}},
 async onShow(){if(this.client)try{await this.client.refresh();if(!this.data.matrix&&!this.data.busy)this.load();}catch(e){this.setData({error:e.message});}},
 change(e){if(this.data.busy)return;const key=e.currentTarget.dataset.key;this.setData({[key]:e.detail.value,offset:0});if(key==='server')this.setData({big:'all',stars:'all',star_map:{},oc:false});if(this.data.server==='global')this.setData({zone:'五区',tier:'理论'});this.load();},
 input(e){this.setData({q:e.detail.value});},toggle(e){if(this.data.busy)return;this.setData({[e.currentTarget.dataset.key]:!this.data[e.currentTarget.dataset.key],offset:0});this.load();},
 load(){return ui.run(this,()=>this.fetchMatrix());},
 async fetchMatrix(){const d=this.data,body={server:d.server,zone:d.zone,tier:d.tier,route:d.route,big:d.big,stars:d.stars,q:d.q,offset:d.offset,oc:d.server==='global'&&d.oc,gaps:d.gaps,star_map:d.star_map};
  const matrix=await this.client.call('/coverage/view',{method:'POST',data:body});
  const sheets=body.server==='global'?[{zone:'五区',tier:'理论',label:'五区理论'}]:[{zone:'五区',tier:'理论',label:'五区理论'},{zone:'五区',tier:'高手',label:'五区高手'},{zone:'四区',tier:'理论',label:'四区理论'},{zone:'四区',tier:'高手',label:'四区高手'}];const rows=matrix.rows.map((r,i)=>({...r,index:i,cells:r.cells.map((c,j)=>({...c,index:j,display:c.status==='empty'?'—':c.value===null?'未解锁':Number(c.value).toFixed(2)}))}));
  this.setData({chosenMapName:matrix.maps.find(m=>m.id===matrix.access.chosen)?.name||'',sheets,matrix:{...matrix,rows},columns:matrix.columns.map(c=>({...c,starOptions:(c.star_options||[]).map(n=>({value:n,label:'★'+n}))})),bigOptions:[{value:'all',label:'全部地图'},...matrix.maps.map(m=>({value:m.id,label:m.name}))],picked:null});
 },
 columnStars(e){this.setData({['star_map.'+e.currentTarget.dataset.car]:e.detail.value});this.load();},
 pick(e){const row=this.data.matrix.rows[Number(e.currentTarget.dataset.row)],cell=row.cells[Number(e.currentTarget.dataset.column)];this.setData({picked:{...cell,map_id:row.map_id,map:row.big+' / '+row.small,car:this.data.columns[Number(e.currentTarget.dataset.column)].title}});},
 toggleProgress(){this.setData({progressOpen:!this.data.progressOpen});},
 selectSheet(e){if(this.data.busy)return;const sheet=this.data.sheets[Number(e.currentTarget.dataset.index)];this.setData({zone:sheet.zone,tier:sheet.tier,offset:0,star_map:{},stars:'all'});return this.load();},
 page(e){if(this.data.busy)return;const next=Math.max(0,this.data.offset+Number(e.currentTarget.dataset.delta)*48);if(next<this.data.matrix.column_total){this.setData({offset:next});this.load();}},
 choose(){if(!this.data.picked||this.data.busy)return;const generation=this.client.generation(),server=this.data.server,map_id=this.data.picked.map_id;wx.showModal({title:'解锁所选地图',content:'此服一级权益的地图首次选择后不能自行更改，确认选择？',success:r=>{if(!r.confirm)return;if(generation!==this.client.generation()||server!==this.data.server||map_id!==this.data.picked?.map_id){this.setData({error:'账号、服别或地图已变化，未执行旧选择'});return;}void ui.run(this,async()=>{await this.client.call('/coverage/choice',{method:'POST',data:{server,map_id}});if(generation!==this.client.generation()||server!==this.data.server)return;await this.fetchMatrix();this.setData({message:'地图已选择，表格已按当前权益更新'});});}});},
 contribute(){if(!this.data.picked)return;getApp().submissionTarget={...this.data.picked.target};wx.navigateTo({url:'/pages/submissions/submissions?server='+this.data.server});},
 recover(){return ui.recover(this);},onUnload(){ui.cleanup(this);}
});
