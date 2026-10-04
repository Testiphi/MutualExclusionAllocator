/** 状态边界与计算调度；不读取 DOM 或存储，便于独立验证。 */
const appState = (() => {
    function garage(value, knownCars) {
        if (!Array.isArray(value) || value.some(car => typeof car !== 'string')) {
            throw new Error('车库数据格式损坏');
        }
        return new Set(value.filter(car => !knownCars || knownCars.has(car)));
    }

    function route(value, available) {
        return value === 'off' || value === 'all' || available.includes(value) ? value : 'all';
    }

    function createScheduler(schedule) {
        let revision = 0;
        function cancel() { revision++; }
        function run({ compute, publish, onError, onStart, onFinish }) {
            const ticket = ++revision;
            const current = () => ticket === revision;
            function fail(error) { if (current()) onError(error); }
            try {
                onStart();
                schedule(() => {
                    if (!current()) return;
                    try {
                        const result = compute();
                        if (current()) publish(result);
                    } catch (error) {
                        fail(error);
                    } finally {
                        if (current()) onFinish();
                    }
                });
            } catch (error) {
                try { fail(error); } finally { if (current()) onFinish(); }
            }
        }
        return { run, cancel };
    }

    return { garage, route, createScheduler };
})();
