'use strict';
const {options}=require('../../lib/feature_page');
const scores=require('../../services/public_scores');
const videos=require('../../services/route_videos');

const servers=options(['cn','global'],{cn:'国服',global:'国际服'});
const runs=options(['normal','special'],{normal:'普通跑法',special:'特殊跑法'});
const allMaps=[{value:'all',label:'全部地图'}];
const sheets=server=>(server==='global'?['五区']:['五区','四区']).flatMap(zone=>
  (server==='global'?['理论']:['理论','高手']).map(tier=>({zone,tier,label:zone+' · '+tier}))
);

module.exports={
  startPublic(o) {
    const server=o?.server==='global'?'global':'cn';
    this.scoreChoices=new Map();
    this.setData({publicMode:'scores',scoreServer:server,referenceServer:server,publicServers:servers,
      publicRuns:runs,scoreZone:'五区',scoreTier:'理论',scoreRun:'normal',scoreMap:'all',
      scoreMaps:allMaps,scoreSearch:'',scoreOc:false,scoreSheets:sheets(server),
      mapQuery:'',carQuery:'',referenceOnly:false,publicOffset:0});
    return this.loadPublic();
  },
  publicBack() {
    if(getCurrentPages().length>1)wx.navigateBack();
    else wx.reLaunch({url:'/pages/home/home'});
  },
  publicTab(e) {
    const mode=e.currentTarget.dataset.mode;
    if(mode===this.data.publicMode)return;
    this.setData({publicMode:mode,publicOffset:0});
    if(mode==='videos'&&!this.referenceOpened){
      this.referenceOpened=true;
      this.setData({referenceServer:this.data.scoreServer});
    }
    return this.loadPublic();
  },
  publicScope() {
    const d=this.data;
    return {server:d.scoreServer,zone:d.scoreZone,tier:d.scoreTier,big:d.scoreMap,route:d.scoreRun,
      q:d.scoreSearch.trim(),offset:d.publicOffset,oc:d.scoreServer==='global'&&d.scoreOc};
  },
  publicStars() {
    const key=this.data.scoreServer+':'+this.data.scoreZone;
    if(!this.scoreChoices.has(key))this.scoreChoices.set(key,new Map());
    return this.scoreChoices.get(key);
  },
  publicFilter(e) {
    const key=e.currentTarget.dataset.key,value=e.detail.value;
    if(!['scoreServer','scoreRun','scoreMap','referenceServer'].includes(key)||value===this.data[key])return;
    const changes={[key]:value,publicOffset:0};
    if(key==='scoreServer')Object.assign(changes,{scoreZone:'五区',scoreTier:'理论',scoreMap:'all',
      scoreMaps:allMaps,scoreOc:false,scoreSheets:sheets(value)});
    this.setData(changes);
    return this.loadPublic();
  },
  publicSearch(e) {
    const key=e.currentTarget.dataset.key;
    this.setData({[key]:e.detail.value});
    if(key!=='scoreSearch'){
      this.setData({publicOffset:0});
      this.renderReference();
    }
  },
  loadPublicRetry() { return this.loadPublic(); },
  publicRefresh() {
    this.setData({publicOffset:0});
    return this.loadPublic();
  },
  publicToggle(e) {
    const key=e.currentTarget.dataset.key;
    this.setData({[key]:e.detail.value.length>0,publicOffset:0});
    if(key==='referenceOnly')this.renderReference();
    else return this.loadPublic();
  },
  publicSelectSheet(e) {
    const sheet=this.data.scoreSheets[Number(e.currentTarget.dataset.index)];
    if(!sheet || (sheet.zone===this.data.scoreZone&&sheet.tier===this.data.scoreTier))return;
    this.setData({scoreZone:sheet.zone,scoreTier:sheet.tier,publicOffset:0});
    return this.loadPublic();
  },
  publicSelectStar(e) {
    this.publicStars().set(e.currentTarget.dataset.car,e.detail.value);
    return this.loadPublic(true);
  },
  publicPage(e) {
    const sheet=this.data.publicSheet;
    if(!sheet||this.data.publicBusy)return;
    const offset=sheet.offset+Number(e.currentTarget.dataset.delta)*sheet.limit;
    if(offset<0||offset>=sheet.total)return;
    this.setData({publicOffset:offset});
    if(this.data.publicMode==='videos')this.renderReference();
    else return this.loadPublic();
  },
  stopPublic() {
    const pending=this.publicRequests;
    this.publicRequests=null;
    if(pending)pending.cancelled=true;
    for(const task of pending||[])task?.abort();
  },
  async loadPublic(keepSheet=false) {
    this.stopPublic();
    const pending=this.publicRequests=[];
    const scope=this.publicScope(),mode=this.data.publicMode;
    if(mode==='videos')this.referenceMatrix=null;
    this.setData({publicBusy:true,publicError:'',...(!keepSheet?{publicSheet:null}:{})});
    try {
      if(mode==='videos'){
        const server=this.data.referenceServer;
        const matrix=await scores.readReference(wx,scope.server===server?
          {server,zone:scope.zone,tier:scope.tier,route:scope.route,oc:scope.oc}:{server},pending);
        if(this.publicRequests!==pending)return;
        this.referenceMatrix=matrix;
        this.renderReference();
      }else{
        const result=await scores.readScores(wx,scope,new Map(this.publicStars()),pending);
        if(this.publicRequests!==pending)return;
        this.setData({publicSheet:scores.projectScores(result),scoreMaps:[...allMaps,...result.maps.map(({id,name})=>({value:id,label:name}))]});
      }
    }catch(error){
      if(this.publicRequests===pending)this.setData({publicError:error.message,publicSheet:null});
    }finally{
      if(this.publicRequests===pending){
        this.publicRequests=null;
        this.setData({publicBusy:false});
      }
    }
  },
  renderReference() {
    if(!this.referenceMatrix)return;
    const d=this.data;
    const sheet=scores.projectReference(this.referenceMatrix,
      {mapQuery:d.mapQuery,carQuery:d.carQuery,only:d.referenceOnly,offset:d.publicOffset});
    this.setData({publicSheet:sheet,publicOffset:sheet.offset});
  },
  publicOpenVideos(e) {
    if(this.data.publicMode!=='videos')return;
    const {row,car}=e.currentTarget.dataset;
    const map=this.data.publicSheet?.rows[row];
    if(!map?.cells.some(cell=>cell.id===car&&cell.text))return;
    videos.open(wx,{server:this.data.referenceServer,big:map.big,small:map.small,car,reference:true});
  }
};

