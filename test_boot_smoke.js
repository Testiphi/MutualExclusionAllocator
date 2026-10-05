/**
 * 启动冒烟测试：用最小 DOM 桩真实执行 index.html 的内联脚本（含 config.js / api.js / allocator.js），
 * 断言页面能完成启动，且车池与星级规则确实由 cars.json 派生出来。
 *
 * 为什么需要它：车池与星级规则原先硬编码在 index.html，现在改为从 cars.json 派生。
 * 若这段派生被破坏（字段改名、加载顺序写错、条件写反），页面在浏览器里才会白屏，
 * 而纯单元测试发现不了。本测试在不启动浏览器的前提下覆盖这条路径。
 *
 * 只读、不联网。运行：node test_boot_smoke.js（退出码非 0 表示失败）
 */
const fs = require('node:fs');
const path = require('node:path');

const REPO = __dirname;
const read = file => fs.readFileSync(path.join(REPO, file), 'utf8');

const failures = [];
const check = (ok, message) => { if (!ok) failures.push(message); return ok; };

// ---------------- 最小 DOM 桩 ----------------
const nodes = new Map();
const noop = new Proxy(function () { return undefined; }, {
    get: (target, key) => (key === 'length' ? 0 : key === Symbol.toPrimitive ? () => '' : noop),
    apply: () => undefined,
});
const innerHtmlWrites = [];

function node(id) {
    if (nodes.has(id)) return nodes.get(id);
    const store = {
        id, innerHTML: '', textContent: '', value: '', disabled: false, checked: false,
        style: {}, dataset: {}, children: [], parentNode: null, firstChild: null, options: [],
        classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    };
    const proxy = new Proxy(store, {
        get(target, key) {
            if (key in target) return target[key];
            if (key === 'appendChild' || key === 'insertBefore' || key === 'removeChild') return child => child;
            if (key === 'addEventListener' || key === 'removeEventListener') return () => {};
            if (key === 'querySelectorAll') return () => [];
            if (key === 'querySelector') return () => node(id + ':child');
            if (key === 'closest') return () => null;
            if (key === 'getAttribute') return () => null;
            if (key === 'setAttribute' || key === 'removeAttribute') return () => {};
            if (key === 'remove' || key === 'focus' || key === 'blur' || key === 'click') return () => {};
            return noop;
        },
        set(target, key, value) {
            if (key === 'innerHTML') innerHtmlWrites.push({ id, value: String(value) });
            target[key] = value;
            return true;
        },
    });
    nodes.set(id, proxy);
    return proxy;
}

globalThis.document = {
    getElementById: id => node(id),
    createElement: tag => node('new:' + tag),
    createTextNode: () => node('text'),
    addEventListener: () => {},
    querySelectorAll: () => [],
    querySelector: () => null,
    body: node('body'),
    documentElement: node('html'),
};
globalThis.window = globalThis;

const storage = new Map();
globalThis.localStorage = {
    getItem: key => (storage.has(key) ? storage.get(key) : null),
    setItem: (key, value) => storage.set(key, String(value)),
    removeItem: key => storage.delete(key),
    clear: () => storage.clear(),
};
globalThis.requestAnimationFrame = callback => setTimeout(callback, 0);
globalThis.fetch = async url => {
    const file = path.join(REPO, String(url).replace(/^\.?\//, ''));
    if (!fs.existsSync(file)) return { ok: false, status: 404, json: async () => ({}) };
    const text = fs.readFileSync(file, 'utf8');
    return { ok: true, status: 200, json: async () => JSON.parse(text), text: async () => text };
};

// ---------------- 组装（浏览器里三个 <script> 共享同一全局作用域）----------------
const inline = read('index.html').match(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/)[1];
const callPattern = /initApp\(\);/;
if (!callPattern.test(inline)) {
    console.error('❌ index.html 内联脚本里找不到 initApp() 调用点');
    process.exit(1);
}
const instrumented = inline.replace(callPattern,
    'globalThis.__probe = () => ({ zone5Cars, zone4Cars, rules: CAR_STAR_RULES,' +
    ' carStats, nickToName, rdata: RACE_DATA });\n    initApp();');

const warnings = [];
const realWarn = console.warn;
const realError = console.error;
console.warn = (...args) => warnings.push('warn: ' + args.join(' '));
console.error = (...args) => warnings.push('error: ' + args.join(' '));

let syncError = null;
try {
    new Function([read('config.js'), read('app_state.js'), read('api.js'), read('allocator.js'), read('race_scores.js'), instrumented].join('\n;\n'))();
} catch (error) {
    syncError = error.message;
}

setTimeout(() => {
    console.warn = realWarn;
    console.error = realError;

    check(!syncError, `启动时同步抛错: ${syncError}`);
    check(warnings.length === 0, `启动期出现告警/错误: ${JSON.stringify(warnings)}`);
    const bootError = innerHtmlWrites.filter(x => x.value.includes('加载失败'));
    check(bootError.length === 0, `页面进入「加载失败」分支: ${JSON.stringify(bootError)}`);

    const probe = globalThis.__probe;
    if (check(typeof probe === 'function', '内联脚本未执行到 initApp()')) {
        const state = probe();
        check(state.zone5Cars.length === 76, `zone5Cars 应为 76，实际 ${state.zone5Cars.length}`);
        check(state.zone4Cars.length === 50, `zone4Cars 应为 50，实际 ${state.zone4Cars.length}`);
        check(Object.keys(state.rules).length === 72,
            `CAR_STAR_RULES 应为 72 车，实际 ${Object.keys(state.rules).length}`);
        check(state.zone5Cars.includes('919') && state.zone5Cars.includes('dose'),
            'zone5Cars 应含 919 与 dose');
        check(state.zone4Cars.includes('919') && state.zone4Cars.includes('biome'),
            'zone4Cars 应含 919 与 biome');
        check(JSON.stringify(state.rules.dose) === '{"min":3,"max":6,"zone4Max":4}',
            `dose 星级规则不符: ${JSON.stringify(state.rules.dose)}`);
        check(Object.keys(state.carStats).length === 346, 'carStats 应为 346 条');
        check(state.rdata && state.rdata.tracks.length === 83, 'RACE_DATA 应为 83 条赛道');
    }

    if (failures.length) {
        console.error('❌ 启动冒烟测试失败:');
        for (const message of failures) console.error('   - ' + message);
        process.exitCode = 1;
    } else {
        console.log('✅ 启动冒烟测试通过：页面完成启动，车池 76/50、星级规则 72 车均从 cars.json 派生');
    }
}, 2500);
