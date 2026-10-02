/** 成绩计算：无 DOM、网络或应用状态依赖；不同跑法独立估算后取最快值。 */
const raceScores = (() => {
    const STAR_PENALTY_A = 0.00525;
    const STAR_PENALTY_B = 0.001025;

    function starPenalty(diff) {
        return Math.exp(STAR_PENALTY_A * diff + STAR_PENALTY_B * diff * diff);
    }

    function getStarAdjustedScore(dataPoints, userStars) {
        if (!dataPoints || dataPoints.length === 0) return null;
        // 按星级排序
        var sorted = dataPoints.slice().sort(function(a, b) { return a.stars - b.stars; });
        // 精确匹配
        for (var i = 0; i < sorted.length; i++) {
            if (sorted[i].stars === userStars) return sorted[i].time;
        }
        // 找到包围 userStars 的两个数据点
        var lower = null, upper = null;
        for (var i = 0; i < sorted.length; i++) {
            if (sorted[i].stars < userStars) {
                if (!lower || sorted[i].stars > lower.stars) lower = sorted[i];
            } else if (sorted[i].stars > userStars) {
                if (!upper || sorted[i].stars < upper.stars) upper = sorted[i];
            }
        }
        // 有上下界 → 线性插值
        if (lower && upper) {
            var ratio = (userStars - lower.stars) / (upper.stars - lower.stars);
            return +(lower.time + (upper.time - lower.time) * ratio).toFixed(3);
        }
        // 只有下界（userStars > 所有已知）→ 用最接近的已知点 + 惩罚倒数
        if (lower) {
            var diff = userStars - lower.stars;
            // 更高星应更快，除以惩罚倍数
            return +(lower.time / starPenalty(diff)).toFixed(3);
        }
        // 只有上界（userStars < 所有已知）→ 用最接近的已知点 + 惩罚
        if (upper) {
            var diff = upper.stars - userStars;
            return +(upper.time * starPenalty(diff)).toFixed(3);
        }
        return null;
    }

    function effectiveTime(entries, carName, tier, userStars, routeState = 'all', onlySc = null) {
        const routes = new Map();
        for (const entry of entries) {
            const raw = entry._raw || entry;
            if (raw.cars?.[0]?.name !== carName || raw.time == null) continue;
            const sc = !!raw.sc;
            if (onlySc !== null && sc !== onlySc) continue;
            if (sc && (routeState === 'off' || (routeState !== 'all' && raw.sc_type !== routeState))) continue;
            const key = sc ? (raw.sc_type || 'sc') : null;
            if (!routes.has(key)) routes.set(key, []);
            routes.get(key).push({stars: raw.cars[0].stars || 6, time: raw.time});
        }
        let best = null;
        for (const points of routes.values()) {
            let time;
            if (tier === '高手') {
                time = getStarAdjustedScore(points, userStars);
            } else {
                const highest = Math.max(...points.map(point => point.stars));
                time = Math.min(...points.filter(point => point.stars === highest).map(point => point.time));
            }
            if (time != null && (best === null || time < best)) best = time;
        }
        return best;
    }

    return { starPenalty, getStarAdjustedScore, effectiveTime };
})();
