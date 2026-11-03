'use strict';
// Scripted UI fixture, deliberately no real scores, candidates or solver.
function createMock() {
  const maps = Array.from({ length: 6 }, (_, i) => ({
    big: '联调区域' + (i + 1), small: '联调赛道' + (i + 1)
  }));
  function model(draft) {
    return {
      server: draft.server, version: 'mock-v1-' + draft.server,
      zones: draft.server === 'global' ? ['zone5'] : ['zone5', 'zone4'],
      tiers: draft.server === 'global' ? ['理论'] : ['理论', '高手', '普通', '自动'],
      maps,
      knownCarIds: ['联调车A','联调车B','联调车C'],
      cars: ['联调车A', '联调车B', '联调车C'].map(id => ({
        id, label: id, stars: draft.server === 'global' ? [6] : [3, 4, 5, 6],
        defaultStar: 6, ocAllowed: draft.server === 'global'
      })), routes: []
    };
  }
  return {
    mode: 'mock', model,
    async calculate(draft) {
      return { mock: true, schemes: [{ rows: draft.maps.map(map => ({
        map: map ? map.small : '', car: null, time: null
      })), total: null }] };
    },
    async recognize() {
      return { mock: true, server: 'cn', version: 'mock-v1-cn', slots: maps.slice(0, 5) };
    },
    async resume() {}, cancel() {}
  };
}
module.exports = { createMock };
