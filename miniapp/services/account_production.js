'use strict';

const files = ['cars.json','gauntlet_data.json','cars.global.json','gauntlet_data.global.json','global-data-manifest.json'];
const hasKeys = (value, keys) => !!value && typeof value === 'object' && !Array.isArray(value) &&
  Object.keys(value).sort().join() === [...keys].sort().join();

function validateProductionProfile(value) {
  const runtime = value.fixedRuntime;
  if (!hasKeys(value, ['enabled','mode','origin','planId','allowCloudWrites','fixedRuntime']) ||
      value.enabled !== true || value.mode !== 'production-a' || value.origin !== 'https://racepick.cn' || value.planId !== 'racepick-production-a-v1' ||
      typeof value.allowCloudWrites !== 'boolean' ||
      !hasKeys(runtime, ['snapshot_versions','files','global_dataset']) ||
      !hasKeys(runtime.snapshot_versions, ['cn','global']) ||
      !Object.values(runtime.snapshot_versions).every(v => typeof v === 'string' && /^[a-f0-9]{32,64}$/.test(v)) ||
      !/^[a-f0-9]{64}$/.test(runtime.global_dataset) || !hasKeys(runtime.files, files) ||
      !Object.values(runtime.files).every(f => hasKeys(f, ['sha256','bytes']) && /^[a-f0-9]{64}$/.test(f.sha256) && Number.isSafeInteger(f.bytes) && f.bytes > 0)) {
    throw Error('正式账号配置缺少已固定的双服快照');
  }
  return value;
}

function verifyProductionHealth(health, versions, writing) {
  const account = health?.mini_account;
  if (health?.mode !== 'production' || health.status !== 'ok' || health.global_profile_schema !== 1 ||
      health.score_version !== versions.cn || health.global_score_version !== versions.global ||
      account?.mode !== 'formal-a' || account.enabled !== true || typeof account.cloud_writes !== 'boolean' ||
      (writing && !account.cloud_writes)) {
    throw Error('正式账号入口或云写开关尚未就绪');
  }
}

module.exports = {validateProductionProfile, verifyProductionHealth};
