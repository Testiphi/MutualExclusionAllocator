'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../route_videos.js'), 'utf8');
const map = {big: '古老斗技场', small: '偏僻小道'};
const entries = [
    {car: '9x8', title: '9x8 偏僻小道 19.8', tier: '自动'},
    {car: '9x8', title: '9x8 偏僻小道 19.169'},
    {car: '9x8', title: '9x8 四区参考', zone: '四区'},
    {car: '9x8', title: '9x8 五区参考'},
    {car: '9x8', title: '9x8（新跳图）'},
    {car: '9x8', title: '9x8（旧跳图）'},
    {car: '9x8', title: '9x8（自动）'},
    {car: '帕梅', title: '帕梅 偏僻小道 19.022（跳图）'},
];

function element(tag) {
    return {tag, isConnected: true, children: [], append(...children) { this.children.push(...children); }};
}

async function render(tier, zone, specialRoutes, car = '9x8', connected = true) {
    const context = {
        URLSearchParams, AbortSignal,
        document: {createElement: element},
        fetch: async url => {
            const params = new URL(url, 'http://localhost').searchParams;
            assert.equal(params.get('server'), 'cn');
            assert.equal(params.get('small'), map.small);
            return {ok: true, json: async () => ({videos: entries})};
        },
    };
    vm.runInNewContext(source, context);
    const anchor = element('li');
    context.RacePickRouteVideos.showForCar(anchor, 'cn', map, car, {tier, zone, specialRoutes});
    anchor.isConnected = connected;
    await new Promise(resolve => setImmediate(resolve));
    return anchor.children[0]?.children[0];
}

test('manual tiers share videos and automatic mode uses explicit automatic references', async () => {
    for (const tier of ['普通', '高手', '理论']) {
        const group = await render(tier, '五区', []);
        assert.equal(group.tag, 'details');
        assert.equal(group.open, undefined);
        assert.deepEqual(group.children.map(node => node.textContent),
            ['跑法视频 2', '9x8 偏僻小道 19.169', '9x8 五区参考']);
    }
    const automatic = await render('自动', '五区', []);
    assert.deepEqual(automatic.children.map(node => node.textContent),
        ['跑法视频 2', '9x8 偏僻小道 19.8（自动）', '9x8（自动）']);
});

test('only enabled special routes are shown, with no fallback to normal links', async () => {
    const oldJump = await render('普通', '四区', ['旧跳图']);
    assert.equal(oldJump.tag, 'a');
    assert.equal(oldJump.textContent, '9x8（旧跳图）');

    const both = await render('普通', '五区', ['新跳图', '旧跳图']);
    assert.deepEqual(both.children.map(node => node.textContent),
        ['跑法视频 2', '9x8（新跳图）', '9x8（旧跳图）']);

    assert.equal(await render('普通', '五区', ['滑雪']), undefined);
    assert.equal(await render('普通', '五区', [], '帕梅'), undefined);
});

test('detached results stay empty', async () => {
    const jump = await render('普通', '五区', ['跳图'], '帕梅');
    assert.equal(jump.tag, 'a');
    assert.equal(jump.textContent, '帕梅 偏僻小道 19.022（跳图）');
    assert.equal(await render('普通', '五区', ['跳图'], '帕梅', false), undefined);
});
