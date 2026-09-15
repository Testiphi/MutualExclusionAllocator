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

        // ---- 2. 回溯枚举所有可行分配（车不重复） ----
        const allSchemes = [];    // { assignment: string[], vector: number[] }
        const usedCars = new Set();
        const curAssign = new Array(n).fill(null);
        const curVector = new Array(n).fill(noCarPriority);

        /**
         * 递归回溯。按地图顺序逐一尝试可用车辆，保证同一辆车不重复分配。
         * 某图无可用车时将其留空，继续后续地图。
         */
        function backtrack(idx) {
            if (idx === n) {
                allSchemes.push({
                    assignment: [...curAssign],
                    vector: [...curVector]
                });
                return;
            }
            const { filteredGroups, carToPriority } = mapsData[idx];

            if (filteredGroups.length === 0 || filteredGroups.every(g => g.length === 0)) {
                // 无可用车：留空当前图，继续
                curAssign[idx] = null;
                curVector[idx] = noCarPriority;
                backtrack(idx + 1);
                return;
            }

            var anyAssigned = false;
            for (let g = 0; g < filteredGroups.length; g++) {
                const group = filteredGroups[g];
                if (group.length === 0) continue;
                for (const car of group) {
                    if (!usedCars.has(car)) {
                        anyAssigned = true;
                        const prio = carToPriority.get(car) ?? noCarPriority;
                        usedCars.add(car);
                        curAssign[idx] = car;
                        curVector[idx] = prio;
                        backtrack(idx + 1);
                        usedCars.delete(car);
                        curAssign[idx] = null;
                        curVector[idx] = noCarPriority;
                    }
                }
            }
            // 所有车已被其他图占用：留空继续
            if (!anyAssigned) {
                curAssign[idx] = null;
                curVector[idx] = noCarPriority;
                backtrack(idx + 1);
            }
        }

        backtrack(0);
        if (allSchemes.length === 0) return [];

        // ---- 3. 帕累托非支配过滤（前沿构建） ----
        const paretoFront = [];
        for (const scheme of allSchemes) {
            let dominated = false;
            for (let i = 0; i < paretoFront.length; i++) {
                if (dominates(paretoFront[i].vector, scheme.vector)) {
                    dominated = true;
                    break;
                }
            }
            if (!dominated) {
                const newFront = [];
                for (const existing of paretoFront) {
                    if (!dominates(scheme.vector, existing.vector)) {
                        newFront.push(existing);
                    }
                }
                newFront.push(scheme);
                paretoFront.length = 0;
                paretoFront.push(...newFront);
            }
        }

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

    return { generateParetoSchemes };
})();
