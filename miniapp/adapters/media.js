'use strict';
function createMedia(wx, {confirmUpload=false} = {}) {
  return {
    // Direct album-only image selection: no action sheet, camera or video entry.
    choose: () => new Promise((resolve, reject) => wx.chooseMedia({
      count: 1, mediaType: ['image'], sourceType: ['album'], sizeType: ['original'],
      success(result) {
        const f = result.tempFiles && result.tempFiles[0];
        if (!f || !f.tempFilePath || !Number.isFinite(f.size) || f.size <= 0) {
          reject(Error('未取得可用图片')); return;
        }
        if (f.size > 8 * 1024 * 1024) { reject(Error('图片超过8MiB')); return; }
        const image={path:f.tempFilePath,size:f.size};
        if(!confirmUpload){resolve(image);return;}
        if(typeof wx.showModal!=='function'){resolve(null);return;}
        wx.showModal({
          title:'确认发送截图',
          content:'所选截图将发送至 RacePick 服务，并由阿里云内容安全服务审核，通过后提取文字辅助填写。你也可以取消并手动填写。',
          confirmText:'同意发送',cancelText:'取消',
          success: choice=>resolve(choice.confirm?image:null),
          fail: ()=>resolve(null)
        });
      },
      fail(error) {
        if (/cancel/.test(error.errMsg || '')) resolve(null);
        else reject(Error('无法打开相册，可继续手动选图'));
      }
    }))
  };
}
module.exports = { createMedia };
