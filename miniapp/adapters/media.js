'use strict';
function createMedia(wx) {
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
        resolve({ path: f.tempFilePath, size: f.size });
      },
      fail(error) {
        if (/cancel/.test(error.errMsg || '')) resolve(null);
        else reject(Error('无法打开相册，可继续手动选图'));
      }
    }))
  };
}
module.exports = { createMedia };
