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

    return { generateParetoSchemes };
})();
