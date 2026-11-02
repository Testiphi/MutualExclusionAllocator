'use strict';
const { createController } = require('../../lib/controller');
const { createStorage } = require('../../adapters/storage');
const { createMedia } = require('../../adapters/media');
const { createMock } = require('../../services/mock');

Page({
  data: { garageOpen: false, query: '', rows: [], cars: [], schemes: [], slotRows: [] },
  onLoad() {
    // Deliberately no native service configuration until the contract is agreed.
    this.controller = createController({ service: createMock(), storage: createStorage(wx, 'mock'),
      media: createMedia(wx), render: state => { this.state = state; this.updateView(); } });
  },
  updateView() {
    const s = this.state, d = s.draft, m = s.model;
    const bigs = [...new Set(m.maps.map(x => x.big))];
    const row = (map, index) => {
      const big = map && map.big || '', small = map && map.small || '';
      const options = m.maps.filter(x => x.big === big).map(x => x.small);
      return { index, big, small, bigs: ['选择大地图'].concat(bigs),
        bigIndex: bigs.indexOf(big) + 1, smalls: ['选择小地图'].concat(options),
        smallIndex: options.indexOf(small) + 1 };
    };
    const q = (this.data.query || '').trim().toLowerCase();
    const cars = m.cars.filter(x => !q || (x.label + ' ' + x.id).toLowerCase().includes(q))
      .map(x => ({ ...x, selected: d.cars.includes(x.id), starIndex: x.stars.indexOf(d.stars[x.id]),
        oc: d.oc[x.id] === true }));
    this.setData({ server: d.server, mode: s.mode, error: s.error, busy: s.busy,
      dirty: s.dirty, image: s.image, hasPending: !!s.pending,
      selectedCount: d.cars.length, zones: m.zones.map(x => x === 'zone4' ? '四区' : '五区'),
      zoneIndex: m.zones.indexOf(d.zone), tiers: m.tiers, tierIndex: m.tiers.indexOf(d.tier),
      rows: d.maps.map(row), cars, slotRows: s.pending ? s.pending.map(row) : [],
      schemes: s.result ? s.result.schemes.map((scheme, index) => ({
        index, totalText: scheme.total == null ? '—' : scheme.total.toFixed(3) + '秒',
        rows: scheme.rows.map((r, i) => ({ index: i, map: r.map || '未选地图',
          car: r.car || '未分配', timeText: r.time == null ? '—' : r.time.toFixed(3) + '秒' }))
      })) : [] });
  },
  onShow() { if (this.controller) this.controller.show(); },
  onHide() { if (this.controller) this.controller.hide(); },
  onUnload() { if (this.controller) this.controller.destroy(); },
  switchServer(e) { this.controller.switchServer(e.currentTarget.dataset.server); },
  selectZone(e) { this.controller.setMode(this.state.model.zones[Number(e.detail.value)], this.state.draft.tier); },
  selectTier(e) { this.controller.setMode(this.state.draft.zone, this.state.model.tiers[Number(e.detail.value)]); },
  selectMap(e) {
    const { index, field, pending } = e.currentTarget.dataset;
    const target = pending ? this.state.pending : this.state.draft.maps;
    const previous = target[index];
    let map = null;
    if (field === 'big') {
      const bigs = [...new Set(this.state.model.maps.map(x => x.big))];
      const big = bigs[Number(e.detail.value) - 1];
      // A big selection is kept until its small map is selected.
      if (big) map = { big, small: '' };
    } else if (previous) {
      const options = this.state.model.maps.filter(x => x.big === previous.big);
      map = options[Number(e.detail.value) - 1] || { big: previous.big, small: '' };
    }
    if (pending) this.controller.correctSlot(Number(index), map);
    else this.controller.setMap(Number(index), map);
  },
  toggleGarage() { this.setData({ garageOpen: !this.data.garageOpen }); },
  search(e) { this.setData({ query: e.detail.value }); this.updateView(); },
  toggleCar(e) {
    const id = e.currentTarget.dataset.id;
    this.controller.setCar(id, !this.state.draft.cars.includes(id));
  },
  selectStars(e) {
    const id = e.currentTarget.dataset.id, car = this.state.model.cars.find(x => x.id === id);
    this.controller.setStars(id, car.stars[Number(e.detail.value)]);
  },
  toggleOc(e) { this.controller.setOc(e.currentTarget.dataset.id, e.detail.value); },
  save() { this.controller.save(); }, restore() { this.controller.restore(); },
  compute() { this.controller.compute(); }, chooseImage() { this.controller.chooseImage(); },
  recognize() { this.controller.recognize(); }, applyRecognition() { this.controller.applyRecognition(); },
  cancelRecognition() { this.controller.cancelRecognition(); }
});
