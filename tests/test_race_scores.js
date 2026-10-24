/** 成绩计算与页面接线回归：不同跑法不能混合插值，显示必须与排序一致。 */
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');
const read = file => fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
const moduleSource = read('race_scores.js');
const scores = new Function(`${moduleSource}; return raceScores;`)();
const raw = (time, stars, route = null, name = 'X') => ({
    cars: [{ name, ...(stars == null ? {} : { stars }) }], time,
    ...(route ? { sc: true, sc_type: route } : {}),
});
const normalized = entry => Object.assign([entry.cars[0].name], { _raw: entry });

test('精确成绩、线性插值和三位小数取整保持原语义', () => {
    assert.equal(scores.getStarAdjustedScore([{ stars: 3, time: 20.1234 }], 3), 20.1234);
    assert.equal(scores.getStarAdjustedScore([{ stars: 1, time: 25 }, { stars: 4, time: 23 }], 2), 24.333);
    assert.equal(scores.getStarAdjustedScore([], 3), null);
});
test('双向外推仍使用原生产曲线', () => {
    assert.equal(scores.getStarAdjustedScore([{ stars: 6, time: 25 }], 1), +(25 * Math.exp(.00525 * 5 + .001025 * 25)).toFixed(3));
    assert.equal(scores.getStarAdjustedScore([{ stars: 3, time: 20 }], 6), +(20 / Math.exp(.00525 * 3 + .001025 * 9)).toFixed(3));
});
test('不同SC跑法各自估算后取快者，不能跨跑法插值出24秒', () => {
    const rows = [raw(20, 1, '旧跳图'), raw(30, 6, '稳定跳图')];
    const expected = scores.getStarAdjustedScore([{ stars: 1, time: 20 }], 3);
    assert.equal(scores.effectiveTime(rows, 'X', '高手', 3), expected);
    assert.notEqual(expected, 24);
});
test('同一SC跑法的不同星级仍可插值', () => {
    assert.equal(scores.effectiveTime([raw(20, 1, '跳图'), raw(30, 6, '跳图')], 'X', '高手', 3), 24);
});
test('关闭SC及指定跑法时普通成绩仍可参与', () => {
    const rows = [raw(25, 6), raw(20, 6, '旧跳图'), raw(30, 6, '稳定跳图')];
    assert.equal(scores.effectiveTime(rows, 'X', '高手', 6, 'off'), 25);
    assert.equal(scores.effectiveTime(rows, 'X', '高手', 6, '稳定跳图'), 25);
    assert.equal(scores.effectiveTime(rows, 'X', '高手', 6, '旧跳图'), 20);
});
test('理论档多跑法同星取最快值，无有效成绩返回null', () => {
    assert.equal(scores.effectiveTime([raw(20, null, '旧跳图'), raw(30, null, '稳定跳图')], 'X', '理论', 6), 20);
    assert.equal(scores.effectiveTime([raw(null, 6), raw(10, 6, null, 'Y')], 'X', '高手', 6), null);
});
test('原始JSON和页面规范化条目算出相同成绩', () => {
    const rows = [raw(25, 6), raw(20, 6, '跳图')];
    assert.equal(scores.effectiveTime(rows, 'X', '高手', 6), scores.effectiveTime(rows.map(normalized), 'X', '高手', 6));
});

const inline = read('index.html');
const extract = name => {
    const match = inline.match(new RegExp(`^    function ${name}\\([^\\n]*\\) \\{.*?^    \\}`, 'ms'));
    assert.ok(match, `缺少页面函数 ${name}`);
    return match[0];
};
function page(rows, tier = '高手', savedStars = 3) {
    return new Function('rows', 'tier', 'savedStars', `${moduleSource}
        const currentTier = tier; const currentZone = 'zone5';
        const ocMap = {};
        const specialRouteEnabled = {}; const getRouteState = () => 'all';
        const smallMapsByBig = {A:[{name:'B',zone5Entries:rows,zone4Entries:[]}]};
        const starsMap = {X:savedStars};
        const getZoneDefaultStar = () => 6;
        const getStarRange = () => ({min:1,max:6});
        const parseCarGroup = entry => [entry[0]];
        ${['getCarStars','getCarScore','getEffectiveTime','getOriginalGroups'].map(extract).join('\n')}
        return {
            display: getCarScore('A','B','X','zone5'),
            priorityTime: getEffectiveTime(rows,'X',true,'zone5'),
            emptyZone: getOriginalGroups('A','B','zone4'),
            stars: getCarStars('X')
        };`)(rows, tier, savedStars);
}
test('页面理论档显示与排序使用同一个最快成绩', () => {
    const result = page([raw(20, 6, '旧跳图'), raw(30, 6, '稳定跳图')].map(normalized), '理论');
    assert.equal(result.display, 20);
    assert.equal(result.display, result.priorityTime);
});
test('页面高手档显示和排序均不混合不同跑法插值', () => {
    const result = page([raw(20, 1, '旧跳图'), raw(30, 6, '稳定跳图')].map(normalized));
    assert.equal(result.display, result.priorityTime);
    assert.notEqual(result.display, 24);
});
test('四区空档位保留空候选，不回退到五区', () => {
    assert.deepEqual(page([normalized(raw(20, 6))]).emptyZone, []);
});
test('损坏的保存星级回退默认值，合法星级仍正常恢复', () => {
    for (const saved of ['broken', '3', {}, [], null, 0, 7, 2.5, Infinity]) {
        assert.equal(page([], '高手', saved).stars, 6);
    }
    assert.equal(page([], '高手', 3).stars, 3);
});

const ocRaw = (time, stars, route = null, name = 'X') => {
    const entry = raw(time, stars, route, name);
    entry.cars[0].oc = true;
    return entry;
};
test('OC开关按同一车名严格选择，默认关闭且缺OC成绩不回退', () => {
    const rows = [raw(25, 6), ocRaw(20, 6)];
    assert.equal(scores.effectiveTime(rows, 'X', '理论', 6), 25);
    assert.equal(scores.effectiveTime(rows, 'X', '理论', 6, 'all', null, {ocMap:{}}), 25);
    assert.equal(scores.effectiveTime(rows, 'X', '理论', 6, 'all', null, {ocMap:{X:true}}), 20);
    assert.equal(scores.effectiveTime([raw(25, 6)], 'X', '理论', 6, 'all', null, {ocMap:{X:true}}), null);
    assert.equal(scores.effectiveTime([ocRaw(20, 6)], 'X', '理论', 6), null);
    assert.equal(scores.effectiveTime(rows, 'X', '理论', 6, 'all', null, {ocMap:{Y:true}}), 25);
    assert.equal(scores.effectiveTime(rows.map(normalized), 'X', '理论', 6, 'all', null, {ocMap:{X:true}}), 20);
    for (const invalid of [null, 'true', 1]) {
        const malformed = raw(10, 6);
        malformed.cars[0].oc = invalid;
        assert.equal(scores.effectiveTime([malformed, ...rows], 'X', '理论', 6), 25);
        assert.equal(scores.effectiveTime([malformed, ...rows], 'X', '理论', 6, 'all', null, {ocMap:{X:true}}), 20);
    }
});
test('OC和SC独立过滤，同车普通与特殊跑法不能跨状态混入', () => {
    const rows = [raw(25, 6), raw(18, 6, '跳图'), ocRaw(21, 6), ocRaw(20, 6, '滑雪')];
    const ctx = {ocMap:{X:true}};
    assert.equal(scores.effectiveTime(rows, 'X', '理论', 6, 'off', null, ctx), 21);
    assert.equal(scores.effectiveTime(rows, 'X', '理论', 6, 'all', null, ctx), 20);
    assert.equal(scores.effectiveTime(rows, 'X', '理论', 6, '跳图', null, ctx), 21);
    assert.equal(scores.effectiveTime(rows, 'X', '理论', 6, 'all', true, ctx), 20);
    assert.equal(scores.effectiveTime(rows, 'X', '理论', 6, 'all', false, ctx), 21);
    assert.equal(scores.effectiveTime(rows, 'X', '理论', 6), 18);
});
test('高手档星级插值只使用当前OC状态的点', () => {
    const rows = [raw(50, 1), raw(30, 6), ocRaw(22, 1), ocRaw(20, 6)];
    assert.equal(scores.effectiveTime(rows, 'X', '高手', 3), 42);
    assert.equal(scores.effectiveTime(rows, 'X', '高手', 3, 'all', null, {ocMap:{X:true}}), 21.2);
    assert.equal(scores.effectiveTime([raw(50, 1), ocRaw(20, 6)], 'X', '高手', 3, 'all', null, {ocMap:{X:true}}),
        scores.getStarAdjustedScore([{stars:6,time:20}], 3));
});
