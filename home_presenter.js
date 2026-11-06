/** DOM-free homepage presentation. Scores/candidates/solver remain in the five shared modules. */
const homePresenter = (() => {
    const core = typeof module !== 'undefined' && module.exports ? require('./selection_core.js') : selectionCore;
    const state = typeof module !== 'undefined' && module.exports ? require('./app_state.js') : appState;
    const NICKNAME_ALIASES = {
        '第六元素': '六子',
        '兔子': 'c2',
    };
    const RESULT_COPY = Object.freeze({
        select_maps: '请先选择地图',
        select_cars: '请先选择车辆',
        no_records: '找不到合适的方案？尝试投稿你自己的成绩来帮助我们提升！',
        partial_missing: '找不到合适的方案？尝试投稿你自己的成绩来帮助我们提升！',
        conflict: '找不到合适的方案？尝试投稿你自己的成绩来帮助我们提升！',
    });
    function resultGuidance({maps, ownedCars, candidates = [], scheme}) {
        const valid = maps.flatMap((m, i) => m?.big && m?.small ? [{...m, originalIndex:m.originalIndex ?? i}] : []);
        const owned = new Set(ownedCars);
        const notice = (kind, missingMaps = [], targetMaps = missingMaps) => ({kind, message:RESULT_COPY[kind], canSubmit:!['select_maps','select_cars'].includes(kind), action:'投稿我的成绩', missingMaps, targetMaps});
        if (!valid.length) return notice('select_maps');
        if (!owned.size) return notice('select_cars');
        const empty = valid.map((map, i) => ({map, i})).filter(({map}) => !scheme?.assignment?.[map.originalIndex]);
        if (!empty.length) return null;
        // Unknown/failed input is not proof of a data gap. Callers also hide this during errors/busy states.
        if (candidates.length !== valid.length || candidates.some(c => !Array.isArray(c?.groups))) return null;
        const missing = empty.filter(({i}) => !candidates[i].groups.some(group => group.some(car => owned.has(car)))).map(({map}) => map);
        if (missing.length === valid.length) return notice('no_records', missing);
        const targets=empty.map(({map})=>map);
        if (missing.length) return notice('partial_missing', missing, targets);
        return notice('conflict',[],targets);
    }
    function filterBySearch(carList, query, {nickToName, aliases = NICKNAME_ALIASES}) {
        if (!query) return [...carList];
        const q = query.toLowerCase();
        return carList.filter(car => {
            if (car.includes(query)) return true;
            if (nickToName[car] && nickToName[car].toLowerCase().includes(q)) return true;
            // 别名匹配：查所有指向此车的别名键
            for (var aliasKey in aliases) {
                if (aliases[aliasKey] === car && aliasKey.includes(query)) return true;
            }
            return false;
        });
    }
    function filterByClass(carList, cls, {carStats, nickToName}) {
        if (!cls) return [...carList];
        return carList.filter(car => {
            const stats = carStats[nickToName[car]];
            return stats && stats.class === cls;
        });
    }
    function sortCarList(carList, mode, {carStats, nickToName}) {
        const sorted = [...carList];
        if (mode === 'score-desc' || mode === 'score-asc') {
            sorted.sort((a, b) => {
                const left = carStats[nickToName[a]]?.score, right = carStats[nickToName[b]]?.score;
                const leftKnown = Number.isFinite(left), rightKnown = Number.isFinite(right);
                if (leftKnown !== rightKnown) return leftKnown ? -1 : 1;
                if (!leftKnown) return a.localeCompare(b, 'zh');
                return mode === 'score-desc' ? right - left : left - right;
            });
        } else {
            sorted.sort((a, b) => a.localeCompare(b, 'zh'));
        }
        return sorted;
    }
    function getTopCars(candidate, ownedInZone, {tier, starsFor, scoreFor}) {
        const cars = [...new Set(candidate.groups.flat())].filter(car => ownedInZone.has(car)).slice(0, 3);
        return cars.map(car => ({
            car,
            stars: tier === '理论' ? null : starsFor(car),
            score: scoreFor(car),
        }));
    }
    function subtitle(server, data, zone, tier) {
        if (server === 'global') return '国际服 · 五区满星理论参考 · 含特殊跑法';
        const info=data?.tier_info?.[tier];
        if (!info) return null;
        return tier === '理论' && zone === 'zone4' ? '顶级特改理论成绩，默认最优解，含特殊跑法' : info.desc;
    }
    function schemeSummary(scheme,maps,index) {
        const parts=[];
        maps.forEach((map,i)=>{if(map?.big && map?.small)parts.push(`${i+1}:${scheme.assignment[i] || '空'}`);});
        const total=scheme.vector.reduce((sum,value)=>sum+(value!==null?value:0),0);
        return `方案${index+1} · ${parts.join(' ')} · Σ=${total}`;
    }
    function createHomePresenter(snapshot) {
        const {cars,data,server}=snapshot;
        const selection=core.createSelectionCore(snapshot),context=core.createSelectionContext(snapshot);
        const carStats=Object.fromEntries(cars.cars.map(car=>[car.title,car]));
        const nickToName={...cars._nickname_map};
        cars.cars.forEach(car=>{if(car.nickname&&!nickToName[car.nickname])nickToName[car.nickname]=car.title;});
        const lookup={carStats,nickToName};
        function present(draft,filters={}) {
            const model=context.getModel(draft);
            const valid=draft.maps.flatMap((m,i)=>m?.big&&m?.small?[{...m,originalIndex:i}]:[]);
            const input={maps:valid,zone:draft.zone,tier:draft.tier,starsMap:draft.stars||{},ocMap:draft.oc||{},scStates:draft.routes||{}};
            const candidates=selection.prepareMapCandidates(input);
            const pool=selection.carRules()[draft.zone==='zone4'?'zone4Cars':'zone5Cars'];
            const owned=state.garage(draft.cars,new Set(pool));
            const visibleCars=sortCarList(filterByClass(filterBySearch(pool,filters.query||'',lookup),filters.class||null,lookup),filters.sort||'alpha',lookup);
            const references=Array.from({length:5},()=>[]);
            valid.forEach((map,i)=>{references[map.originalIndex]=getTopCars(candidates[i],owned,{tier:draft.tier,
                starsFor:car=>core.carStars(selection.carRules().rules[car],draft.zone,draft.stars?.[car],server),
                scoreFor:car=>selection.effectiveTime({...input,...map,car})});});
            const result=context.calculate(draft);
            const guidanceInput={maps:valid,ownedCars:owned,candidates};
            const guidanceByScheme=result.schemes.map(scheme=>resultGuidance({...guidanceInput,scheme}));
            return {subtitle:subtitle(server,data,draft.zone,draft.tier) ?? '帕累托最优 · 擂台选车',visibleCars,references,
                model,schemes:result.schemes.map((scheme,i)=>({...scheme,summary:schemeSummary(scheme,draft.maps,i)})),
                guidanceByScheme,guidance:guidanceByScheme[0] ?? (result.schemes.length?null:resultGuidance(guidanceInput)),
                emptyState:!valid.length?'请先选择地图':!result.schemes.length?'无可分配方案':null};
        }
        return {present};
    }
    return {aliases:NICKNAME_ALIASES,resultCopy:RESULT_COPY,resultGuidance,initialTier:server=>server==='global'?'理论':'高手',filterBySearch,filterByClass,sortCarList,getTopCars,subtitle,schemeSummary,createHomePresenter};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=homePresenter;
