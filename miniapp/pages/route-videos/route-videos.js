'use strict';
const build = require('../../generated/build-info');
const videos = require('../../services/route_videos');

Page({
  data: {items: [], busy: false, error: ''},
  onLoad(options) {
    if (!build.routeVideoLab) return this.setData({error: '跑法视频服务暂未开放'});
    try {
      const scope = JSON.parse(decodeURIComponent(options.scope));
      if (!['cn', 'global'].includes(scope.server) || !['四区', '五区'].includes(scope.zone) ||
          !['理论', '高手', '普通', '自动'].includes(scope.tier) ||
          !['big', 'small', 'car'].every(key => typeof scope[key] === 'string' && scope[key]) ||
          !Array.isArray(scope.routes)) throw Error('invalid scope');
      this.scope = scope;
      this.setData({heading: scope.small + ' · ' + scope.car});
      return this.retry();
    } catch (_) {
      this.setData({error: '视频目标无效，请返回重新选择'});
    }
  },
  async retry() {
    if (!this.scope || this.data.busy) return;
    this.setData({busy: true, error: '', items: []});
    try {
      const items = await videos.load(wx, this.scope, build.routeVideoOrigin);
      if (!this.unloaded) this.setData({items});
    } catch (error) {
      if (!this.unloaded) this.setData({error: error.message});
    } finally {
      if (!this.unloaded) this.setData({busy: false});
    }
  },
  openBili(event) {
    const item=this.data.items[Number(event.currentTarget.dataset.index)];
    if(!build.routeVideoLab||!(item?.aid||item?.shortLink))return;
    const failed=()=>wx.showToast({title:'跳转失败，请复制链接',icon:'none'});
    if(typeof wx.navigateToMiniProgram!=='function')return failed();
    if(item.shortLink)return wx.navigateToMiniProgram({shortLink:item.shortLink,fail:failed});
    const path='pages/video/video?avid='+item.aid+(item.part?'&p='+item.part:'')+(item.start?'&t='+item.start:'');
    wx.navigateToMiniProgram({appId:'wx7564fd5313d24844',path,fail:failed});
  },
  copy(event) {
    const item = this.data.items[Number(event.currentTarget.dataset.index)];
    if (item) wx.setClipboardData({
      data: item.url,
      fail: () => wx.showToast({title: '复制失败，请重试', icon: 'none'}),
    });
  },
  onUnload() { this.unloaded = true; },
});
