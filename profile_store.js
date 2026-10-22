/* Account profile state machine. No DOM or authentication tokens in persistent storage. */
(function(root) {
    const copy = value => JSON.parse(JSON.stringify(value));
    function create({request, storage, userId, notify = () => {}, autoSave = false}) {
        const key = 'racepick.account-draft.v1.' + userId;
        let profile = null, revision = 0, generation = 0, dirty = false;
        let pending = null, frozen = false, status = 'loading', error = '';
        let conflict = false;
        function emit(state, message = '') { status = state; error = message; notify({status, error, dirty}); }
        function persist() {
            storage.setItem(key, JSON.stringify({revision, profile}));
        }
        function clearDraft() { storage.removeItem(key); }
        async function init() {
            const remote = await request('GET', '/me/profile');
            revision = remote.revision; profile = remote.profile;
            const draft = storage.getItem(key);
            if (draft !== null) {
                let saved;
                try { saved = JSON.parse(draft); } catch { throw new Error('账号草稿损坏；原草稿已保留，请先导出或清理本会话的草稿'); }
                if (!saved || !Number.isInteger(saved.revision) || !saved.profile || !Array.isArray(saved.profile.cars) || !saved.profile.stars || typeof saved.profile.stars !== 'object' || Array.isArray(saved.profile.stars)) {
                    throw new Error('账号草稿格式不正确；原草稿已保留');
                }
                profile = saved.profile; dirty = true;
                conflict = saved.revision !== revision;
                // Keep original base revision; retries must not silently overwrite newer server data.
                revision = saved.revision;
                emit(conflict ? 'conflict' : 'unsaved', '已恢复本窗口的未保存草稿，请确认后重试或加载账号资料');
            } else emit('saved');
        }
        function update(value) {
            if (frozen) throw new Error('账号正在退出，不能继续修改');
            profile = copy(value); generation++; dirty = true;
            try { persist(); } catch { emit('error', '本窗口草稿无法保存，请勿关闭页面，点击重试'); return; }
            if (conflict) { emit('conflict','账号资料存在冲突，请选择加载账号资料或覆盖'); return; }
            emit(pending?'saving':'unsaved',pending?'保存期间的新修改需要再次点击保存':'');
            if (autoSave) void flush().catch(() => {});
        }
        async function flush() {
            if (pending) return pending;
            if (conflict) throw new Error('请先处理账号资料冲突');
            if (!dirty) return;
            pending = (async () => {
                while (dirty) {
                    const ticket = generation;
                    const snapshot = copy(profile);
                    persist(); emit('saving');
                    const result = await request('PUT', '/me/profile', {revision, ...snapshot});
                    revision = result.revision;
                    if (ticket === generation) {
                        dirty = false; clearDraft(); emit('saved');
                    } else {persist();emit('unsaved','保存期间的新修改尚未保存');}
                    if (!autoSave) break;
                }
            })().catch(e => {
                conflict = e.status === 409;
                emit(conflict ? 'conflict' : e.status === 401 ? 'expired' : 'error', e.message);
                throw e;
            }).finally(() => { pending = null; });
            return pending;
        }
        async function useRemote() {
            if (pending) await pending.catch(() => {});
            const remote = await request('GET', '/me/profile');
            profile = remote.profile; revision = remote.revision; generation++;
            dirty = false; conflict = false; clearDraft(); emit('saved');
        }
        async function overwrite() {
            if (pending) await pending.catch(() => {});
            const remote = await request('GET', '/me/profile');
            revision = remote.revision; conflict = false; dirty = true;
            persist(); await flush();
        }
        async function freeze() { frozen = true; if (pending) await pending.catch(() => {}); }
        return {init, update, flush, useRemote, overwrite, freeze, unfreeze: () => { frozen = false; }, snapshot: () => copy(profile), state: () => ({dirty,status,error})};
    }
    root.ProfileStore = {create};
    if (typeof module !== 'undefined') module.exports = {create};
})(globalThis);
