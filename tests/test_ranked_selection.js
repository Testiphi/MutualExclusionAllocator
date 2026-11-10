'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {performance} = require('node:perf_hooks');
const allocator = require('../allocator');
const core = require('../selection_core');

const dominates = (a, b) => a.every((value, i) => value <= b[i]) && a.some((value, i) => value < b[i]);

function candidate(entries) {
    return {
        groups: entries.map(([car]) => [car]),
        carToPriority: new Map(entries.map(([car, , priority], i) => [car, priority ?? i])),
        times: new Map(entries.map(([car, time]) => [car, time])),
    };
}

// Exhaustive slot-order enumeration, including empty branches. Fixtures use millisecond scores.
function exhaustive(maps, owned, limit) {
    const all = [];
    function visit(assignment, vector, used, sum, timed) {
        const map = maps[assignment.length];
        if (!map) {
            all.push({assignment, vector, sum, timed, coverage: used.size, order: all.length});
            return;
        }
        visit([...assignment, null], [...vector, 99], used, sum, false);
        for (const car of map.groups.flat()) {
            if (used.has(car) || !owned.has(car)) continue;
            const time = map.times.get(car);
            const valid = Number.isFinite(time) && time > 0;
            visit([...assignment, car], [...vector, map.carToPriority.get(car)], new Set([...used, car]),
                sum + (valid ? Math.round(time * 1000) : 0), timed && valid);
        }
    }
    visit([], [], new Set(), 0, true);
    const hasTimed = maps.length === 5 && all.some(scheme => scheme.timed);
    const sum = vector => vector.reduce((a, b) => a + b, 0);
    const coverage = Math.max(...all.map(item => item.coverage));
    const eligible = hasTimed ? all.filter(scheme => scheme.timed)
        : all.filter(scheme => scheme.coverage === coverage);
    return eligible.filter(scheme => !eligible.some(other => dominates(other.vector, scheme.vector))).sort((a, b) => {
        const primary = (hasTimed ? a.sum - b.sum : 0) || sum(a.vector) - sum(b.vector);
        if (primary) return primary;
        for (let i = 0; i < maps.length; i++) if (a.vector[i] !== b.vector[i]) return a.vector[i] - b.vector[i];
        return a.order - b.order;
    }).slice(0, limit).map(({assignment, vector}) => ({assignment, vector}));
}
test('ranked solver matches exhaustive search across timing, exact ties, coverage and conflicts', () => {
    const owned = new Set('ABCDEFG');
    const tail = [[['E', 20]], [['F', 20]], [['G', 20]]];
    const opposite = [[['A', 20], ['B', 20.001]], [['A', 20], ['C', 20.01]], ...tail];
    assert.deepEqual(allocator.generateRankedSchemes(opposite.map(candidate), owned, 25, 99)[0].assignment,
        ['B', 'A', 'E', 'F', 'G']);
    assert.deepEqual(allocator.generateParetoSchemes(opposite.map(candidate), owned, 25, 99)[0].assignment,
        ['A', 'C', 'E', 'F', 'G']);
    const subMillisecond = [[['A', 20], ['B', 20.00001]], [['A', 20], ['C', 20.00002]], ...tail];
    assert.equal(allocator.generateRankedSchemes(subMillisecond.map(candidate), owned, 1, 99)[0].assignment[0], 'B');
    const cutoff = Array.from({length: 5}, (_, slot) =>
        [...'ABCDE'].map((car, rank) => [car, 20 + rank * (slot === 4 ? 10 : 1)]));
    const oldTop = allocator.generateParetoSchemes(cutoff.map(candidate), owned, 25, 99);
    const newFirst = allocator.generateRankedSchemes(cutoff.map(candidate), owned, 25, 99)[0];
    assert.deepEqual(newFirst.assignment, ['B', 'C', 'D', 'E', 'A']);
    assert.ok(!oldTop.some(scheme => scheme.assignment.join() === newFirst.assignment.join()));
    const fixtures = [opposite,
        cutoff,
        [[['A', 20.1], ['B', 20.2]], [['A', 20.2], ['C', 20.3]], ...tail],
        [[['A', 20, 0], ['B', 20, 0]], [['C', 20]], ...tail],
        [[['A', 20], ['B', null]], [['A', 20], ['C', 22]], ...tail],
        [[['B', null]], [['A', 20]], ...tail],
        [[['A', 20]], [['A', 21]], ...tail],
        [[['A', null]], [['B', 20]], []]];
    let state = 60291;
    const next = n => ((state = (Math.imul(state, 1664525) + 1013904223) >>> 0) % n);
    for (let i = 0; i < 120; i++) fixtures.push(Array.from({length: 1 + next(5)}, () =>
        [...owned].filter(() => next(7) < 3).map(car => [car, [null, 20.001, 20.003, 20.008][next(4)], next(4)])));
    for (const fixture of fixtures) {
        const maps = fixture.map(candidate);
        for (const limit of [1, 3, 25]) {
            assert.deepEqual(allocator.generateRankedSchemes(maps, owned, limit, 99), exhaustive(maps, owned, limit));
        }
    }
});

const root = path.join(__dirname, '..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
const names = ['cars.json', 'gauntlet_data.json', 'cars.global.json', 'gauntlet_data.global.json', 'global-data-manifest.json'];
const files = Object.fromEntries(names.map(name => [name, read(name)]));
const bundle = {kind: 'local-unfrozen', files, hashes: Object.fromEntries(names.map(name => [name,
    {bytes: Buffer.byteLength(files[name]), sha256: crypto.createHash('sha256').update(files[name]).digest('hex')}]))};

function webEntry(cars, data, draft) {
    const inline = read('index.html').match(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/)[1];
    const entry = inline.replace('initApp();', [
        'RACE_DATA = data; carStats = Object.fromEntries(cars.cars.map(car => [car.title, car]));',
        'currentTier = draft.tier; currentZone = draft.zone; starsMap = draft.stars; ocMap = draft.oc;',
        'specialRouteEnabled = {...draft.routes}; selectedCars = new Set(draft.cars);',
        'for (const [key, banned] of Object.entries(draft.mapBans || {})) mapBans.set(key, new Set(banned));',
        'buildCarRules(); buildMapIndex();',
        'getCurrentValidMaps = () => draft.maps.flatMap((map, originalIndex) => map ? [{...map, originalIndex}] : []);',
        'renderTopCars = () => {}; renderResultGuidance = () => {}; computationError = error => { throw error; };',
        'let result; updateUIWithSchemes = schemes => { result = schemes; }; computeAndDisplay();',
        'Object.assign(out, {result, score: (map, car) => getCarScore(map.big, map.small, car, currentZone)});',
    ].join('\n'));
    const sources = ['app_state.js', 'allocator.js', 'race_scores.js', 'selection_core.js', 'home_presenter.js'].map(read);
    const document = {getElementById: () => ({classList: {add() {}, remove() {}}})};
    const out = {};
    new Function('document', 'APP_CONFIG', 'cars', 'data', 'draft', 'requestAnimationFrame', 'setTimeout', 'globalThis', 'out',
        [...sources, entry].join('\n;\n'))(document, {server: draft.server, storageKeys: {}}, cars, data, draft,
        f => f(), f => f(), {RACEPICK_SERVER: draft.server}, out);
    return out;
}

test('the five reported maps exclude the dominated sf90 substitution', t => {
    const cars = JSON.parse(files['cars.json']);
    const data = JSON.parse(files['gauntlet_data.json']);
    const shared = core.createSelectionCore({cars, data});
    const maps = ['偏僻小道', '乐园追逐', '城市狂飙', '山野小路', '凌云狂飙'].map(small => {
        const track = data.tracks.find(track => track.小地图 === small);
        return {big: track.大地图, small};
    });
    const owned = ['r兔', 'sf90', 'f5r', '恶魔', '玻璃', '杰皇'];
    const draft = {schema: 1, server: 'cn', zone: 'zone5', tier: '理论', maps, cars: owned, stars: {}, oc: {}, routes: {}};
    const candidates = shared.prepareMapCandidates({maps, zone: draft.zone, tier: draft.tier}, true);
    const winner = ['r兔', ...owned.slice(2)];
    const loser = ['sf90', ...owned.slice(2)];
    const vector = assignment => assignment.map((car, i) => candidates[i].carToPriority.get(car));
    assert.ok(dominates(vector(winner), vector(loser)));
    const {result} = webEntry(cars, data, draft);
    assert.ok(result.some(scheme => scheme.assignment.join() === winner.join()));
    assert.ok(!result.some(scheme => scheme.assignment.join() === loser.join()));
    t.diagnostic(`screenshot candidate vectors ${vector(winner)} vs ${vector(loser)}`);
});

test('real website recommendation and generated mini-program local service agree', t => {
    const manifest = path.join(root, 'miniapp/shared/source.json');
    if (!fs.existsSync(manifest) || require(manifest).files['allocator.js'].source !== 'uncommitted-local-worktree') {
        t.skip('Generate the mini-program with node tools/prepare_miniapp.cjs --local-selection-preview');
        return;
    }
    const generated = require(manifest);
    for (const name of ['allocator.js', 'selection_core.js']) {
        assert.equal(generated.files[name].sha256, crypto.createHash('sha256').update(read(name)).digest('hex'));
    }
    const mini = require('../miniapp/services/local').createLocalService(require('../miniapp/shared/selection_core'), bundle);
    let checked = 0;
    for (const server of ['cn', 'global']) {
        const cars = JSON.parse(files[server === 'cn' ? 'cars.json' : 'cars.global.json']);
        const data = JSON.parse(files[server === 'cn' ? 'gauntlet_data.json' : 'gauntlet_data.global.json']);
        const shared = core.createSelectionCore({cars, data, server});
        const allMaps = data.tracks.map(track => ({big: track.大地图, small: track.小地图}));
        if (server === 'cn') {
            const jump = data.tracks.find(track => track.五区?.理论?.some(entry => entry.sc_type === '跳图'));
            const map = {big: jump.大地图, small: jump.小地图};
            const car = jump.五区.理论.find(entry => entry.sc_type === '跳图').cars[0].name;
            const input = {zone: 'zone5', tier: '理论', ...map, car};
            assert.notEqual(shared.effectiveTime(input),
                shared.effectiveTime({...input, scStates: {[map.big + '/' + map.small]: 'off'}}));
        }
        const configs = server === 'cn'
            ? [['理论', false, 'all'], ['高手', false, 'all'], ['高手', true, 'all'], ['高手', true, 'off'],
                ['高手', true, 'all', 'zone4'], ['普通', true, 'all'], ['自动', false, 'all']]
            : [['理论', false, 'all', 'zone5', false], ['理论', false, 'all', 'zone5', true]];
        for (const [tier, mixed, route, zone = 'zone5', overclock = false] of configs) {
            const rules = shared.carRules();
            const owned = zone === 'zone4' ? rules.zone4Cars : rules.zone5Cars;
            const stars = Object.fromEntries(owned.map((car, i) => {
                const range = core.starRange(rules.rules[car], zone);
                return [car, mixed ? range.min + i % (range.max - range.min + 1) : range.max];
            }));
            const oc = {};
            const routes = Object.fromEntries(allMaps.map(map => [map.big + '/' + map.small, route]));
            const input = {zone, tier, starsMap: stars, ocMap: oc, scStates: routes};
            const baselineInput = {...input, ocMap: {}, scStates: Object.fromEntries(allMaps.map(map => [map.big + '/' + map.small, 'all']))};
            const ranked = shared.prepareMapCandidates({...baselineInput, maps: allMaps})
                .map((map, index) => ({map: allMaps[index], count: map.groups.flat().filter(car => owned.includes(car)).length}))
                .sort((a, b) => b.count - a.count);
            const maps = [];
            for (const {map} of ranked) {
                if (!maps.some(other => other.big === map.big)) maps.push(map);
                if (maps.length === 5) break;
            }
            if (overclock) {
                const track = data.tracks.find(track => maps.some(map => map.big === track.大地图 && map.small === track.小地图)
                    && track.五区.理论.some(entry => entry.cars[0].oc));
                const car = track.五区.理论.find(entry => entry.cars[0].oc).cars[0].name;
                oc[car] = true;
                const map = {big: track.大地图, small: track.小地图, car};
                assert.notEqual(shared.effectiveTime({...input, ...map}), shared.effectiveTime({...baselineInput, ...map}));
            }
            const candidates = shared.prepareMapCandidates({...input, maps}, true);
            const draft = {schema: 1, server, zone, tier, maps, cars: owned, stars, oc, routes};
            const solveStarted = performance.now();
            const solved = core.recommendSchemes(candidates, new Set(owned), tier, 25, 99);
            const solveMs = performance.now() - solveStarted;
            const started = performance.now();
            const web = webEntry(cars, data, draft);
            const webMs = performance.now() - started;
            const actual = mini.calculate(draft).schemes;
            const compact = schemes => schemes.map(({assignment, vector}) => ({assignment, vector}));
            assert.deepEqual(compact(web.result), compact(actual));
            assert.deepEqual(compact(actual), solved);
            assert.ok(!actual.some(a => actual.some(b => dominates(b.vector, a.vector))));
            for (const scheme of actual) assert.deepEqual(scheme.rows.map(row => row.time),
                scheme.assignment.map((car, i) => car ? web.score(maps[i], car) : null));
            if (['普通', '自动'].includes(tier)) {
                assert.deepEqual(compact(actual), allocator.generateParetoSchemes(candidates, new Set(owned), 25, 99));
            } else if (actual[0]?.total !== null) {
                for (let i = 1; i < actual.length; i++) {
                    const millis = scheme => scheme.rows.reduce((sum, row) => sum + Math.round(row.time * 1000), 0);
                    assert.ok(actual[i].total !== null && millis(actual[i - 1]) <= millis(actual[i]));
                }
            }
            if (server === 'cn' && tier === '理论') {
                const first = actual[0].assignment[0], map = maps[0];
                const banned = {...draft, mapBans: {[JSON.stringify([server, zone, map.big, map.small])]: [first]}};
                const bannedMini = mini.calculate(banned).schemes;
                assert.ok(bannedMini.every(scheme => scheme.assignment[0] !== first));
                assert.deepEqual(compact(webEntry(cars, data, banned).result), compact(bannedMini));
            }
            t.diagnostic([server, zone, tier, mixed ? 'mixed' : 'max', route, 'OC=' + overclock,
                'density=' + candidates.map(c => c.groups.flat().filter(car => owned.includes(car)).length).join('/'),
                'solver=' + solveMs.toFixed(1) + 'ms', 'web=' + webMs.toFixed(1) + 'ms'].join(' '));
            checked++;
        }
    }
    assert.equal(checked, 9);
});
