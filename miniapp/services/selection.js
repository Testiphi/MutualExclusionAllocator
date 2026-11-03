'use strict';
// The website branch owns the implementation of this port. No second ruleset.
function createSelectionService(core, snapshot) {
  if (!core || typeof core.createSelectionContext !== 'function') {
    throw Error('等待网站分支提供共享候选模块');
  }
  const context = core.createSelectionContext(snapshot);
  return {
    mode: 'native',
    model: draft => context.getModel(draft),
    calculate: draft => context.calculate(draft),
    async recognize() { throw Error('原生识图接口尚未接入'); },
    async resume() {}, cancel() {}
  };
}
module.exports = { createSelectionService };
