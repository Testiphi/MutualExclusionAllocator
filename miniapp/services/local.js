'use strict';
const { verifyLocalBundle } = require('../adapters/snapshot');
const {enrichModel}=require('../lib/garage_view');
function createLocalService(core, bundle) {
  const snapshots = verifyLocalBundle(bundle);
  const contexts = {}, known = {};
  for (const server of ['cn','global']) {
    const context = core.createSelectionContext(snapshots[server]); contexts[server] = context;
    const base = {schema:1,server,zone:'zone5',tier:'理论',maps:[null,null,null,null,null],cars:[],stars:{},oc:{},routes:{}};
    const initial = context.getModel(base);
    known[server] = [...new Set(initial.zones.flatMap(zone=>context.getModel({...base,zone}).cars.map(c=>c.id)))];
  }
  function context(draft) { if (!contexts[draft.server]) throw Error('无效服别'); return contexts[draft.server]; }
  return {
    mode:'local',
    model: draft=>({...enrichModel(context(draft).getModel(draft),snapshots[draft.server],draft,core),knownCarIds:known[draft.server]}),
    calculate: draft=>context(draft).calculate(draft),
    async recognize() { throw Error('原生识图接口尚未接入，请先手动选图'); },
    async resume() {}, cancel() {}
  };
}
module.exports = { createLocalService };
