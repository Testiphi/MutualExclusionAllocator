'use strict';
(() => {
    function element(tag, text) {
        const node = document.createElement(tag);
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function button(text, click) {
        const node = element('button', text);
        node.type = 'button';
        node.onclick = click;
        return node;
    }

    function link(video) {
        const title = video.tier === '自动' && !video.title.includes('自动')
            ? video.title + '（自动）' : video.title;
        const node = element('a', title);
        node.href = video.url;
        node.target = '_blank';
        node.rel = 'noopener noreferrer';
        return node;
    }

    function detail(video) {
        return [video.car, video.zone, video.tier, video.lap == null ? '' : '视频圈速 ' + video.lap + ' 秒',
            video.part > 1 ? 'P' + video.part : '', video.start ? '从 ' + video.start + ' 秒播放' : '']
            .filter(Boolean).join(' · ');
    }

    function reference(editor) {
        const filters = document.getElementById('filters');
        const main = filters.closest('main');
        const tabs = element('nav');
        tabs.className = 'route-reference-tabs';
        tabs.setAttribute('aria-label', '表格视图');
        const scoreTab = button('成绩表', () => switchView(false));
        const videoTab = button('跑法参考', () => switchView(true));
        scoreTab.setAttribute('aria-pressed', 'true');
        videoTab.setAttribute('aria-pressed', 'false');
        tabs.append(scoreTab, videoTab);
        main.prepend(tabs);
        const section = element('section');
        section.className = 'route-reference';
        section.hidden = true;
        const toolbar = element('div');
        toolbar.className = 'toolbar';
        const server = document.getElementById('server').cloneNode(true);
        server.removeAttribute('id');
        const map = element('input');
        const car = element('input');
        map.type = car.type = 'search';
        const only = element('input');
        only.type = 'checkbox';
        for (const [text, field] of [['服别', server], ['地图搜索', map], ['车辆搜索', car], ['只看有视频的格子', only]]) {
            const label = element('label');
            if (field === only) label.className = 'check';
            label.append(text, field);
            toolbar.append(label);
        }
        const hint = element('p');
        const status = element('p');
        status.setAttribute('role', 'status');
        const wrap = element('div');
        wrap.className = 'sheet-wrap route-reference-grid';
        wrap.tabIndex = 0;
        wrap.setAttribute('role', 'region');
        wrap.setAttribute('aria-label', '跑法参考表');
        const table = element('table');
        table.className = 'route-reference-sheet';
        const head = element('thead');
        const body = element('tbody');
        table.append(head, body);
        wrap.append(table);
        const previous = button('上一组车辆', () => { offset -= pageSize; render(); });
        const next = button('下一组车辆', () => { offset += pageSize; render(); });
        const page = element('span');
        const paging = element('div');
        paging.className = 'paging';
        paging.append(previous, page, next);
        section.append(toolbar, hint, status, wrap, paging);
        main.append(section);
        const dialog = element('dialog');
        const title = element('h2');
        title.id = 'route-reference-title';
        dialog.setAttribute('aria-labelledby', title.id);
        const list = element('ul');
        const edit = button('维护本格视频', () => {
            dialog.close();
            editor.open(target, owner, load);
        });
        dialog.append(title, list, edit, button('关闭', () => dialog.close()));
        document.body.append(dialog);
        let pageSize = 48;
        let matrix, owner, target, scoreScope, offset = 0, ticket = 0;
        const cellKey = (big, small, nick) => JSON.stringify([big, small, nick]);

        function switchView(active) {
            const wasHidden = section.hidden;
            section.hidden = !active;
            main.classList.toggle('show-route-reference', active);
            scoreTab.setAttribute('aria-pressed', String(!active));
            videoTab.setAttribute('aria-pressed', String(active));
            if (active && wasHidden) {
                if (!matrix) server.value = document.getElementById('server').value;
                void load();
            }
        }

        async function load() {
            const epoch = ++ticket;
            matrix = null;
            render();
            status.textContent = '正在加载跑法参考…';
            try {
                const scope = scoreScope?.server === server.value ? scoreScope : {};
                const response = await fetch('/api/route-videos/matrix?' + new URLSearchParams({...scope, server: server.value}));
                if (!response.ok) throw Error('跑法参考加载失败，请切换视图后重试。');
                const data = await response.json();
                if (epoch !== ticket) return;
                pageSize = data.column_limit;
                matrix = data;
                render();
            } catch {
                if (epoch === ticket) status.textContent = '跑法参考加载失败，请切换视图后重试。';
            }
        }

        async function open(big, small, nick) {
            const cell = {server: server.value, big, small, car: nick};
            target = cell;
            title.textContent = small + ' · ' + nick;
            edit.hidden = !owner;
            list.replaceChildren(element('li', '正在读取视频…'));
            dialog.showModal();
            try {
                const {videos} = await videosFor(mapKey(cell.server, cell));
                if (target !== cell || !dialog.open) return;
                const matches = videos.filter(video => video.car === nick);
                list.replaceChildren(...matches.map(video => {
                    const row = element('li');
                    row.append(link(video), element('div', detail(video)));
                    return row;
                }));
                if (!matches.length) list.append(element('li', '本格暂无视频。'));
            } catch {
                if (target === cell && dialog.open) list.replaceChildren(element('li', '视频列表加载失败。'));
            }
        }

        function render() {
            hint.textContent = owner ? '点数字查看视频，点空格可添加视频。' : '点数字查看视频。';
            head.replaceChildren();
            body.replaceChildren();
            wrap.hidden = paging.hidden = true;
            if (!matrix) return;
            const mapQuery = map.value.trim().toLowerCase();
            const carQuery = car.value.trim().toLowerCase();
            const counts = new Map(matrix.counts.map(([big, small, nick, count]) => [cellKey(big, small, nick), count]));
            let maps = matrix.maps.filter(names => names.join(' ').toLowerCase().includes(mapQuery));
            let cars = matrix.cars.filter(names => names.join(' ').toLowerCase().includes(carQuery));
            if (only.checked) {
                cars = cars.filter(([nick]) => maps.some(([big, small]) => counts.has(cellKey(big, small, nick))));
            }
            offset = Math.min(offset, Math.max(0, Math.ceil(cars.length / pageSize) - 1) * pageSize);
            const visible = cars.slice(offset, offset + pageSize);
            if (only.checked) maps = maps.filter(([big, small]) => visible.some(([nick]) => counts.has(cellKey(big, small, nick))));
            if (!maps.length || !visible.length) {
                status.textContent = '当前筛选没有匹配的车图组合。';
                return;
            }
            const header = element('tr');
            table.style.setProperty('--coverage-columns', String(visible.length));
            for (const [label, cls] of [['#', 'row-num'], ['大地图', 'map-col'], ['小地图', 'track-col']]) {
                const th = element('th', label);
                th.className = cls;
                header.append(th);
            }
            for (const [nick] of visible) {
                const th = element('th', nick);
                th.className = 'car-col';
                header.append(th);
            }
            head.append(header);
            for (const [index, [big, small]] of maps.entries()) {
                const row = element('tr');
                for (const [label, cls] of [[index + 1, 'row-num'], [big, 'map-col'], [small, 'track-col']]) {
                    const th = element('th', label);
                    th.className = cls;
                    row.append(th);
                }
                for (const [nick] of visible) {
                    const td = element('td');
                    const count = counts.get(cellKey(big, small, nick)) || 0;
                    td.className = count ? 'filled' : 'empty';
                    if (count || (owner && !only.checked)) {
                        const action = button(count ? count + ' 条' : '', () => {
                            if (count) void open(big, small, nick);
                            else editor.open({server: server.value, big, small, car: nick}, owner, load);
                        });
                        action.className = 'cell';
                        action.setAttribute('aria-label', small + ' · ' + nick + ' · ' + (count ? count + ' 条视频' : '添加视频'));
                        td.append(action);
                    }
                    row.append(td);
                }
                body.append(row);
            }
            previous.disabled = offset === 0;
            next.disabled = offset + pageSize >= cars.length;
            page.textContent = (offset + 1) + '–' + (offset + visible.length) + ' / ' + cars.length + ' 列';
            status.textContent = maps.length + ' 张地图';
            wrap.hidden = paging.hidden = false;
        }

        server.onchange = () => { offset = 0; void load(); };
        map.oninput = car.oninput = only.onchange = () => { offset = 0; render(); };
        return (user, scope) => {
            owner = user?.verified && ['admin', 'superadmin'].includes(user.role) ? user.id : null;
            scoreScope = scope;
            if (!section.hidden) render();
        };
    }

    function editor(call) {
        const toggle = button('维护跑法视频', () => {
            enabled = !enabled;
            updateMode();
            rerender();
        });
        toggle.className = 'primary';
        const mode = element('aside');
        mode.className = 'notice route-video-mode';
        mode.hidden = true;
        const hint = element('p');
        hint.setAttribute('role', 'status');
        mode.append(toggle, hint);
        document.getElementById('filters').before(mode);
        const dialog = element('dialog');
        const heading = element('h2', '维护跑法视频');
        heading.id = 'route-video-heading';
        dialog.setAttribute('aria-labelledby', heading.id);
        const context = element('p');
        const saved = element('ul');
        const form = element('form');
        const raw = element('textarea');
        raw.required = true;
        raw.maxLength = 2500;
        raw.rows = 2;
        const title = element('input');
        title.required = true;
        title.maxLength = 200;
        const tier = element('select');
        const zone = element('select');
        for (const value of ['', '四区', '五区']) {
            const option = element('option', value || '未标分区');
            option.value = value;
            zone.append(option);
        }
        for (const label of ['', '理论', '高手', '普通', '自动']) {
            const option = element('option', label || '不限档位');
            option.value = label;
            tier.append(option);
        }
        const lap = element('input');
        Object.assign(lap, {type: 'number', min: '0.001', max: '3600', step: 'any'});
        for (const [caption, field] of [['B 站链接或分享文案', raw], ['显示标题（可标星级，特殊跑法请写明类型）', title], ['参考分区', zone], ['参考档位', tier], ['视频圈速（秒，选填）', lap]]) {
            const label = element('label');
            label.append(element('span', caption), field);
            label.style.display = 'grid';
            label.style.marginBlock = '8px';
            form.append(label);
        }
        const result = element('p');
        const message = element('p');
        message.setAttribute('role', 'status');
        const submit = element('button', '保存关联');
        submit.type = 'submit';
        const close = button('关闭', () => dialog.close());
        const retry = button('重新读取链接', () => void read());
        form.append(result, message, submit, ' ', retry, ' ', close);
        dialog.append(heading, context, saved, form);
        document.body.append(dialog);
        let enabled = false, rerender, target, account, activeAccount, preview, timer, onChange, busy = false, readId = 0, dialogId = 0;

        function updateMode() {
            toggle.setAttribute('aria-pressed', String(enabled));
            toggle.textContent = enabled ? '退出视频维护' : '维护跑法视频';
            hint.textContent = enabled ? '视频维护已开启。点车辆和地图交叉的格子即可绑定。' :
                '只想添加跑法参考？先开启视频维护，再点格子。直接点空格会进入成绩投稿。';
        }

        function refreshControls() {
            submit.disabled = busy || !preview;
            raw.disabled = busy;
            retry.disabled = busy;
            close.disabled = busy;
        }

        function adminCall(path, payload) {
            return call('POST', '/route-videos/' + path, payload, account);
        }

        async function list() {
            const epoch = dialogId;
            const data = await adminCall('cell', target);
            if (epoch !== dialogId || !dialog.open) return;
            saved.replaceChildren();
            for (const video of data.videos) {
                const row = element('li');
                row.append(link(video), ' ' + detail(video) + ' ',
                    button(video.active ? '停用' : '恢复', async () => {
                        if (busy) return;
                        busy = true;
                        refreshControls();
                        try {
                            await adminCall('visibility', {...target, id: video.id, active: !video.active});
                            onChange?.();
                            await list();
                        } catch (error) {
                            message.textContent = error.message;
                        } finally {
                            busy = false;
                            refreshControls();
                        }
                    }));
                saved.append(row);
            }
        }

        async function read() {
            if (busy || !dialog.open) return;
            clearTimeout(timer);
            const epoch = ++readId;
            preview = null;
            result.replaceChildren();
            refreshControls();
            if (!raw.value.trim()) return;
            message.textContent = '正在读取链接…';
            try {
                const data = await adminCall('preview', {raw: raw.value});
                if (epoch !== readId || !dialog.open) return;
                preview = data;
                if (!title.value.trim()) title.value = data.title ||
                    target.car + ' · ' + target.small + (data.part > 1 ? ' · P' + data.part : ' · 跑法参考');
                result.append(link({...data, title: '预览跳转'}), ' ',
                    data.part > 1 ? 'P' + data.part + ' ' : '', data.start ? '从 ' + data.start + ' 秒播放' : '');
                message.textContent = data.title ? '' : '未读到 B 站标题，已填入可编辑的车图标题。';
            } catch (error) {
                if (epoch === readId && dialog.open) message.textContent = error.message;
            } finally {
                refreshControls();
            }
        }
        raw.oninput = () => {
            readId++;
            preview = null;
            title.value = '';
            result.replaceChildren();
            message.textContent = '';
            refreshControls();
            clearTimeout(timer);
            timer = setTimeout(read, 400);
        };
        dialog.oncancel = event => { if (busy) event.preventDefault(); };
        dialog.onclose = () => { readId++; dialogId++; clearTimeout(timer); };
        form.onsubmit = async event => {
            event.preventDefault();
            if (busy || !preview || !title.value.trim()) return;
            busy = true;
            refreshControls();
            try {
                const {video_id, part, start} = preview;
                await adminCall('bind', {...target, video_id, part, start, title: title.value.trim(),
                    tier: tier.value, zone: zone.value, lap: lap.value === '' ? null : Number(lap.value)});
                message.textContent = '已保存。';
                onChange?.();
                await list();
            } catch (error) {
                message.textContent = error.message;
            } finally {
                busy = false;
                refreshControls();
            }
        };
        const controller = {
            get enabled() { return enabled; },
            setSession(user, render, scope) {
                rerender = render;
                const allowed = user?.verified && ['admin', 'superadmin'].includes(user.role);
                if (!allowed || activeAccount !== user?.id) {
                    enabled = false;
                    if (dialog.open) dialog.close();
                }
                activeAccount = allowed ? user.id : null;
                updateMode();
                mode.hidden = !allowed;
                setReferenceSession(user, scope);
            },
            open(cell, owner, changed) {
                if (busy || dialog.open) return;
                dialogId++;
                target = cell;
                account = owner;
                onChange = changed;
                context.textContent = cell.big + ' / ' + cell.small + ' · ' + cell.car;
                form.reset();
                saved.replaceChildren();
                result.replaceChildren();
                message.textContent = '';
                preview = null;
                refreshControls();
                dialog.showModal();
                void list().catch(error => { if (dialog.open && target === cell) message.textContent = error.message; });
            },
        };
        const setReferenceSession = reference(controller);
        return controller;
    }

    const inFlight = new Map();
    function videosFor(key) {
        if (!inFlight.has(key)) {
            const request = fetch('/api/route-videos?' + key, {signal: AbortSignal.timeout(5000)})
                .then(response => response.ok ? response.json() : Promise.reject(Error('视频列表暂不可用')))
                .finally(() => inFlight.delete(key));
            inFlight.set(key, request);
        }
        return inFlight.get(key);
    }

    function mapKey(server, map) {
        return new URLSearchParams({server, big: map.big, small: map.small}).toString();
    }

    function matchesScope(video, {zone, tier, specialRoutes}) {
        // Older bindings sometimes carry these labels only in the title.
        const titleZones = [...new Set(video.title.match(/[四五]区/g) || [])];
        const videoZone = video.zone || (titleZones.length === 1 ? titleZones[0] : '');
        if (videoZone && videoZone !== zone) return false;

        const automatic = video.tier === '自动' || (!video.tier && /(?<!非)自动/.test(video.title));
        if (automatic !== (tier === '自动')) return false;

        const special = video.title.match(/稳定跳图|旧跳图|新跳图|跳图|滑栏杆|滑雪|跳楼|跳船|挂桥/)?.[0];
        return special ? specialRoutes.includes(special) : specialRoutes.length === 0;
    }

    function showForCar(anchor, server, map, car, scope) {
        if (!anchor || !car) return;
        void videosFor(mapKey(server, map)).then(({videos}) => {
            if (!anchor.isConnected) return;
            const matches = videos.filter(video => video.car === car && matchesScope(video, scope));
            if (!matches.length) return;
            const group = element('div');
            group.className = 'route-video-links';
            if (matches.length === 1) {
                group.append(link(matches[0]));
            } else {
                const more = element('details');
                more.append(element('summary', '跑法视频 ' + matches.length));
                for (const video of matches) more.append(link(video));
                group.append(more);
            }
            anchor.append(group);
        }).catch(() => {});
    }

    globalThis.RacePickRouteVideos = {editor, showForCar};
})();
