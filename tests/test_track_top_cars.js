const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');
const read = f => fs.readFileSync(path.join(__dirname, '..', f), 'utf8');
const html = read('index.html');
const inline = html.match(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/)[1];
function element() {
    return {
        dataset: {}, children: [], open: false, hidden: false,
        textContent: '', append(...children) { this.children.push(...children); },
        appendChild(child) { this.children.push(child); },
        replaceChildren() { this.children = []; },
    };
}
function panel() {
    const p = element(), nodes = {};
    p.querySelector = selector => nodes[selector] ||= element();
    return p;
}
const entry = (name, time, stars = 6, route) => ({
    cars: [{name, stars}], ...(time == null ? {} : {time}),
    ...(route ? {sc: true, sc_type: route} : {}),
});
function page() {
    const panels = [panel(), panel()], out = {};
    const setup = `
        out.configure = (zone, tier, owned, stars, route) => {
            currentZone=zone; currentTier=tier; selectedCars=new Set(owned); starsMap=stars;
            specialRouteEnabled={'大/图':route}; buildMapIndex();
        };
        out.load = data => {
            RACE_DATA=data; zone5Cars=['A','B','C','D','E']; zone4Cars=['B','C'];
            CAR_STAR_RULES={A:{min:1,max:6},B:{min:1,max:6,zone4Max:3}};
        };
        out.top = () => {
            const candidate=prepareMapCandidates([{big:'大',small:'图'}],currentZone)[0];
            return getTopCars(candidate,new Set(getCurrentCarList().filter(c=>selectedCars.has(c))),'大','图',currentZone);
        };
        topCarPanels=panels;
        out.render = maps => renderTopCars(maps,prepareMapCandidates(maps,currentZone),
            new Set(getCurrentCarList().filter(c=>selectedCars.has(c))));
    `;
    new Function('document', 'out', 'panels', 'APP_CONFIG',
        read('app_state.js') + read('race_scores.js') + inline.replace('initApp();', setup))(
        {getElementById: element, createElement: element}, out, panels,
        {server:'cn',storageKeys:{guestDraft:'racepick.guest-draft.v1'}});
    const expert = [entry('A', 20, 6), entry('A', 24, 3), entry('A', 18, 6, '跳图'),
        entry('A', 19, 6, '滑栏杆'), entry('B', 21), entry('C', 21), entry('D', 22),
        entry('E', 23), entry('outside', 1)];
    const tiers = {'高手': expert, '理论': expert, '普通': [entry('A'),entry('B'),entry('C'),entry('D')],
        '自动': [entry('C'),entry('B')]};
    out.load({tracks:[{大地图:'大',小地图:'图',五区:tiers,四区:tiers}]});
    return {out, panels};
}
test('real page candidates: unique owned zone cars, stable ties and top-three cap', () => {
    const {out} = page();
    out.configure('zone5','高手',['A','B','C','D','outside'],{},'all');
    assert.deepEqual(out.top().map(x=>[x.car,x.score]),[['A',18],['B',21],['C',21]]);
    out.configure('zone5','高手',['B','D'],{},'all');
    assert.deepEqual(out.top().map(x=>x.car),['B','D']);
    out.configure('zone4','高手',['A','B','C','outside'],{B:6},'off');
    assert.deepEqual(new Set(out.top().map(x=>x.car)),new Set(['B','C']));
    assert.equal(out.top().find(x=>x.car==='B').stars,3);
});
test('route off/specific type and user stars change both score and order', () => {
    const {out} = page();
    out.configure('zone5','高手',['A','B','C'],{},'off');
    assert.equal(out.top()[0].score,20);
    out.configure('zone5','高手',['A','B','C'],{},'滑栏杆');
    assert.equal(out.top()[0].score,19);
    out.configure('zone5','高手',['A','B','C'],{A:3},'off');
    assert.deepEqual(out.top().map(x=>[x.car,x.score]),[['B',21],['C',21],['A',24]]);
    out.configure('zone5','理论',['A'],{A:3},'off');
    assert.deepEqual(out.top(),[{car:'A',stars:null,score:20}]);
});
test('normal/auto retain candidate order and explicitly show missing scores', () => {
    const {out,panels} = page();
    for (const tier of ['普通','自动']) {
        out.configure('zone5',tier,['A','B','C'],{},'all');
        assert.ok(out.top().every(x=>x.score===null));
        out.render([{big:'大',small:'图',originalIndex:0}]);
        assert.match(panels[0].querySelector('summary').textContent,/优先候选/);
        assert.ok(panels[0].querySelector('.track-top-list').children.every(li=>li.children[1].textContent==='暂无成绩'));
    }
    assert.deepEqual(out.top().map(x=>x.car),['C','B']);
});
test('collapsed initially, preserve same-map expansion, clear stale rows and empty garage', () => {
    const {out,panels} = page(), maps=[{big:'大',small:'图',originalIndex:1}];
    out.configure('zone5','高手',['A','B'],{},'all');
    out.render(maps);
    assert.equal(panels[0].hidden,true);
    assert.equal(panels[1].hidden,false);
    assert.equal(panels[1].open,false);
    panels[1].open=true;
    out.configure('zone5','高手',[],{},'off');
    out.render(maps);
    assert.equal(panels[1].open,true);
    assert.equal(panels[1].querySelector('.track-top-list').children.length,0);
    assert.equal(panels[1].querySelector('.track-top-empty').hidden,false);
    out.render([]);
    assert.equal(panels[1].hidden,true);
    assert.equal(panels[1].open,false);
    out.render(maps);
    assert.equal(panels[1].open,false);
});
test('same car can be referenced in multiple rows; references do not reserve it', () => {
    const {out,panels} = page();
    out.configure('zone5','高手',['A'],{},'all');
    out.render([{big:'大',small:'图',originalIndex:0},{big:'大',small:'图',originalIndex:1}]);
    for(const p of panels) assert.equal(p.querySelector('.track-top-list').children[0].children[0].textContent,'A ★6');
    assert.deepEqual(out.top().map(x=>x.car),['A']);
});
test('garage tag clicks refresh references immediately without starting allocation', () => {
    const fn = html.match(/^    function onCarTagClick\([^\n]*\) \{.*?^    \}/ms)[0];
    const result = new Function(`
        const selectedCars=new Set(['A']), snapshots=[];
        const saveGarage=()=>{},updateGarageUI=()=>{},renderCarTags=()=>{};
        const refreshTopCars=()=>snapshots.push([...selectedCars]);
        ${fn}
        const event={target:{closest:()=>({dataset:{carNick:'A'}})}};
        onCarTagClick(event); onCarTagClick(event);
        return snapshots;
    `)();
    assert.deepEqual(result,[[],['A']]);
});
