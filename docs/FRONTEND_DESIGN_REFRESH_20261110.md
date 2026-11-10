# 网页前端视觉刷新 2026-11-10

## 0. 状态

- 分支：`feature/frontend-design-refresh`
- 工作树：`E:\hzz\work\MutualExclusionAllocator\frontend-design-refresh-20261110`
- 基线：`origin/main` 的 `41ac4911f583ee63e5bfcb659a431f37c7f92c1d`
- 本轮改动提交在 `feature/frontend-design-refresh`；推送状态以 `origin` 分支头为准。未构包、未部署。
- 目标：按 2026-11-10 只读评审的方向做视觉刷新，不改变排版骨架、主题和主色，不碰接口、算法、数据、工作簿。
- 结论：网页首页与共享控件已完成第一轮视觉改造；小程序端未改，单独排期。

## 1. 固定边界（本轮的硬约束）

### 已改

- `theme.css`：新增 token 与基础字体栈。
- `styles.css`：首页视觉层、响应式、结果卡、空状态、弹窗按钮。
- `ui.css`：共享按钮与反馈卡片的 token 化。
- `index.html`：只改静态文案、下拉占位文字、空结果位的 class 与去表情符号；没有改事件、求解、存储或 API。
- `home_theme.json`：用仓库生成器重生，使网页 CSS 与冻结导出一致；`--check` 通过。

### 未改，且本轮不能改

- `home_presenter.js`：与小程序共享，`miniapp/mirror-source.json` 固定 pin，`test_result_guidance` 校验 SHA。
- `selection_core.js`、`allocator.js`、`race_scores.js`、`app_state.js`：算法与状态。
- `api.js`、`config.js`、后端、账号/投稿契约。
- 任何 `gauntlet_data*.json/xlsx`、`cars*.json`。
- `miniapp/**`：原生 WXML/WXSS 是独立端，不在本轮改；本轮只做只读兼容审计（见第 5 节）。

## 2. 视觉改了什么

### 2.1 Token（theme.css）

新增或明确：

| token | 值 | 用途 |
|---|---|---|
| `--rp-text-2` | `#9aa4b2` | 次要文字；`#161b22` 上 6.86:1 |
| `--rp-text-3` | `#7d8896` | 更弱信息；`#0d1117` 上 5.26:1 |
| `--rp-surface-2` | `#0f141a` | 地图行、结果卡底 |
| `--rp-radius-card/control/chip` | 12 / 8 / 6 | 外卡 / 控件 / 标签 |
| `--rp-size-xs/sm/md/lg/xl` | 11 / 12 / 14 / 16 / 24 | 元信息 / 标签 / 正文 / 强调 / 标题 |
| `--rp-mono` | 系统等宽栈 | 序号、秒数、Σ、徽标 |
| `--rp-focus` | `#79b8ff` | 统一焦点环 |
| `--rp-shadow-pop` | 低透明阴影 | 仅弹窗 |

`--rp-font` 在原有 system-ui/Segoe 栈上补了 PingFang SC、Hiragino、Microsoft YaHei、Noto Sans SC；仍是系统字体，不加载外部字体。

### 2.2 首页

- 档位/分区/服别：原来的「○/●」文字点改为两段式分段控件；HTML 仍是 label/anchor，点击逻辑未动。
- 地图行：去掉可见边框和嵌套卡片感，改用 `--rp-surface-2` 底 + hover/focus-within 边框；序号改为等宽 11px。
- 下拉：统一 40/44px 高、14px 字、8px 圆角；占位文字从「-- 选择大地图 --」缩成「选择大地图」，解决 320–414px 截断。
- 车库：标题 18px；操作按钮 40/42px；筛选改成可横滚的 tab 行；车标降为 12px/6px 圆角，选中态用 `--rp-accent-text` + `--rp-accent-border`，星级降到 `#c9a45c`，减少整面蓝色和满屏金色。
- 结果：面板从「又一张卡片」改为分隔线后的结果区；结果卡左对齐，地图名/大地图降级，车名 16px，秒数 22px 等宽主数字，单位 11px；空结果位改为 `is-empty` 虚线中性卡，文案「空位 / 缺小地图 / 待选图」，去掉 ⛔。
- 弹窗：禁车和投稿地图选择弹窗的按钮不再是浏览器默认样式，统一 36px 控件高度。
- 文案只改了不共享、不被测试锁定的地方：星级说明、搜索占位、空匹配引号、加载省略号、方案下拉初始占位。

### 2.3 共享页面

`ui.css` 的按钮、主按钮、反馈卡片、徽标改用 token；`theme.css` 的 `rp-page` 外壳、panel、输入框圆角统一到 12/8。子页面自己的硬编码色板没有大改，见第 6 节。

## 3. 响应式与兼容矩阵

用 Chrome headless + 本地静态服务实测，视口宽度：

| 视口 | 结果 |
|---|---|
| 320×568 | 无横向滚动；地图下拉在 ≤380px 改为单列，卡片 300px |
| 360×640 | 同上，单列 |
| 390×844 | 无横向滚动；地图两列，占位文字完整显示 |
| 414×896 | 两列，完整 |
| 844×390 横屏手机 | 无横向滚动；保留桌面两列地图行 |
| 768×1024 平板 | 无横向滚动；两列地图行，标签可见 |
| 834×1112 平板 | 无横向滚动 |
| 1024×768 横屏平板 | 无横向滚动 |
| 1280×800 / 1440×900 / 1920×1080 | 卡片最大 1280，无溢出 |

改造前后关键差异：

- 390px：大地图下拉可用宽度 75px，占位文字 117px → 改造后 80px vs 70px，`fit=true`。
- 320px：改造前大地图可用 43px；改造后改单列，可用 170px。
- 640px 以下地图行高度：390 两列 58px；320 单列 108px（更宽松但仍紧凑）。
- 选择器 `select` 统一 40px（桌面）/44px（手机），点击高度更稳。

微信内置浏览器/X5 兼容：本轮只用 CSS 变量、flex/grid、`gap`、`prefers-reduced-motion`、`-webkit-overflow-scrolling` 等现有页面已在用的能力；没有引入 `color-mix`、容器查询、`text-wrap: balance`。新增没有依赖 `:has()` 的样式；原有 `:has()` 仍在禁车按钮上，旧内核下会退化为普通按钮位置（这是本轮未改的既有风险）。

## 4. 测试与验证

- `node --test tests/test_boot_smoke.js`：通过。
- `node --test tests/test_home_presenter.js`：通过（`home_theme.json` 重生后）。
- `node --test` 其余不依赖小程序生成夹具的测试：通过；合计 20/22 通过。
- `python -B -X utf8 tools/export_home_theme.py --check`：exit 0。
- `python -B -X utf8 -m unittest tests.test_release_tools tests.test_production_release -v`：21 项执行，18 通过、1 项 Linux 专用跳过、2 项因本机缺少 `argon2` 依赖失败（环境问题，不是 CSS/主题契约失败）。
- `node --test tests/test_web_home_mirror.cjs`：补入小程序生成夹具时通过；干净工作树缺 `miniapp/shared` 会因缺模块退出，属于夹具问题，不是网页样式回归。
- 浏览器交互：生成 2 图方案、结果卡、三个空位、禁车弹窗打开/关闭均正常；重复大地图实测：正常选图时其他槽位同名 option 被禁用，键盘移动会跳过；程序化赋值可绕过但属非用户路径；`.result-car` 与五卡索引保留，禁车按钮仍挂在第 1/2 张卡上；页面无 JS 异常（仅一个无意义的 404 资源请求）。
- `git diff --check` 在 CRLF 文件上会报 CR；用 `git -c core.whitespace=cr-at-eol diff --check` 复核，无真实行尾空格问题。

### 当前未通过的两个测试及原因

1. `tests/test_result_guidance.js`：工作树缺少 `.gitignore` 的 `miniapp/shared/` 与 `miniapp/generated/` 生成夹具；本地主树有旧夹具，复制后仍因 `home_presenter.js` 的固定 pin/本地生成来源不同而失败。不是网页样式回归。
2. `tests/test_visual_acceptance.cjs`：断言小程序 `miniapp/shared/home_theme.json` 与 `functional_theme.wxss` 的生成一致性；它属于小程序同步门，网页分支没有更新 `miniapp/**`，所以必然 stale。属于本轮明确不同步的范围。

## 5. 小程序兼容审计（只读，未改）

审计对象：`miniapp/app.wxss`、`miniapp/pages/home/home.wxss`、`coverage.wxss`、`components/select/select.wxss`、`app.json`、`shared-source.json`、`mirror-source.json`、`tools/prepare_miniapp.cjs`、`tools/mini_theme.cjs`。

关键事实：

- 小程序是原生 WXML/WXSS，不是 web-view；网页 CSS 不会热更新进小程序。
- 自动同步只有两条窄通道：`theme.wxss` 的 4 条规则（bg/text/font/surface/divider/muted/selected/blue）和 `functional_theme.wxss` 的 7 条规则（`.mirror-page`、`.rp-page h1`、`.rp-page .panel`、600px 断点）。首页 `home.wxss` 基本是手抄字面量。
- `miniapp/app.wxss:4` 的 `page{background:#0d1117}` 在 `@import` 之后，会覆盖生成层的 page 规则；改网页 `--rp-bg` 不会改小程序首页底色。
- 小程序仍有 12 处 `#6e7681`、7 处 `#484f58`；网页已改为更亮的 `--rp-text-2/--rp-text-3`，两端次要文字层级会不一致。
- `mirror-source.json` 固定 `04cabf3`，比网页 HEAD 落后约 30 个提交；`home_presenter.js` 和 `home_theme.json` 不能直接跟网页走。
- `home.wxss` 同时存在 rpx 区和 px 覆盖区；只改一处会出现 320 与大屏字号跳变。安全区只有首页有 `env(safe-area-inset-bottom)`。
- `mini_theme.cjs` 的 `resolve()` 对带数字的 token 名（如 `--rp-surface-2`）不友好；将来同步新 token 要先修正则。
- 现有验收脚本 `check_miniapp_devtools.cjs` 仍等待原生 picker，而当前 home 已是页内下拉；不能拿旧脚本当本轮验收入口。
- 小程序已首发上线（见 `docs/MINI_FIRST_LAUNCH_STATUS_20261108.md`），网页视觉差会与线上小程序并存，这是已知状态，不是本轮回归。

本轮决定：**不修改 `miniapp/**`，不 bump pin，不生成小程序构建**。网页侧只保证 `export_home_theme.py` 的契约选择器不漂移（`.card`、`.car-grid`、`.car-tag`、`.garage-btn`、`.rp-page` 系列、600px 断点仍在）。

如后续要同步小程序，最小范围是：

1. 提升 `mirror-source.json` pin，重跑 `tools/prepare_miniapp.cjs`，修 `mini_theme.cjs` 的数字 token 解析。
2. 只做值级 1:1 的 16 个颜色字面量替换 + px 区圆角收敛（约 40 处），不碰 rpx 区。
3. 分段控件、结果卡层级、空位样式、安全区统一需要改 WXML/WXSS，属独立任务，必须走微信开发者工具 + iOS/Android 真机 + 平板验收。

## 6. 未修问题（按“指出但不动逻辑/接口”记录）

- **键盘可达性**：首页档位/分区仍是 `label`，车型筛选和车标是 `span`，星级触发器是 `span`；实测 175 个可点击元素自身不可聚焦。改法需要换语义/加键盘处理，属于行为改动，本轮不做。
- **触控目标**：390px 下仍有 96 个交互元素高度 <36px（车标 34、筛选 34、档位 32）。已比原来 17–26px 改善，但未全部达到 44px。
- **结果空位逻辑**：代码固定渲染 5 个结果位，未选图仍占两个空卡；本轮只做中性化，没有删卡，因为禁车按钮/跑法视频按 `resultGrid.children[i]` 挂载，删卡会破坏索引。
- **重复选图**：正常 UI 不允许同一大地图重复——`refreshBigMaps` 会把其他槽位已用的大地图 option 设为 disabled；实测第 1 行选「古老斗技场」后，第 2 行同名 option 被禁用，键盘下移会跳到下一张可用图。只有直接改 DOM/程序化赋值能绕过，而且 `getCurrentValidMaps` 没有键控去重校验，重复状态一旦进入求解会被当成多张图。之前的自动化截图是直接赋值生成的，不是正常用户路径；本轮不改，若修建议在 `getCurrentValidMaps`/change 事件做 `(big,small)` 校验。
- **共享文案**：`home_presenter.js` 的三种结果引导共用一句「找不到合适的方案？尝试投稿你自己的成绩来帮助我们提升！」，被 `tests/test_result_guidance.js:11` 锁定；未改，建议单独立项并同步小程序镜像。
- **副标题**：仍由 `tier_info.desc` 数据驱动（「自定义星级 + 成绩排序，可开启特殊跑法」），属数据文案，未改。
- **子页面 token 漂移**：`submissions.css`、`leaderboard.css`、`usage.css`、`map_recognition.css` 仍有各自硬编码色值/宽度；本轮只通过 `ui.css/theme.css` 共享层改善按钮和外壳。
- **`:has()`**：禁车按钮定位依赖 `:has()`；旧微信内核不支持时按钮会退化。未改，属既有实现。

## 7. 常用验证命令

```bash
node --test tests/test_boot_smoke.js tests/test_home_presenter.js
python -B -X utf8 tools/export_home_theme.py --check
```

完整前端测试依赖 `miniapp/shared`、`miniapp/generated` 生成夹具；在干净工作树里需要先按小程序构建流程生成，或使用已生成夹具。不要为了跑测试把生成物提交进仓库。

## 8. 本地证据

- 工作区 `_frontend_tmp/before/`、`after/` 有各视口截图与 `before-metrics.json` / `after-metrics.json`；交付归档在 `本地归档/frontend-design-refresh-20261110/`。
- 关键对比：`before/phone390.png`、`after/phone390.png`、`after/desktop1440.png`、`after/result1440.png`、`after/result390.png`、`after/dialog-mobile.png`。

## 9. 下一步

1. 用户本地验收：320/390/768/1024/1440 与横屏；确认档位分段、结果主数字、空位颜色。
2. 决定是否进入 P1 的第二轮：车库默认折叠/生成后自动滚到结果/品牌橙细线（都会改变交互或增加动效，需单独确认）。
3. 小程序同步另开任务，按第 5 节最小范围执行；不在本分支顺手改。
4. 键盘可达性与测试锁定文案另开行为改造任务，避免和纯视觉改动混在一起。

## 网站侧后续验收

用户确认大地图唯一。网页保留最先出现的槽位，清空后续重复槽位的大小地图。重建选项和进入求解前均检查，五槽索引保留。改动独立于已推送的 9704363。

投稿、账号、排行榜、统计、预览、地图识别和成绩表只调整 CSS。面板与控件共用 12/8px 圆角、共享表面色与次要文字 token，收掉重复面板边框。业务标记、表单字段、表格列和权限沿用现有实现。home_theme.json 由导出工具重生。

36 项 Node 回归通过，主题导出检查通过。Chrome headless 验证正常选图、直接赋值绕过、切服、切区和切档，以及七页在 320/390/768/1024/1440 的布局。表单使用离线界面夹具测试，宽表验证容器内滚动。OCR 覆盖内嵌布局和弹窗样式夹具。截图和复现脚本在工作区本地归档 frontend-followup-20261110。

原始仓库构包测试为 19 通过、1 跳过、1 失败。失败原因为既有白名单未收录 mini_wechat_binding.py。用已交付的 9ade659b 白名单复跑为 20 通过、1 项 Linux 专用跳过。候选沿用 9ade659b 的运行文件和数据，仅覆盖本轮网页运行文件。目标 Linux 和生产验收另行处理，小程序同步另行处理。

## 首页键盘本地验收

独立分支从已上线网页源码 f76c896 分出，并合入 ee2689e 的运维记录。首页通过 Chrome 键盘、鼠标和移动触摸模拟验收。用户已确认 8066 验收通过。
