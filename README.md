# 卡牌闯关（Card Run）

基于 **React + Phaser 3 + FastAPI + SQLite** 的浏览器卡牌闯关游戏。

## 功能
- 选择路线（种子地图，3 条节点路径，最终挑战首领）
- **卡牌成长树**：锻造节点花金币为指定卡牌实例点亮成长节点——三层 DAG（入门 25 金 / 进阶 40 金 / 终阶 60 金），
  进阶与终阶节点需先点亮前置，且同一层分支互斥（如「锋锐」后只能在「破甲/壁垒」二选一，
  选「破甲」后其 T3 只余「裂甲/处决」）；同名卡为独立实例、各自保存解锁节点序列与每笔成本；
  成长即时换算生效卡牌（伤害/格挡/抽牌/能量/费用），贯通战斗结算、商店移除、跨章继承、续局与回放；
  旧版三分支强化记录（`forges`）按确定性默认链（sharpen→keen→rend 等）自动迁移为节点序列
- **旅途商店**：路线上的商人节点可购买卡牌/遗物，或付费移除指定卡牌实例；库存由种子确定性生成，
  统一事务处理扣款/售罄（409）/失败整体回退（400 零副作用），交易结果带入后续战斗，续局与回放一致
- 构筑牌组、挑战精英/首领，奖励选择影响后续遭遇（遗物加伤、首领血量提升等）
- 卡牌效果统一经 **结算队列** 处理，支持连锁触发、状态叠加、死亡打断
- **战斗演出**：Phaser 场景按服务端结算顺序逐条播放（待机/攻击/受击/死亡动画、护盾与状态实时刷新），
  播放期间操作锁定，播完再应用权威快照同步血量/护盾/手牌，战斗结束衔接领奖
- 服务端权威校验行动，防作弊；失败解锁新卡
- **多章远征**：创建跨章节远征（默认 3 章），击败章节首领后携带牌组、锻造成长、遗物与金币
  进入下一章（交接时休整回血 25%）；战败即结算远征并更新解锁，征服终章首领则远征通关；
  章节存档/奖励交接/整程回放统一管理，推进章节走 request_id 幂等 + 状态守卫，
  重复开章（400/409）与重复结算（状态机只流转一次）都被拦截
- **远征委托**：远征章节的旅途商店挂出限章委托（讨伐 N 场战斗 / 完成 N 笔商店交易），
  免费接取（最多同时持有 3 个，同款不重复挂出）；战斗胜利与商店交易自动推进目标，
  完成后在侧栏/章节结算页领取金币或卡牌（领奖走状态机 `ready→claimed` + request_id
  幂等，重复领取 409、绝不重复发奖，失败交易不推进）；超期未完成或战败则委托失败，
  已完成可领奖的不随超期失效，章节通关后、进入下一章前仍可领取（终章结算后关闭）。
  委托随交接快照跨章保留进度，续局与整程回放完整重建（含超期/战败/领奖终态）
- 中途可续局（`POST /api/runs` → 刷新 → 回到同一节点/战斗）；种子回放一致
- **可交互整局回放**：动作日志升级为可 ▶播放 / ⏸暂停 / ◀单步 / 拖拽跳转 / 0.5–4× 倍速 的时间轴，
  逐步重建路线、战斗（Phaser 按结算顺序重演）、锻造与交易状态；记录规则版本与逐步校验点（可检出日志损坏/规则漂移），
  兼容无版本号的旧日志（裸卡牌 id）；回放全程只读隔离——不写存档、战败不发解锁
- 服务端对无限连锁触发设上限防止死循环；领奖/锻造防重复（重复领取返回 409，不重复扣款）
- **远征整程回放**：`GET /api/expeditions/{id}/replay` 返回远征事件时间线
  （create/chapter_clear/advance/settle）+ 逐章完整可交互回放；章节 run 的初始状态由
  create 事件携带的交接快照重建，校验点逐位比对；全程只读隔离——不写存档、不发解锁
- 旧存档自动兼容：裸 id 牌组在首次载入（续局/行动）时迁移为卡牌实例结构，含战斗中存档
- **并发一致性**：每个行动的「校验 → 存档 → 动作日志 → 战败解锁」在单个 SQLite 事务
  （`BEGIN IMMEDIATE` + WAL）内原子提交，任一写入失败整体回滚，杜绝写入失败/并发操作导致的
  存档与回放分叉；per-run 锁串行化同一局的读改写，乐观版本号 `rev` 检测状态冲突（409），
  请求令牌 `request_id` 做请求级幂等（双击/超时重试不重复扣款发奖）；异常/损坏日志不拖垮回放

## 目录结构
```
backend/   FastAPI + SQLite（引擎、结算队列、会话、路由、测试）
frontend/  Vite + React + Phaser + zustand
```

## 启动

### 后端（端口 8001）
```bash
cd backend
py -m pip install -r requirements.txt
py run.py
```

### 前端（端口 5173，代理 /api → 8001）
```bash
cd frontend
npm install
npm run dev
```
浏览器打开 http://localhost:5173

## 测试（后端）
```bash
cd backend
$env:PYTHONPATH="."; $env:PYTHONDONTWRITEBYTECODE="1"
py -m pytest -q tests
```
测试覆盖：结算队列（连锁/叠加/死亡打断）、无限连锁封顶、成长树（21 节点 DAG 结构与成本、
前置条件/同层互斥/跨 lane 不互斥、同名卡独立成长、失败零副作用/重复 409、
成长贯通战斗伤害与费用、续局、商店移除、跨章继承与互斥延续、合法流程回放逐位一致、
旧 forges 记录与战斗中旧档迁移、旧版/无版本号 forge 日志默认链兼容重演）、
失败解锁、种子+动作日志确定性回放、**可交互回放逐帧重建（帧视口/规则版本/校验点/损坏检出/旧日志兼容/只读隔离与解锁隔离）**、
商店库存确定性/续局一致、购买卡牌/遗物（扣款/售罄/失败回退）、移除指定实例（递增价/牌组下限）、
交易贯通后续战斗与回放、**并发与原子提交（写入失败整体回滚、并发领奖/锻造/战败只生效一次、
request_id 幂等含并发同键、expected_rev 状态冲突 409、旧 schema 自动迁移、损坏日志/序号缺口容错）**、
**多章远征（创建即开第 1 章、章节通关交接牌组/锻造/遗物/金币、推进章节防重复开章与 request_id 幂等、
战败/终章通关结算且只结算一次、整程回放逐章校验点通过且只读隔离）**、
**远征委托（仅远征商店确定性挂单/同款去重/限张、接取防重复、战斗胜利与成功交易自动推进、
失败交易不推进、领奖防重复与 request_id 幂等、未完成/失败/战斗中拒绝领奖、战败批量失败、
推进章节超期失败且 ready 不超期、章节通关后仍可领奖而终章结算后关闭、委托跨章交接、
续局保留、合法两章流程的逐章/整程回放校验点全通过且与在线状态一致）**。

## API 摘要
- `POST /api/runs {seed?}` 建局
- `GET  /api/runs/{id}/resume` 续局
- `POST /api/runs/{id}/act {action,...}` 行动（choose_node / play / end_turn / claim_reward / forge / shop_buy / shop_remove / commission_accept / commission_claim）
  - 可选并发字段：`request_id`（客户端为每个意图生成的令牌；同令牌重复/并发提交返回首次响应，
    响应里 `duplicate:true`，绝不重复执行）、`expected_rev`（所依据视口的存档版本号；
    存档已被推进则返回 409 状态冲突）。行动响应与 `/resume` 视口携带当前 `rev`。
- `GET  /api/runs/{id}/replay` 整局可交互回放：除原 `actions`（兼容）外，返回
  `rules_version` / `recorded_versions` / `legacy` / `initial.checkpoint` / `steps[]` /
  `final_view` / `verification` / `isolated`；每个 `step` 含动作、类型/标题/摘要、
  结算事件 `events`、战斗结果，以及该步完成后的完整只读 `view`（与 `/resume` 同构）
- `GET  /api/cards`、`/api/enemies`、`/api/map-preview?seed=` 元数据

多章远征：
- `POST /api/expeditions {seed?, chapters?}` 创建远征（默认 3 章）：远征记录与第 1 章 run
  在同一事务落库；返回 `{expedition, run}`，run 视口携带 `expedition` 摘要（章节进度/结算状态）。
- `GET  /api/expeditions/{id}` 远征视口 + 当前章节 run 视口（续远征入口）。
- `POST /api/expeditions/{id}/advance {request_id?}` 进入下一章：仅当远征进行中且当前章
  已通关；以交接快照（牌组/锻造/遗物/金币/生命，休整回血 25%）确定性开新章
  （章节种子由远征种子派生）。重复推进 400、已结算 409、同 request_id 返回首次响应
  （`duplicate:true`），绝不重复开章。
- `GET  /api/expeditions/{id}/replay` 整程回放：远征事件时间线 + 逐章完整回放
  （复用单局可交互回放，校验点逐章比对），全程只读。
- 章节 run 就是普通 run（`/api/runs/{id}/act|resume|replay` 全部适用）；章节 run 结束时
  （won/lost）与行动同一事务同步远征状态：非终章通关记录 chapter_clear 交接快照，
  战败/终章通关结算远征（settle），已结算或非当前章节的重复触发直接跳过。

卡牌成长树（锻造节点）：`{action:"forge", card:<卡牌实例 uid>, growth_node:<节点 id>}`
（旧客户端用 `branch` 传 T1 节点 id 也兼容）。节点分三层收费（入门 25 / 进阶 40 / 终阶 60，
视口 `growth_tier_cost` 与 `growth_tree` 下发完整树定义：每个节点带 `requires` 前置与
`mutex_with` 互斥集）；同一锻造节点仅可锻造一次，重复请求 409 且不扣款，
金币不足/非法卡牌/未知节点 400，前置未达成 400，互斥分支已选 400（校验先于扣款，零副作用）。
卡牌实例按 `growth:[{node,cost}]` 保存解锁节点序列与每笔成本，`growth_spent` 为该实例累计投入。
2.3.0 之前的旧 forge 日志（无版本号或 `ver<2.3.0`，含同分支可重复选择）回放时
按确定性默认链（sharpen→keen→rend、empower→amplify→overload、refine→economize→frugality，
每笔固定 25 金）兼容重演；旧版存档的 `forges:[分支...]` 在首次载入时自动迁移。

商店行动（进入商店节点后视口携带 `shop_available:true` 与 `shop` 库存）：
- 购买：`{action:"shop_buy", kind:"card"|"relic", sku:<货架项 id，如 "card:cleave">}`，
  按货架价格扣款；重复购买/已持有遗物返回 409（售罄，不扣款），金币不足/非法货架返回 400。
- 移除：`{action:"shop_remove", card:<卡牌实例 uid>}`，永久删除该实例（同名卡其余副本不受影响），
  基础价 35 金币，同店每移除一次下一次 +15（`shop.remove.cost`/`next_cost` 随视口返回）；
  牌组仅剩 1 张、金币不足或 uid 非法返回 400。
- 两类交易都走统一事务：先校验后扣款，过程中任何异常把 run 整体回退到交易前快照；
  交易记录保存在 `shop.tx`（含类型/sku 或 uid/价格/余额），离开节点库存清空。
  购入的卡牌/遗物直接进入后续战斗（遗物在战斗初始状态换算，新卡随下次洗牌进三堆）。

远征委托（仅远征章节商店挂单，普通局不出委托）：
- 挂单：进入商店时 `shop.commissions[]` 确定性生成（随商店种子/章号/已持有委托，
  同款不重复，持有满 3 个进行中/待领取时不再刷新），每项含目标（讨伐战斗数 /
  完成交易笔数）、限章 `deadline_chapter` 与奖励（金币或卡牌）。
- 接取：`{action:"commission_accept", sku:"commission:<签名>"}`，免费；挂单随即移除，
  重复接取返回 409（不重复发委托），离开商店/非法 sku/非远征返回 400。
- 自动推进：战斗胜利推进讨伐目标、成功交易（购买/移除各算一笔）推进贸易目标；
  失败交易整体回退不推进。目标达成状态转 `ready`；战斗中不可领奖。
- 领取：`{action:"commission_claim", commission:<委托 id>}`，金币直接入账、
  卡牌以独立实例入牌组；状态机只允许 `ready→claimed` 一次，重复领取 409 不重复发奖，
  request_id 同令牌返回首次响应；未完成/已失败 400。章节通关（won）后、推进下一章前
  仍可领取；终章通关（远征 won）或战败（远征 lost）后关闭领奖。
- 失败：战败时全部进行中委托 `failed(battle_lost)`；推进章节时限章早于新章的进行中
  委托 `failed(expired)`（advance 事件携带 expired id 列表），`ready` 委托不超期。
- 持久化：委托与发号器在 run 状态（`commissions/next_commission_seq/chapter/chapters_total`）
  并进入章节交接快照；在线开章与回放重建共用 `_new_run_state`，逐位校验点一致。

## 设计要点
- 所有战斗逻辑在服务端（唯一权威），客户端仅播放服务器返回的结算事件 → 续局/回放天然一致。
- 行动日志为有序序列：结算事件（`action/target/value/source/extra`）+ 控制项（`{"snapshot"}` 权威校正点、
  `{"result":"won|lost|run_won"}` 战斗结束、`enemy_turn` 敌方回合标记含技能名）；`end_turn` 的敌方结算
  事件同样按序入日志，敌人技能的全部效果都会结算（如血裔"吸取"= 伤害 + 自身回血）。
- 前端播放：Phaser 场景维护展示态（血量/护盾/状态随事件逐条推算），日志末尾的权威快照负责校正；
  播放期间到达的快照（刷新/续局）暂存至队列播完后应用，空闲时立即生效。
- 结算队列：事件按插入序稳定解析，效果 → 连锁子事件；目标死亡后定向事件被剔除（死亡打断）。
- 确定性：洗牌与敌人意图均由 `random.Random(seed)` 派生，持久化在 run 状态，回放可复现。
- 可交互回放：在线行动与回放共用纯推演函数 `_apply_action(run, action, map, grant_unlocks)`，
  “玩”和“放”永远是同一套规则。回放从建局初始状态按日志逐步推演，为每步产出一帧只读视口；
  动作事件携带 `ver`（规则版本）与 `ckpt`（权威状态 SHA-256 校验点），每步重演后比对哈希，
  不一致标记 `mismatch`（日志损坏/规则漂移）、无版本号事件标记 `legacy`（旧日志兼容、不校验）。
  回放路径 `grant_unlocks=False` 且不调用任何写库接口：runs/battle_events/profile 均不变，战败不解锁。
  前端 `ReplayPlayer` 提供播放/暂停/单步/跳转/倍速/类型过滤时间轴，战斗帧经同一 Phaser 事件队列重演。
- 卡牌实例：`run.card_instances` 为 `uid -> {id, growth:[{node,cost}]}`，牌组/牌堆/手牌只存 uid；
  引擎在打牌时用 `forging.effective_card(base, growth)` 即时换算生效卡牌（费用/数值/附加效果），
  成长节点按解锁顺序叠加；因此成长树解锁/商店购卡/商店移除自动贯通战斗结算、续局、回放与跨章继承（初始牌组 7 张，商店可增减）。
- 成长树规则（`app/forging.py`，数据驱动的 21 节点 DAG）：3 个 T1 入口（锋锐/强效/精炼），
  每个 T1 下 2 个互斥 T2，每个 T2 下 2 个互斥 T3；`requires` 表达前置、`mutex_with` 表达
  同层二选一（三条 lane 之间互不互斥）。`validate_unlock(inst,node)` 统一校验
  未知/已解锁/前置/互斥，`available_nodes(inst)` 计算当前可解锁集合；节点金币成本按 tier 固定。
  每个节点的数值变换是独立纯函数（伤害/格挡/易伤/力量/抽牌/能量/费用），依次施加、可自由组合。
- 旧档兼容：缺少 `card_instances` 的存档在首次载入时迁移；战斗中存档按三堆出现序把裸 id
  稳定映射到 uid，洗牌布局与确定性保持不变。2.3.0 起实例 `forges:[分支]` 迁移为
  `growth:[{node,cost}]`（重复分支沿确定性默认链展开、逐笔保留 25 金成本）；
  旧版 forge 动作日志在回放时走同一兼容映射，含旧版本号（`ver<2.3.0`）与无版本号日志。
  结构迁移发生在已存在的动作上，该步事件带 `migrated:true`，回放按 legacy 处理本步校验点
  （结构迁移天然不可逐位比较），后续步骤仍严格校验。
- **原子提交与并发**：`db.transaction()` 经共享单连接开启 `BEGIN IMMEDIATE`，行动事务内
  顺序写 runs（`rev=rev+1` 乐观锁）→ battle_events → profile → act_requests，异常即 rollback；
  per-run `threading.RLock` 在进程内串行同一局，WAL + busy_timeout 让读写不互斥。
  旧库启动自动补 `rev` 列与 `act_requests` 表。损坏的 `payload_json`（非法 JSON/NULL）
  在读取时降级为 `_corrupt` 行，回放标注 `error` 仍可播放其余步骤；序号缺口给出 `warning`
  与 `verification.seq_gaps`。
- SQLite：`runs`（状态，含 rev 乐观版本、商店库存/交易记录、expedition_id/chapter 远征归属）、
  `battle_events`（动作日志，含 forge/shop 行）、`profile`（解锁卡）、
  `act_requests`（request_id → 首次响应，请求级幂等）、
  `expeditions`（远征：状态/章节进度/交接快照 carry_json/rev）、
  `expedition_events`（远征事件：create/chapter_clear/advance/settle，整程回放时间线）。
- 远征章节 run 的初始状态由 `_new_run_state(seed, carry)` 构造：在线开章与回放重建共用
  同一函数，交接快照随章节 run 的 create 事件落库，回放无需读取远征表即可逐位复演；
  章节种子 = f（远征种子， 章节号） 确定性派生，各章地图/洗牌独立但可复现。
  交接快照同时携带远征委托（含进度与 ready/claimed/failed 终态）与委托 uid 发号器，
  开新章时先对快照跑超期判定再建章，advance 事件记录 expired 列表，因此委托的
  接取/推进/领奖/超期/战败全部是动作序列的确定性函数，续局与回放逐位一致。
