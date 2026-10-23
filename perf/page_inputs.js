/* Test-only adapter: executes the actual page functions, never writes storage/data. */
(function (root) {
    function prepare(sources, carData, raceData) {
        const inline = sources['index.html'].match(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/)[1];
        if ((inline.match(/initApp\(\);/g) || []).length !== 1) throw Error('Page entry changed');
        const capture = `
            RACE_DATA = raceData;
            carStats = Object.fromEntries(carData.cars.map(c => [c.title, c]));
            nickToName = { ...carData._nickname_map };
            buildCarRules();
            out.configure = (zone, tier, starMode, route) => {
                currentZone = zone; currentTier = tier; starsMap = {};
                getCurrentCarList().forEach((car, i) => {
                    const r = getStarRange(car);
                    starsMap[car] = starMode === 'mixed' ? r.min + i % (r.max-r.min+1) : r.max;
                });
                specialRouteEnabled = Object.fromEntries(raceData.tracks.map(t => [t.大地图+'/'+t.小地图, route]));
                buildMapIndex();
                return { pool: getCurrentCarList(), stars: {...starsMap} };
            };
            out.candidates = maps => prepareMapCandidates(maps, currentZone);
        `;
        const out = {};
        new Function('document', 'carData', 'raceData', 'out', 'APP_CONFIG',
            sources['app_state.js'] + '\n' + sources['race_scores.js'] + '\n' + inline.replace('initApp();', capture))(
            { getElementById: () => ({}) }, carData, raceData, out,
            {server:'cn',storageKeys:{guestDraft:'racepick.guest-draft.v1'}});
        const cases = [];
        for (const zone of ['zone5', 'zone4']) for (const dense of [false, true]) {
            const tier = dense ? '理论' : '高手';
            const route = dense ? 'all' : 'off';
            const state = out.configure(zone, tier, dense ? 'max' : 'mixed', route);
            const owned = dense ? state.pool : state.pool.filter((_, i) => i % 3 === 0);
            const ownedSet = new Set(owned);
            const tracks = raceData.tracks.map(t => ({big: t.大地图, small: t.小地图}));
            const ranked = tracks.map(map => ({map, count: out.candidates([map])[0].groups.flat().filter(c => ownedSet.has(c)).length}));
            if (dense) ranked.sort((a,b) => b.count-a.count);
            const maps = [];
            for (const x of ranked) {
                if (!maps.some(m => m.big === x.map.big)) maps.push(x.map);
                if (maps.length === 5) break;
            }
            const candidates = out.candidates(maps);
            if (maps.length > 5 || new Set(maps.map(m => m.big)).size !== maps.length) throw Error('Invalid maps');
            for (const c of candidates) if (new Set(c.groups.flat()).size !== c.groups.flat().length) throw Error('Duplicate car');
            cases.push({name: zone + '-' + (dense ? 'dense' : 'ordinary'), zone, tier, route, stars: state.stars, maps, owned, candidates});
        }
        // Same real tracks, mixed user stars and per-route filtering, without raw-entry duplication.
        const base = cases[3];
        const state = out.configure('zone4', '高手', 'mixed', '滑栏杆');
        cases.push({name: 'zone4-expert-route', zone:'zone4', tier:'高手', route:'滑栏杆', stars:state.stars,
            maps:base.maps, owned:state.pool, candidates:out.candidates(base.maps)});
        return cases;
    }
    root.pageInputs = {prepare};
    if (typeof module !== 'undefined') module.exports = root.pageInputs;
})(globalThis);
