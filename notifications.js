/* Shared unread dots: state belongs to the authenticated account on the server. */
(function(root) {
    'use strict';
    function dot(target, unread) {
        let marker = target.querySelector(':scope > .unread-dot');
        if (unread && !marker) {
            marker = document.createElement('span'); marker.className = 'unread-dot';
            marker.setAttribute('role', 'img'); marker.setAttribute('aria-label', '有未读内容');
            target.append(marker);
        }
        if (marker) marker.hidden = !unread;
    }
    function create({request, user, scope = document, changed = () => {}, interval = 60000}) {
        let data = null, stopped = false, flight = null, generation = 0;
        function paintTarget(target) {
            const channels = target.dataset.unreadChannels.split(' ');
            const id = target.dataset.unreadItem;
            dot(target, !!data && channels.some(c => id ? (data.items[c] || []).includes(id) : data.counts[c] > 0));
        }
        function paint() {
            for (const target of scope.querySelectorAll('[data-unread-channels]')) paintTarget(target);
        }
        function stop() {
            stopped = true; generation++; data = null; paint(); clearInterval(timer);
            root.removeEventListener('focus', refresh); document.removeEventListener('visibilitychange', visible);
        }
        async function fetchSummary(ticket) {
            try {
                const next = await request('GET', '/notifications');
                if (stopped || ticket !== generation) return;
                if (next.user_id !== user.id || next.role !== user.role) { stop(); return; }
                data = next; paint(); changed(next);
            } catch (error) {
                if ([401,403].includes(error.status)) stop();
                // A network failure retains last known state. It never marks anything read.
            }
        }
        function refresh() {
            if (stopped || document.hidden) return Promise.resolve();
            if (!flight) flight = fetchSummary(generation).finally(() => { flight = null; });
            return flight;
        }
        function visible() { if (!document.hidden) void refresh(); }
        async function read(item, channel) {
            const event_id = item.notification_cursors?.[channel];
            if (stopped || document.hidden) return;
            if (!event_id) { await refresh(); return; }
            try {
                await request('POST', '/notifications/read', {channel, item_id:item.id, event_id});
                if (flight) await flight;
                await refresh();
            } catch (error) {
                if ([401,403].includes(error.status)) stop();
            }
        }
        function track(target, channels, id) {
            target.dataset.unreadChannels = channels;
            if (id) target.dataset.unreadItem = id;
            paintTarget(target);
        }
        const timer = setInterval(refresh, interval);
        root.addEventListener('focus', refresh); document.addEventListener('visibilitychange', visible);
        root.addEventListener('pagehide', stop, {once:true});
        return {refresh, read, track, paint, stop};
    }
    root.Unread = {create, dot};
    if (typeof module !== 'undefined') module.exports = root.Unread;
})(globalThis);
