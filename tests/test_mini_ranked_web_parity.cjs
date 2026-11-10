'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const path=require('node:path'),cp=require('node:child_process');
const {performance}=require('node:perf_hooks');
const allocator=require('../miniapp/shared/allocator'),core=require('../miniapp/shared/selection_core');
const bundle=require('../miniapp/generated/local-bundle'),files=bundle.files;
const pin=require('../miniapp/shared-source.json').ref;
const root=path.resolve(__dirname,'..');
const read=(name,ref=pin)=>cp.execFileSync('git',['show',ref+':'+name],{cwd:root,encoding:'utf8'});
const dominates=(a,b)=>a.every((x,i)=>x<=b[i])&&a.some((x,i)=>x<b[i]);

function webEntry(cars, data, draft) {
    const webRef = process.env.RACEPICK_WEB_PARITY_REF || pin;
    const inline = read('index.html', webRef).match(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/)[1];
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
    const sources = ['app_state.js', 'allocator.js', 'race_scores.js', 'selection_core.js', 'home_presenter.js'].map(name => read(name, webRef));
    const document = {getElementById: () => ({classList: {add() {}, remove() {}}})};
    const out = {};
    new Function('document', 'APP_CONFIG', 'cars', 'data', 'draft', 'requestAnimationFrame', 'setTimeout', 'globalThis', 'out',
        [...sources, entry].join('\n;\n'))(document, {server: draft.server, storageKeys: {}}, cars, data, draft,
        f => f(), f => f(), {RACEPICK_SERVER: draft.server}, out);
    return out;
}

test('real website recommendation and generated mini-program local service agree', async t => {
    for (const name of ['allocator.js','selection_core.js']) {
        assert.equal(fs.readFileSync(path.join(root,'miniapp/shared',name),'utf8'),read(name));
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
                assert.deepEqual(mini.calculate({...banned,mapBans:{}}).schemes,actual);
                const {createController}=require('../miniapp/lib/controller');
                let state;
                const queue=[];
                const controller=createController({service:mini,storage:{read:()=>draft},media:{},
                    render:next=>{state=next;},autoCompute:true,schedule:run=>queue.push(run)});
                async function flush(){
                    queue.splice(0).forEach(run=>run());
                    await Promise.resolve();
                }
                await flush();
                assert.deepEqual(state.result.schemes,actual);
                const key=JSON.stringify([server,zone,map.big,map.small]);
                assert.ok(controller.setMapBans(0,key,[first]));
                await flush();
                assert.deepEqual(state.result.schemes,bannedMini);
                assert.equal(state.dirty,false);
                assert.ok(controller.setMapBans(0,key,[]));
                await flush();
                assert.deepEqual(state.result.schemes,actual);
                controller.setMap(0,null);
                controller.setMap(1,map);
                controller.setMap(0,{big:map.big,small:''});
                assert.equal(state.draft.maps[0],null);
                assert.deepEqual(state.draft.maps[1],map);
                assert.match(state.error,/不能重复/);
                await flush();
                assert.ok(state.result.schemes.length);


            }
            t.diagnostic([server, zone, tier, mixed ? 'mixed' : 'max', route, 'OC=' + overclock,
                'density=' + candidates.map(c => c.groups.flat().filter(car => owned.includes(car)).length).join('/'),
                'solver=' + solveMs.toFixed(1) + 'ms', 'web=' + webMs.toFixed(1) + 'ms'].join(' '));
            checked++;
        }
    }
    assert.equal(checked, 9);
});
