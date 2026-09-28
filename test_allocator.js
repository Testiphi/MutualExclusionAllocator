/**
 * allocator.js 边界测试。
 *
 * 运行：node --test test_allocator.js
 *
 * allocator.js 是非 CommonJS 的 IIFE（把模块挂在局部 `const allocator` 上），
 * 因此这里用 Function 构造器求值后取出该变量——不修改被测文件，也不引入依赖。
 */
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const assert = require('node:assert/strict');

const SOURCE = fs.readFileSync(path.join(__dirname, 'allocator.js'), 'utf8');
const allocator = new Function(`${SOURCE}; return allocator;`)();
const { generateParetoSchemes } = allocator;

const NO_CAR = 99;

/**
 * 构造单张图的候选数据。
 * groups 为候选组数组（每组是若干车名），组索引即该组内车辆的优先级；越靠前越优。
 */
function mapOf(...groups) {
    const carToPriority = new Map();
    groups.forEach((group, index) => {
        for (const car of group) {
            if (!carToPriority.has(car)) carToPriority.set(car, index);
        }
    });
    return { groups, carToPriority };
}

const vectorsOf = schemes => schemes.map(s => s.vector.join(',')).sort();
const run = (maps, owned, limit = 25) =>
    generateParetoSchemes(maps, new Set(owned), limit, NO_CAR);

/** 互斥性：同一辆车不得在同一方案里出现两次 */
function assertNoReuse(schemes) {
    for (const scheme of schemes) {
        const assigned = scheme.assignment.filter(Boolean);
        assert.equal(new Set(assigned).size, assigned.length,
            `方案重复用车: ${JSON.stringify(scheme.assignment)}`);
    }
}

/** 帕累托性：返回的向量两两互不支配 */
function assertMutuallyNonDominated(schemes) {
    for (const left of schemes) {
        for (const right of schemes) {
            if (left === right) continue;
            const atLeastOneBetter = left.vector.some((v, i) => v < right.vector[i]);
            const noWorse = left.vector.every((v, i) => v <= right.vector[i]);
            assert.ok(!(noWorse && atLeastOneBetter),
                `被支配的方案混入前沿: ${left.vector} 支配 ${right.vector}`);
        }
    }
}

// ---------------------------------------------------------------- 基本边界

test('无地图时返回空数组', () => {
    assert.deepEqual(run([], ['A']), []);
});

test('单图有候选时恰好一个方案', () => {
    const schemes = run([mapOf(['A'], ['B'])], ['A', 'B']);
    assert.deepEqual(vectorsOf(schemes), ['0']);
    assert.deepEqual(schemes[0].assignment, ['A']);
});

test('单图无候选时留空', () => {
    const schemes = run([mapOf()], ['A']);
    assert.deepEqual(vectorsOf(schemes), [String(NO_CAR)]);
    assert.deepEqual(schemes[0].assignment, [null]);
});

test('候选组存在但车辆均未拥有时留空', () => {
    const schemes = run([mapOf(['A'], ['B'])], []);
    assert.deepEqual(vectorsOf(schemes), [String(NO_CAR)]);
});

test('空候选组不产生方案也不抛错', () => {
    // 优先级取「组索引」，故第 0 组为空时，第 1 组的车优先级是 1
    const schemes = run([mapOf([], ['A'])], ['A']);
    assert.deepEqual(vectorsOf(schemes), ['1']);
});

// ------------------------------------------------------- 留空枚举（本次修复点）

test('两行都只能选同一辆车时，两个方向都必须枚举', () => {
    const both = [mapOf(['A']), mapOf(['A'])];
    const schemes = run(both, ['A']);
    assert.deepEqual(vectorsOf(schemes), [`0,${NO_CAR}`, `${NO_CAR},0`]);
    assertMutuallyNonDominated(schemes);
    assertNoReuse(schemes);
});

test('三行两车时给出全部 6 个非支配方案', () => {
    const rows = [mapOf(['A'], ['B']), mapOf(['A'], ['B']), mapOf(['A'], ['B'])];
    const schemes = run(rows, ['A', 'B'], 50);
    assert.equal(schemes.length, 6);
    assert.deepEqual(vectorsOf(schemes),
        ['0,1,99', '0,99,1', '1,0,99', '1,99,0', '99,0,1', '99,1,0'].sort());
    assertMutuallyNonDominated(schemes);
    assertNoReuse(schemes);
});

test('车辆充足时留空分支全部被支配，不出现在前沿', () => {
    // 优先级按图独立计算，两图各自的最优车都是 0
    const schemes = run([mapOf(['A']), mapOf(['B'])], ['A', 'B']);
    assert.deepEqual(vectorsOf(schemes), ['0,0']);
});

test('交换行序不改变帕累托解集合（不存在行序优先权）', () => {
    const first = mapOf(['A']);
    const second = mapOf(['A']);
    assert.deepEqual(vectorsOf(run([first, second], ['A'])), vectorsOf(run([second, first], ['A'])));
});

test('稀缺车场景下两侧留空都可达，不偏向任何一行', () => {
    // 3 行、1 辆车：留空可以落在任意一行
    const rows = [mapOf(['A']), mapOf(['A']), mapOf(['A'])];
    const schemes = run(rows, ['A'], 50);
    assert.deepEqual(vectorsOf(schemes),
        [`0,${NO_CAR},${NO_CAR}`, `${NO_CAR},0,${NO_CAR}`, `${NO_CAR},${NO_CAR},0`].sort());
});

// ---------------------------------------------------------------- 不变量

test('互斥与帕累托不变量在混合候选下成立', () => {
    const rows = [
        mapOf(['A', 'B'], ['C']),
        mapOf(['B'], ['A', 'D']),
        mapOf(['C'], ['A']),
    ];
    const schemes = run(rows, ['A', 'B', 'C', 'D'], 100);
    assert.ok(schemes.length > 0);
    assertNoReuse(schemes);
    assertMutuallyNonDominated(schemes);
});

test('重叠候选组属退化输入：同一辆车可从多个组被选中', () => {
    // 实际输入约定：getOriginalGroups 为每辆车各建一个单车组，故候选组互不重叠。
    // 这里锁定重叠时的行为（同车可达两次 → 向量重复的方案），避免日后被误判成回归。
    const schemes = run([mapOf(['A'], ['B', 'A'])], ['A', 'B']);
    assert.deepEqual(vectorsOf(schemes), ['0', '0']);
});

test('退化输入：carToPriority 缺项时按哨兵值参与比较', () => {
    // prepareMapCandidates 会为组内每辆车建表，故实际调用不会出现缺项；
    // 此处只是锁定兜底行为：有车可得与留空同为哨兵值，两者互不支配，都会留在前沿。
    const single = { groups: [['A']], carToPriority: new Map() };
    const schemes = run([single], ['A']);
    assert.deepEqual(vectorsOf(schemes), [String(NO_CAR), String(NO_CAR)]);
    assert.deepEqual(schemes.map(s => s.assignment[0]).sort(), ['A', null].sort());
});

// ---------------------------------------------------------------- 截断与排序

test('按总优先级升序截断，且不超过上限', () => {
    const rows = [mapOf(['A'], ['B']), mapOf(['A'], ['B']), mapOf(['A'], ['B'])];
    const schemes = run(rows, ['A', 'B'], 3);
    assert.equal(schemes.length, 3);
    const totals = schemes.map(s => s.vector.reduce((sum, v) => sum + v, 0));
    assert.deepEqual(totals, [...totals].sort((a, b) => a - b));
    // 3 张图只有 2 辆车：每个完整方案都必然留空一张图，6 个方案总分相同，靠字典序决胜
    assert.deepEqual(vectorsOf(schemes), ['0,1,99', '0,99,1', '1,0,99'].sort());
});

test('上限为 0 时返回空数组', () => {
    assert.deepEqual(run([mapOf(['A'])], ['A'], 0), []);
});
