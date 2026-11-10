/** 互斥分配算法：无 DOM、网络或应用状态依赖。 */
const allocator = (() => {
    /**
     * 帕累托非支配比较：方案 A 支配 B ⟺ A 各维度不差于 B 且至少一维严格更优。
     * 此处维度 = 各图的优先级数值（越小越好）。
     */
    function dominates(aVec, bVec) {
        let atLeastOneBetter = false;
        for (let i = 0; i < aVec.length; i++) {
            if (aVec[i] > bVec[i]) return false;
            if (aVec[i] < bVec[i]) atLeastOneBetter = true;
        }
        return atLeastOneBetter;
    }

    /** 核心算法：仅使用传入候选数据和车库，返回与输入地图对应的方案。 */
    function generateParetoSchemes(mapCandidates, ownedSet, maxSchemesLimit = 20, noCarPriority = 99) {
        const n = mapCandidates.length;
        if (n === 0) return [];
        const mapsData = mapCandidates.map(({ groups, carToPriority }) => ({
            filteredGroups: groups.map(group => group.filter(car => ownedSet.has(car))),
            carToPriority,
        }));

        // ---- 2. 回溯枚举，边走边维护帕累托前沿 ----
        //
        // 不再把全部可行分配收集到 allSchemes 里再统一过滤：密集候选下叶子数可达数百万，
        // 逐个复制 assignment/vector 会吃掉上 GB 堆。改为每走到叶子就**直接与当前前沿比较**，
        // 被支配的立即返回（一次数组复制都不做），只有能进入前沿的方案才复制。
        //
        // 正确性：在线前沿构建（被支配则丢弃 → 否则剔除被本方案支配的前沿项 → 登记本方案）
        // 得到的最终前沿与「先收集全部再批量过滤」完全一致——支配关系有传递性，
        // 若某方案被一个非前沿方案支配，那个非前沿方案又被前沿中某方案支配，则它也直接被前沿支配。
        // 枚举顺序未变，前沿的维护顺序也未变，故最终顺序（含同向量方案的相对顺序）保持一致。
        const paretoFront = [];
        const usedCars = new Set();
        const curAssign = new Array(n).fill(null);
        const curVector = new Array(n).fill(noCarPriority);

        // 放松剩余位置之间及其与前缀的车辆互斥约束，得到逐维乐观下界。
        // 留空也参加 min：调用者的 noCarPriority 不一定比候选优先级大。
        // 非有限数值输入沿用原始枚举行为，不为其引入新的比较语义。
        let canBound = Number.isFinite(noCarPriority);
        const optimistic = mapsData.map(({ filteredGroups, carToPriority }) => {
            let best = noCarPriority;
            for (const group of filteredGroups) for (const car of group) {
                const priority = carToPriority.get(car) ?? noCarPriority;
                if (!Number.isFinite(priority)) canBound = false;
                best = Math.min(best, priority);
            }
            return best;
        });

        function branchDominated(idx) {
            for (const existing of paretoFront) {
                let strictlyBetter = false;
                let noWorse = true;
                for (let i = 0; i < n; i++) {
                    const bound = i < idx ? curVector[i] : optimistic[i];
                    if (existing.vector[i] > bound) { noWorse = false; break; }
                    if (existing.vector[i] < bound) strictlyBetter = true;
                }
                if (noWorse && strictlyBetter) return true;
            }
            return false;
        }

        /**
         * 递归回溯。按地图顺序逐一尝试可用车辆，保证同一辆车不重复分配。
         *
         * 「留空」本身也是一条可行方案（允许部分分配），因此每个位置都显式枚举留空分支：
         * 某张图可用的车可能留给后面的图更划算，两个方案优先级向量不同、互不支配。
         * 若只在「本图已无车可分」时才留空，靠前的图会对稀缺车获得绝对优先权，
         * 并静默漏掉一批非支配方案（例：两行都只能选 A 时，[空, A] 从未被枚举）。
         */
        function backtrack(idx) {
            if (idx === n) {
                // 被当前前沿里任一方案支配 → 直接丢弃，不复制数组
                for (let i = 0; i < paretoFront.length; i++) {
                    if (dominates(paretoFront[i].vector, curVector)) return;
                }
                // 未被支配：剔除被本方案支配的前沿项，再把本方案登记进前沿
                // （注意：相同向量、不同车辆分配的方案互不支配，因此都会保留，不做去重）
                const kept = [];
                for (const existing of paretoFront) {
                    if (!dominates(curVector, existing.vector)) kept.push(existing);
                }
                kept.push({
                    assignment: [...curAssign],
                    vector: [...curVector]
                });
                paretoFront.length = 0;
                paretoFront.push(...kept);
                return;
            }
            // 每个后代向量逐维 >= 下界。严格支配下界即严格支配所有后代；
            // 相等时不能剪枝，否则会丢失相同向量的不同车辆分配。
            if (idx > 0 && canBound && branchDominated(idx)) return;
            const { filteredGroups, carToPriority } = mapsData[idx];

            // 分支 1：留空本图（本图没有任何候选组时，这就是唯一分支）
            curAssign[idx] = null;
            curVector[idx] = noCarPriority;
            backtrack(idx + 1);

            // 分支 2：为每个候选组挑一辆尚未被其他图占用的车
            for (let g = 0; g < filteredGroups.length; g++) {
                const group = filteredGroups[g];
                if (group.length === 0) continue;
                for (const car of group) {
                    if (usedCars.has(car)) continue;
                    usedCars.add(car);
                    curAssign[idx] = car;
                    curVector[idx] = carToPriority.get(car) ?? noCarPriority;
                    backtrack(idx + 1);
                    usedCars.delete(car);
                    curAssign[idx] = null;
                    curVector[idx] = noCarPriority;
                }
            }
        }

        backtrack(0);
        if (paretoFront.length === 0) return [];

        // ---- 3. 排序与截断（必须在搜索全部结束后进行）----
        // 先按总优先级排序，再截取；同分时按向量字典序排序
        paretoFront.sort((a, b) => {
            const totalDifference = a.vector.reduce((sum, value) => sum + value, 0)
                - b.vector.reduce((sum, value) => sum + value, 0);
            if (totalDifference !== 0) return totalDifference;
            for (let i = 0; i < n; i++) {
                if (a.vector[i] !== b.vector[i]) return a.vector[i] - b.vector[i];
            }
            return 0;
        });

        return paretoFront.slice(0, maxSchemesLimit);
    }

    // Sum decimal score values exactly, including the existing three-decimal estimates.
    function timeUnits(options) {
        const decimals = options.map(option => {
            const [mantissa, exponent = '0'] = String(option.time).split('e');
            const [whole, fraction = ''] = mantissa.split('.');
            return {digits: whole + fraction, places: fraction.length - Number(exponent)};
        });
        const places = decimals.reduce((max, value) => Math.max(max, value.places), 0);
        const units = decimals.map(value => value.digits + '0'.repeat(places - value.places));
        const wide = units.some(value => Number(value) > Number.MAX_SAFE_INTEGER / 5);
        options.forEach((option, i) => { option.units = wide ? BigInt(units[i]) : Number(units[i]); });
        return wide ? BigInt(0) : 0;
    }

    function generateRankedSchemes(mapCandidates, ownedSet, limit, noCarPriority) {
        const n = mapCandidates.length;
        if (!n || limit <= 0) return [];
        const byCar = new Map();
        mapCandidates.forEach(({groups, carToPriority, times}, slot) => {
            let order = 0;
            for (const group of groups) for (const car of group) {
                order++;
                if (!ownedSet.has(car)) continue;
                if (!byCar.has(car)) byCar.set(car, []);
                byCar.get(car).push({car, slot, order, priority: carToPriority.get(car) ?? noCarPriority,
                    time: times?.get(car)});
            }
        });
        const full = (1 << n) - 1;
        const cars = [...byCar.values()];

        function search(timed) {
            const options = timed ? cars.map(choices => choices.filter(({time}) => Number.isFinite(time) && time > 0)) : cars;
            const zero = timed ? timeUnits(options.flat()) : 0;
            const best = Array.from({length: full + 1}, () => []);
            best[0].push({choices: new Array(n).fill(null), vector: new Array(n).fill(noCarPriority),
                seconds: zero, priority: n * noCarPriority, covered: 0});
            function compare(a, b) {
                if (timed && a.seconds !== b.seconds) return a.seconds < b.seconds ? -1 : 1;
                if (a.priority !== b.priority) return a.priority - b.priority;
                for (let i = 0; i < n; i++) {
                    const difference = a.vector[i] - b.vector[i];
                    if (difference) return difference;
                }
                for (let i = 0; i < n; i++) {
                    const difference = (a.choices[i]?.order ?? 0) - (b.choices[i]?.order ?? 0);
                    if (difference) return difference;
                }
                return 0;
            }
            function keepOnFrontier(frontier, next) {
                let equal = 0, worstEqual = -1;
                for (let i = 0; i < frontier.length; i++) {
                    const existing = frontier[i];
                    if (dominates(existing.vector, next.vector)) return;
                    if (!existing.vector.every((priority, slot) => priority === next.vector[slot])) continue;
                    equal++;
                    if (worstEqual === -1 || compare(existing, frontier[worstEqual]) > 0) worstEqual = i;
                }
                if (equal === limit) {
                    if (compare(next, frontier[worstEqual]) >= 0) return;
                    frontier.splice(worstEqual, 1);
                }
                for (let i = frontier.length - 1; i >= 0; i--) {
                    if (dominates(next.vector, frontier[i].vector)) frontier.splice(i, 1);
                }
                frontier.push(next);
            }
            // At the same mask, future cars and open slots are identical. Adding
            // the same choices preserves strict dominance and the ranking of ties.
            // Cap equal vectors only: distinct frontier vectors may survive later.
            for (const choices of options) {
                for (let mask = full - 1; mask >= 0; mask--) {
                    for (const choice of choices) {
                        const bit = 1 << choice.slot;
                        if (mask & bit) continue;
                        const target = best[mask | bit];
                        for (const previous of best[mask]) {
                            const assigned = previous.choices.slice();
                            assigned[choice.slot] = choice;
                            const vector = previous.vector.slice();
                            vector[choice.slot] = choice.priority;
                            keepOnFrontier(target, {choices: assigned, vector, seconds: timed ? previous.seconds + choice.units : zero,
                                priority: previous.priority + choice.priority - noCarPriority, covered: previous.covered + 1});
                        }
                    }
                }
            }
            if (timed) return best[full].sort(compare).slice(0, limit);
            const all = best.flat();
            const coverage = all.reduce((max, scheme) => Math.max(max, scheme.covered), 0);
            const eligible = all.filter(scheme => scheme.covered === coverage);
            return eligible.filter(scheme => !eligible.some(other => dominates(other.vector, scheme.vector)))
                .sort(compare).slice(0, limit);
        }

        const timed = n === 5 ? search(true) : [];
        return (timed.length ? timed : search(false)).map(({choices, vector}) => ({
            assignment: choices.map(choice => choice?.car ?? null),
            vector,
        }));
    }

    return { generateParetoSchemes, generateRankedSchemes };
})();

// The browser keeps its existing binding; mini-program logic can import the core.
if (typeof module !== 'undefined' && module.exports) module.exports = allocator;
