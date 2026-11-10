/** Shared selection rules/candidates. No DOM, networking, storage or platform APIs. */
const selectionCore = (() => {
    const scores = typeof module !== 'undefined' && module.exports ? require('./race_scores.js') : raceScores;
    const state = typeof module !== 'undefined' && module.exports ? require('./app_state.js') : appState;
    function carRules(carStats, server = 'cn') {
        const zone5Cars = [];
        const zone4Cars = [];
        const CAR_STAR_RULES = {};
        for (const car of Object.values(carStats)) {
            if (!car.nickname) continue;          // nickname 即数据里的车名（唯一索引）
            const zones = car.zones || [];
            if (zones.includes('五区')) zone5Cars.push(car.nickname);
            if (zones.includes('四区')) zone4Cars.push(car.nickname);
            if (car.star_rule) CAR_STAR_RULES[car.nickname] = car.star_rule;
        }
        if (zone5Cars.length === 0 || (server !== 'global' && zone4Cars.length === 0) || Object.keys(CAR_STAR_RULES).length === 0) {
            throw new Error('cars.json 缺少 zones / star_rule 定义，无法构建车池与星级规则');
        }
        return {zone5Cars, zone4Cars, rules: CAR_STAR_RULES};
    }
    function originalGroups(entries, {tier, starsFor, ocMap = {}, routeState = 'all', times}) {
        const scState = routeState;
        var scOn = scState !== 'off';


        // sc 类型过滤后的可用条目（关闭时剔除全部 sc）
        var usable = [];
        for (var ei = 0; ei < entries.length; ei++) {
            var raw = entries[ei]._raw;
            if (!raw) continue;
            const entryOc = raw.cars?.[0]?.oc;
            if ((entryOc === undefined ? false : entryOc) !== (ocMap[raw.cars?.[0]?.name] === true)) continue;
            if (!scOn && raw.sc) continue;
            if (scOn && scState !== 'all' && raw.sc && raw.sc_type !== scState) continue;
            usable.push(entries[ei]);
        }

        // 收集候选车（保持原数据出现顺序，作为并列时与无成绩时的稳定序）
        var cars = [];
        var seen = {};
        for (var k = 0; k < usable.length; k++) {
            var name = String(usable[k][0]);
            if (!name) continue;
            if (seen[name] === undefined) { seen[name] = cars.length; cars.push(name); }
        }

        // 每车取「可用的最快成绩」：开关打开时普通与 sc 一起比，谁快用谁
        var scored = cars.map(function(carName) {
            var normal = scores.effectiveTime(usable, carName, tier, starsFor(carName), 'all', false, {ocMap});
            var sc = scOn ? scores.effectiveTime(usable, carName, tier, starsFor(carName), 'all', true, {ocMap}) : null;
            var best = normal;
            if (sc != null && (best == null || sc < best)) best = sc;
            times?.set(carName, best);
            return { car: carName, time: best };
        });

        // 有成绩的按成绩升序；无成绩的按原顺序附在末尾
        var withTime = scored.filter(function(s) { return s.time != null; });
        var noTime = scored.filter(function(s) { return s.time == null; });
        withTime.sort(function(a, b) { return a.time - b.time; });

        return withTime.concat(noTime).map(function(s) { return [s.car]; });
    }
    function prepareMapCandidates(validMaps, groupsFor, includeTimes = false) {
        const n = validMaps.length;
        // 1. 预计算每张图的数据:候选组、车→优先级映射
        const mapsData = [];
        for (let i = 0; i < n; i++) {
            const { big, small } = validMaps[i];
            const times = includeTimes ? new Map() : undefined;
            const originalGroups = groupsFor(big, small, times);
            if (!originalGroups) {
                // 无数据的地图，标记为空
                mapsData.push({ groups: [], carToPriority: new Map() });
                continue;
            }

            // 保留原始候选优先级；车库筛选由分配器处理。
            // 车->优先级 (组索引)
            const carToPriority = new Map();
            for (let gIdx = 0; gIdx < originalGroups.length; gIdx++) {
                const group = originalGroups[gIdx];
                for (const car of group) {
                    if (!carToPriority.has(car)) {
                        carToPriority.set(car, gIdx);
                    }
                }
            }
            mapsData.push({ groups: originalGroups, carToPriority, ...(includeTimes ? {times} : {}) });
        }

        return mapsData;
    }
    function ranksByTime(tier) {
        return tier === '高手' || tier === '理论';
    }
    function recommendSchemes(candidates, owned, tier, limit, noCarPriority) {
        const solver = typeof module !== 'undefined' && module.exports ? require('./allocator.js') : allocator;
        const solve = ranksByTime(tier) ? solver.generateRankedSchemes : solver.generateParetoSchemes;
        return solve(candidates, owned, limit, noCarPriority);
    }
    function excludeBannedCars(candidate, banned) {
        if (!banned?.size) return candidate;
        return {...candidate, groups: candidate.groups.map(group => group.filter(car => !banned.has(car)))};
    }
    function starRange(rule, zone) {
        if (!rule) return {min: 1, max: 6};
        let max = rule.max || 6;
        if (zone === 'zone4' && rule.zone4Max != null) max = rule.zone4Max;
        return {min: rule.min || 1, max: Math.max(max, rule.min || 1)};
    }
    function carStars(rule, zone, saved, server = 'cn') {
        const range = starRange(rule, zone);
        if (server === 'global') return range.max;
        const fallback = zone === 'zone5' ? range.max : (rule?.default != null ? rule.default : 6);
        const stars = Number.isInteger(saved) && saved >= 1 && saved <= 6 ? saved : fallback;
        return Math.max(range.min, Math.min(range.max, stars));
    }
    function createSelectionCore({cars, data, server = 'cn'}) {
        if (!['cn', 'global'].includes(server)) throw Error('未知服别');
        const derived = carRules(Object.fromEntries(cars.cars.map(car => [car.title, car])), server);
        function trackFor(big, small) { return data.tracks.find(t => t.大地图 === big && t.小地图 === small); }
        function options(input) {
            const {zone, tier, starsMap = {}, ocMap = {}, scStates = {}} = input;
            if (!['zone4', 'zone5'].includes(zone) || !['理论', '高手', '普通', '自动'].includes(tier)) throw Error('未知区档');
            if (server === 'global' && (zone !== 'zone5' || tier !== '理论')) throw Error('国际服仅支持五区理论');
            return {zone, tier, ocMap, scStates, starsFor: name => carStars(derived.rules[name], zone, starsMap[name], server)};
        }
        function entriesFor(track, opt) {
            return track?.[opt.zone === 'zone4' ? '四区' : '五区']?.[opt.tier] || [];
        }
        function routeFor(track, opt) {
            const entries = entriesFor(track, opt);
            return state.route(opt.scStates[track.大地图 + '/' + track.小地图], [...new Set(entries.filter(e => e.sc).map(e => e.sc_type))]);
        }
        function candidates(input, includeTimes = false) {
            const opt = options(input);
            return prepareMapCandidates(input.maps, (big, small, times) => {
                const track = trackFor(big, small);
                if (!track) return null;
                const entries = entriesFor(track, opt).map(raw => Object.assign([raw.cars[0].name], {_raw: raw}));
                return originalGroups(entries, {...opt, routeState: routeFor(track, opt), times});
            }, includeTimes);
        }
        function effectiveTime({big, small, car, ...input}) {
            const opt = options(input), track = trackFor(big, small);
            if (!track) return null;
            return scores.effectiveTime(entriesFor(track, opt), car, opt.tier, opt.starsFor(car), routeFor(track, opt), null, {ocMap: opt.ocMap});
        }
        return {carRules: () => derived, prepareMapCandidates: candidates, effectiveTime};
    }
    function createSelectionContext(snapshot) {
        const {cars, data, server, version} = snapshot;
        const shared = createSelectionCore({cars, data, server});
        const derived = shared.carRules();
        function inputFor(draft) {
            if (draft.schema !== 1 || draft.server !== server) throw Error('草稿版本或服别不匹配');
            if (!Array.isArray(draft.maps) || draft.maps.length !== 5) throw Error('地图必须保留五槽');
            const maps = [], regions = new Set();
            draft.maps.forEach((map, originalIndex) => {
                if (!map || !map.big || !map.small) return;
                if (!data.tracks.some(t => t.大地图 === map.big && t.小地图 === map.small)) throw Error('地图不在当前目录');
                if (regions.has(map.big)) throw Error('大地图不能重复');
                regions.add(map.big); maps.push({...map, originalIndex});
            });
            return {maps, zone:draft.zone, tier:draft.tier, starsMap:draft.stars || {}, ocMap:draft.oc || {}, scStates:draft.routes || {}};
        }
        function getModel(draft) {
            const input = inputFor(draft);
            shared.prepareMapCandidates(input); // Validate the server/zone/tier even for an empty draft.
            const pool = derived[input.zone === 'zone4' ? 'zone4Cars' : 'zone5Cars'];
            const ocNames = new Set(server === 'global' ? data.tracks.flatMap(t => (t.五区?.理论 || []).filter(e => e.cars?.[0]?.oc === true).map(e => e.cars[0].name)) : []);
            return {server, version, zones:server === 'global' ? ['zone5'] : ['zone5','zone4'],
                tiers:server === 'global' ? ['理论'] : ['理论','高手','普通','自动'],
                maps:data.tracks.map(t => ({big:t.大地图,small:t.小地图})),
                cars:pool.map(id => {
                    const rule=derived.rules[id], range=starRange(rule,input.zone);
                    return {id,label:id,stars:server === 'global' ? [range.max] : Array.from({length:range.max-range.min+1},(_,i)=>range.min+i),
                        defaultStar:carStars(rule,input.zone,undefined,server),ocAllowed:ocNames.has(id)};
                }),
                routes:input.maps.flatMap(map => {
                    const track=data.tracks.find(t=>t.大地图===map.big && t.小地图===map.small);
                    const entries=track[input.zone==='zone4'?'四区':'五区']?.[input.tier] || [];
                    const types=[...new Set(entries.filter(e=>e.sc && e.sc_type).map(e=>e.sc_type))];
                    return types.length ? [{key:map.big+'/'+map.small,label:types.length===1?map.small+'（'+types[0]+'）':map.small,types}] : [];
                })};
        }
        function calculate(draft) {
            const input = inputFor(draft);
            const candidates = shared.prepareMapCandidates(input, ranksByTime(input.tier)).map((candidate, i) => {
                const {big, small} = input.maps[i];
                const banned = draft.mapBans?.[JSON.stringify([server, input.zone, big, small])];
                return excludeBannedCars(candidate, new Set(banned));
            });
            const pool=derived[input.zone==='zone4'?'zone4Cars':'zone5Cars'];
            const owned=state.garage(draft.cars,new Set(pool));
            const schemes=recommendSchemes(candidates,owned,input.tier,25,99);
            return {schemes:schemes.map(scheme => {
                const rows=Array.from({length:5},(_,i)=>({map:draft.maps[i]?.small || '',car:null,time:null}));
                const assignment=new Array(5).fill(null),vector=new Array(5).fill(null);
                input.maps.forEach((map,i)=>{
                    const car=scheme.assignment[i];
                    assignment[map.originalIndex]=car;vector[map.originalIndex]=scheme.vector[i];
                    rows[map.originalIndex]={map:map.small,car,time:car===null?null:shared.effectiveTime({...input,...map,car})};
                });
                return {rows,assignment,vector,total:rows.every(row=>row.car!==null && row.time!==null)?rows.reduce((sum,row)=>sum+row.time,0):null,
                    prioritySum:scheme.vector.reduce((sum,value)=>sum+(value??0),0)};
            })};
        }
        return {getModel, calculate};
    }
    return {carRules, starRange, carStars, originalGroups, prepareMapCandidates, ranksByTime, recommendSchemes,
        excludeBannedCars, createSelectionCore, createSelectionContext};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = selectionCore;
