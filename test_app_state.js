const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');
const read = name => fs.readFileSync(path.join(__dirname, name), 'utf8');
const source = read('app_state.js');
const state = new Function(`${source};return appState;`)();
const apiSource = read('config.js') + source + read('api.js');
const apiFor = storage => new Function('localStorage', `${apiSource};return api;`)(storage);
test('合法空车库保持为空，已移出车池的车过滤掉', () => {
    assert.equal(state.garage([]).size, 0);
    assert.deepEqual([...state.garage(['X', 'Y', 'X'], new Set(['X']))], ['X']);
});
test('损坏的车库必须报错，不能变成字符集合或空车库', () => {
    for (const value of ['ssc', {}, null, [1], ['X', null]]) {
        assert.throws(() => state.garage(value));
    }
});
test('不存在的SC类型回到all，合法选择与off保留', () => {
    assert.equal(state.route('新跳图', ['旧跳图', '稳定跳图']), 'all');
    assert.equal(state.route('旧跳图', ['旧跳图']), '旧跳图');
    assert.equal(state.route('off', []), 'off');
});
function scheduler() {
    const pending = [], published = [], errors = [], finished = [];
    const tasks = state.createScheduler(callback => pending.push(callback));
    const submit = (value, compute = () => value) => tasks.run({
        compute, publish: result => published.push(result), onError: error => errors.push(error),
        onStart() {}, onFinish: () => finished.push(value),
    });
    return { pending, published, errors, finished, tasks, submit };
}
test('快速切换只计算并发布最新任务', () => {
    const s = scheduler(); let obsoleteCalls = 0;
    s.submit('old', () => { obsoleteCalls++; return 'old'; });
    s.submit('new'); s.pending.forEach(callback => callback());
    assert.equal(obsoleteCalls, 0);
    assert.deepEqual(s.published, ['new']);
    assert.deepEqual(s.finished, ['new']);
});
test('清空选择取消旧任务，旧结果不会回写', () => {
    const s = scheduler(); s.submit('old'); s.tasks.cancel(); s.pending[0]();
    assert.deepEqual(s.published, []);
});
test('计算和发布失败都通知错误并执行收尾', () => {
    const s = scheduler(); s.submit('fail', () => { throw Error('compute'); }); s.pending[0]();
    assert.equal(s.errors[0].message, 'compute'); assert.deepEqual(s.finished, ['fail']);
    let finished = false, error;
    state.createScheduler(callback => callback()).run({
        compute: () => 1, publish: () => { throw Error('render'); },
        onStart() {}, onError: e => { error = e; }, onFinish: () => { finished = true; },
    });
    assert.equal(error.message, 'render'); assert.equal(finished, true);
});
test('存储缺失和损坏可区分，损坏记录不被自动写入', async () => {
    let writes = 0;
    const storage = {getItem: () => null, setItem: () => writes++};
    assert.equal(await apiFor(storage).loadGarage(), null);
    storage.getItem = () => '"ssc"';
    await assert.rejects(apiFor(storage).loadGarage());
    assert.equal(writes, 0);
});
test('存储写入失败会返回失败而不是假装成功', async () => {
    const api = apiFor({setItem: () => { throw Error('quota'); }});
    await assert.rejects(api.saveGarage(new Set(['X'])), /quota/);
    assert.throws(() => api.savePref('stars', {}), /quota/);
});
const html = read('index.html');
const fn = name => html.match(new RegExp(`^    (?:async )?function ${name}\\([^\\n]*\\) \\{.*?^    \\}`, 'ms'))[0];
test('真实页面清空选择后不会发布排队的旧结果', () => {
    const result = new Function(`${source}
        const raf=[],timers=[],published=[];
        let maps=[{big:'A',small:'B',index:0}],currentBestSchemes=[];
        const getCurrentValidMaps=()=>maps;
        const loadingOverlay={classList:{add(){},remove(){}}};
        const schemeSelect={innerHTML:'',appendChild(){},disabled:false};
        const schemeCountBadge={},resultGrid={},document={createElement:()=>({})};
        const requestAnimationFrame=f=>raf.push(f),setTimeout=f=>timers.push(f);
        const prepareMapCandidates=m=>m,getCurrentCarList=()=>['X'],selectedCars=new Set(['X']);
        const currentZone='zone5',SCHEME_LIMIT=25,NO_CAR_PRIORITY=99,ROWS=5;
        const allocator={generateParetoSchemes:()=>[{assignment:['X'],vector:[0]}]};
        const mapSchemesToRows=s=>s,updateUIWithSchemes=s=>published.push(s);
        const computation=appState.createScheduler(f=>requestAnimationFrame(()=>setTimeout(f,0)));
        const computationError=e=>{throw e;};
        ${fn('computeAndDisplay')}
        computeAndDisplay(); maps=[]; computeAndDisplay();
        raf.forEach(f=>f()); timers.forEach(f=>f());
        return published;`)();
    assert.deepEqual(result, []);
});
test('真实页面保存失败显示通知，后续保存成功清除通知', async () => {
    const result = await new Function(`
        const storageFailures=new Map(), notice={};
        const document={getElementById:()=>notice};
        const APP_CONFIG={storageKeys:{garage:'garage',zoneMode:'zone'}};
        let fail=true; const selectedCars=new Set(['X']),currentZone='zone5';
        const api={saveGarage:async()=>{if(fail)throw Error('quota');},savePref(){}};
        ${['storageResult','savePreference','saveZoneMode','saveGarage'].map(fn).join('\n')}
        return (async()=>{await saveGarage();const first={...notice};fail=false;await saveGarage();return {first,last:notice};})();`)();
    assert.equal(result.first.hidden, false);
    assert.match(result.first.textContent, /车库未能保存/);
    assert.equal(result.last.hidden, true);
});
test('真实页面损坏车库读取保留原存储，不自动全选并保存', async () => {
    const result = await new Function(`
        const selectedCars=new Set();let currentZone='zone5',saves=0;
        const APP_CONFIG={storageKeys:{garage:'garage',zoneMode:'zone'}};
        const api={loadGarage:async()=>{throw Error('bad');},loadPref:()=>null};
        const zone5Cars=['X'],zone4Cars=['X']; const notices=[];
        const storageResult=(key,message)=>notices.push(message);
        const saveGarage=()=>saves++,getCurrentCarList=()=>['X'];
        ${fn('loadGarage')}
        return loadGarage().then(()=>({cars:[...selectedCars],saves,notices}));`)();
    assert.deepEqual(result.cars, []);assert.equal(result.saves, 0);
    assert.match(result.notices[0], /车库读取失败/);
});
test('真实页面SC状态切到不含原类型的区档时恢复默认', () => {
    const result = new Function(`${source}
        const currentZone='zone5';let currentTier='理论';
        const specialRouteEnabled={'A/B':'新跳图'};
        const RACE_DATA={tracks:[{大地图:'A',小地图:'B',五区:{
            理论:[{sc:true,sc_type:'新跳图'}],高手:[{sc:true,sc_type:'旧跳图'}]}}]};
        ${fn('getRouteState')}
        const theory=getRouteState('A','B');currentTier='高手';
        return {theory,expert:getRouteState('A','B'),stored:specialRouteEnabled['A/B']};`)();
    assert.deepEqual(result, {theory:'新跳图',expert:'all',stored:'all'});
});
