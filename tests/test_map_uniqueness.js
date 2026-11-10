'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
const functions = ['refreshBigMaps', 'updateSmallMapSelect', 'getCurrentValidMaps'].map(name =>
    html.match(new RegExp('^    function ' + name + '\\([^\\n]*\\) \\{.*?^    \\}', 'ms'))[0]).join('\n');

function select(value) {
    return {
        value, disabled: false, options: [],
        set innerHTML(_) { this.value = ''; this.options = []; },
        appendChild(option) { this.options.push(option); },
    };
}

function page(bigs, smalls) {
    const bigSelects = bigs.map(select);
    const smallSelects = smalls.map(select);
    const source = [
        'const ROWS = bigSelects.length; let mapSelectionRevision = 0;',
        "let bigMapList = ['A', 'B', 'C'];",
        "const smallMapsByBig = {A: [{name:'A1'}, {name:'A2'}], B: [{name:'B1'}], C: [{name:'C1'}]};",
        functions,
        'return {bigSelects, smallSelects, refreshBigMaps, getCurrentValidMaps, revision: () => mapSelectionRevision,',
        'replaceCatalog: next => { bigMapList = next; refreshBigMaps(); }};',
    ].join('\n');
    return new Function('bigSelects', 'smallSelects', 'document', source)(
        bigSelects, smallSelects, {createElement: () => ({value: ''})});
}

test('normal map rebuild preserves slots and disables used regions elsewhere', () => {
    const p = page(['A', '', 'B'], ['A2', '', 'B1']);
    p.refreshBigMaps();
    assert.deepEqual(p.getCurrentValidMaps(), [
        {big:'A', small:'A2', originalIndex:0}, {big:'B', small:'B1', originalIndex:2},
    ]);
    assert.equal(p.bigSelects[1].options.find(option => option.value === 'A').disabled, true);
    assert.equal(p.bigSelects[0].options.find(option => option.value === 'A').disabled, false);
    assert.equal(p.revision(), 0);
});

test('solver clears later duplicates with different small maps or an incomplete first slot', () => {
    for (const first of ['A1', '']) {
        const p = page(['A', 'A', 'C'], [first, 'A2', 'C1']);
        const expected = [{big:'C', small:'C1', originalIndex:2}];
        if (first) expected.unshift({big:'A', small:'A1', originalIndex:0});
        assert.deepEqual(p.getCurrentValidMaps(), expected);
        assert.equal(p.bigSelects[1].value, '');
        assert.equal(p.smallSelects[1].disabled, true);
        assert.equal(p.revision(), 1);
        assert.deepEqual(p.getCurrentValidMaps(), expected);
        assert.equal(p.revision(), 1);
    }
});

test('catalog rebuild clears unavailable regions and duplicates without shifting slots', () => {
    const p = page(['A', 'B', 'B', 'C'], ['A1', 'B1', 'B1', 'C1']);
    p.replaceCatalog(['B', 'C']);
    assert.deepEqual(p.getCurrentValidMaps(), [
        {big:'B', small:'B1', originalIndex:1}, {big:'C', small:'C1', originalIndex:3},
    ]);
    assert.equal(p.smallSelects[0].disabled, true);
    assert.equal(p.smallSelects[2].disabled, true);
});
