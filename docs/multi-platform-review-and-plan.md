# 多平台接入审查与实施方案

核对日期：2026-11-10。当前阶段为代码审查、官方资料核对和无凭据公开端点探测；不改业务代码、不迁移数据库、不更换正在使用的Garmin服务、不提交GitHub。

## 1. 审查对象与现状

实际项目是`garmin-running-coach`，正在使用的私人运行环境在同级`Garmin-Running-Assistant`。拟议的`open-running-coach`发布目录尚不存在，不能当作已创建的仓库。

| 位置 | 当前职责 | 发现 |
| --- | --- | --- |
| assistant.py | Garmin认证、联网同步、FIT分圈、SQLite、训练汇总、CLI | 业务集中在一个模块；与私人环境该文件SHA-256一致 |
| server.py | 七个本地MCP工具 | 与私人环境该文件SHA-256一致；查询缓存，不联网同步 |
| skills/open-running-coach | 分析、截图、训练计划指令 | 不包含平台连接器；不会自动刷新云端记录 |
| scripts | 技能安装及vivo/Keep实验映射 | 后两者是文件映射，不是Strava/COROS联网适配器 |
| requirements-garmin.txt | 连接依赖 | Garmin SDK 1.0.0、mcp 1.30.0、fitdecode 0.11.0；pywin32为范围版本 |
| requirements-import.txt | 实验导入依赖 | pyzipper、xlrd；与联网认证无关 |
| config.example.json | 区域示例 | 不含密钥；真正config.json被忽略 |

本机已有Garmin运行环境实测安装版本：SDK 1.0.0、mcp 1.30.0、fitdecode 0.11.0、pywin32 312。未安装新的依赖；未读取密钥文件内容。

### 已具备，可保留

- Garmin Personal API Key首次本地输入；当前Windows用户DPAPI加密保存密钥与Bearer缓存，临时文件写入后替换。
- 中国版/国际版官方主机选择；SDK按密钥及主机指纹复用令牌，距到期不足一小时会用Personal API Key换新Bearer。它不是OAuth refresh_token流程；API Key本身失效仍需重新配置。
- 401首次换令牌重试；429和服务端错误有限次数重试；同步进程文件锁。
- 活动列表分页、详情、原始ZIP/FIT和分圈、若干日常健康数据集。
- SQLite WAL、活动ID主键与upsert；同一Garmin活动重复同步不重复入库。
- 单条错误时保留已有有效数据；success/partial/failed及活动上限提示。
- MCP省略常见身份与位置字段；技能处理缺测、借表、心率可信度、重复活动及截图边界。
- .gitignore忽略凭据、数据目录、私有文件和数据库。

本轮执行并通过：5项Garmin虚构数据测试、2项技能安装测试。没有使用真实账号做新同步。此前MCP握手记录属于既有验证，本轮未重跑握手。

### 需要修改的地方

1. 没有统一Provider接口；认证、同步、存储、汇总与Garmin字段耦合。
2. 现有MCP查询只读缓存，分析前没有自动联网入口。
3. activities仅按整数活动ID索引，无平台、账号分区；多平台或换账号会混淆归属。
4. 时区固定UTC+8，day主要截取来源字符串；多时区/跨午夜统计需保留UTC时刻及来源时区。
5. 同步计数是处理条数，不区分新增、修改、未变化；没有增量游标、逐平台成功水位或缓存新鲜度。
6. 错误只保留异常类和HTTP状态，无法准确区分未配置、撤权、缺scope、网络失败、不支持能力和无新数据。
7. 写库支持部分成功，但异常中断可能留下running记录，需要运行ID、心跳/中断恢复判断；并发刷新令牌也需锁。
8. 导入模块即依赖msvcrt/win32crypt，限制所有核心逻辑在Windows运行；应仅让Windows凭据实现依赖它们。
9. 自定义令牌缓存解析未完整保留SDK对损坏缓存的容错；不能把坏缓存一概等同于密钥错误。覆盖SDK私有方法还需固定兼容性测试。
10. .gitignore并非凭据检测。需要发布文件白名单、暂存区敏感信息扫描及CI检查；当前截图/任意ZIP并未被通用排除。健康数据库也没有因凭据DPAPI加密而自动加密。

## 2. 官方路线核对与限制

### Garmin：保留现有个人接口

先用适配器包装现有Source与同步能力，旧CLI、旧数据库和七个MCP工具保留兼容入口。真实运行目录不作为实验目标。新增存储先用独立v2数据库，备份并试运行后再决定迁移；回退时旧服务仍可使用。

### Strava：OAuth可行不等于本项目可用

官方OAuth需要注册应用、client_id/client_secret、用户授权码、实际授予scope及短期access_token/refresh_token。访问令牌约六小时失效；必须按expires_at判断并持久化返回的最新refresh_token，串行刷新。只申请必要读取权限，私有活动须获相应scope；不申请写权限。回调校验state、一次性授权事务及回调地址；不收集用户密码。

重要边界：现行API Policy限制普通API数据进入AI上下文、自建代理/MCP以及长期存储，并为官方Strava MCP另设路径。普通API缓存上限为7天，也有删除/撤权处理要求。因此不实施“普通Strava REST API → 长期统一数据库 → 本地MCP → AI分析”作为默认功能。用户同意、匿名化或仅缓存汇总不能自动解除这些限制。

AI用途优先评估官方`https://mcp.strava.com/mcp`，按其订阅、受支持客户端及个人使用条件接入；不能据已公布URL保证Codex可授权，也不绕过客户端限制。Strava数据是否允许本项目的持久化、跨平台合并与再暴露需进一步确认；受限时保持会话级直接使用，不进入通用长期仓库。REST OAuth技术模块可以在获准用途下复用，但默认不为当前AI流程开放数据桥接。

API还有应用人数和读请求配额限制，实际配额按应用设置及响应头处理，不写死成无限接入。没有Strava应用凭据/账号授权，本轮未完成OAuth实测。Strava日常睡眠、HRV覆盖不能由活动API推断。

### COROS：官方MCP为个人自助路线

COROS官方说明MCP用户自行OAuth授权即可，无需Partner API申请。Partner API是另一条有公司/平台资格要求的路线，不混用其配额或推送能力。默认仅调用读取工具，不调用其创建/修改训练计划等写入能力。

本轮独立探测结果（无凭据）：

| 步骤 | 结果 | 可说明什么 |
| --- | --- | --- |
| 对https://mcp.coros.com/mcp发送initialize | HTTP 401，带Bearer资源元数据挑战 | 服务可达、要求授权；不是授权失败或MCP握手成功 |
| 按挑战读取中国区资源元数据 | HTTP 200；resource为https://mcpcn.coros.com/mcp | 本次路由及资源发现成功，不推广为所有账号所属区域 |
| 读取该issuer的OAuth元数据 | HTTP 200 | 广告了授权、令牌及注册端点；支持S256和refresh_token |
| 动态客户端注册、账号授权 | 未执行 | 元数据声明不证明注册或完整授权一定可用 |
| tools/list、真实活动/分圈/健康读取、刷新 | 未执行 | 需要合法账号授权和有数据的样本，不能标为端到端通过 |

公开scopes为openid、mcp.tools、offline_access。发现文档中还列出其他grant类型，不意味着个人客户端可以绕过用户授权。本次不创建账号、不获取任何人的token、不尝试未授权数据读取。

适配时按实际tools/list与inputSchema确定能力，再与官方工具指南核对。文档列有活动查询、详情、分圈和FIT获取；活动labelId与sportType应配套保留。文本/结构化返回都须保留证据与单位，无法可靠归一化时报告SCHEMA_MISMATCH，不能从示例数值猜单位。FIT下载还有独立限额，不在每次分析中全量下载。

官方FAQ描述当前无状态MCP及令牌轮换，不能沿用旧版长会话假设；元数据声明、官方文档、真实工具结果要分开记录。

用户没有COROS设备，不妨碍本轮公开入口验证和后续离线契约测试。真实记录正确性及授权更新仍需要本人或明确授权志愿者的账号与数据；无需要求项目作者先购买手表，也不能凭空完成这一级验证。

## 3. 统一接口设计（待实现）

建议渐进新增，不立即搬动旧文件：

```text
running_coach/
  models.py                 # Activity、Lap、Coverage、SyncResult
  adapters/base.py          # 平台无关Protocol与能力声明
  adapters/garmin.py        # 包装现有可用Source
  adapters/coros_mcp.py     # 仅官方MCP、读取工具白名单
  adapters/strava_mcp.py    # 官方路线候选；用途/客户端不允许时关闭
  auth/store.py             # 凭据存储接口
  auth/windows_dpapi.py     # Windows实现；核心模块不导入win32crypt
  auth/oauth.py             # 回调事务、state、PKCE及安全元数据发现
  storage.py                # v2 SQLite及迁移
  sync_service.py           # 每次分析前自动刷新，生成一致快照
  errors.py                 # 稳定的机器状态
```

协议建议提供capabilities、auth_status、begin_authorization、complete_authorization、ensure_access、fetch_activities、fetch_activity、fetch_laps、fetch_health及close。可选能力明确标注；截图入口不假装具备云端刷新。分页/游标、缓存期限、允许的AI使用与持久化策略由平台能力决定，不能所有适配器一刀切。

Activity统一字段建议：schema_version、provider、account_key、source_activity_id（文本，必要时保留复合来源键）、sport、source_sport、start_time_utc、source_timezone、distance_m、timer_time_s、elapsed_time_s、moving_time_s、avg_hr_bpm、max_hr_bpm、cadence_spm、elevation_gain_m、reported_pace、calculated_pace及计算所用时长、available_metrics、quality_flags、fetched_at、provenance。

缺失值使用null，不填0；保留原始语义，不将品牌恢复分数、移动时长与计时混为一谈。分圈和有时间戳的采样序列分别存储，不塞入概要强制字段。原始响应及GPS按授权和用途单独控制，默认不进入AI摘要。

## 4. 自动获取、缓存与去重

分析请求 → 确认已授权平台和用途 → 检查/更新令牌 → 向云端获取相关日期记录 → 校验/归一化 → 按政策写入允许的缓存 → 基于本次快照分析。

- 首次运行引导用户授权；已授权且令牌有效时不反复弹窗。没有授权就返回AUTH_REQUIRED，不返回伪造空列表。
- 每次分析触发一次云端刷新事务，多个分析工具共享此次快照；不让七个工具各自重复同步整段历史。先请求概要，仅对新增、变化或所需详情补查。
- 同一平台/账号用锁合并并发刷新；只在完整分页成功后推进水位。使用小范围重叠窗口补捉延迟上传及修改；只有开始时间游标不足以发现历史修改，另需受支持的更新通知或周期复查。
- 核心唯一约束为(provider, account_key, source_activity_id)。本地账号标识不进入公开日志；换账号不会继续混用原有库。
- 分开统计inserted/updated/unchanged；全部成功且无变化才报告NO_NEW_DATA。原来的activities计数不能用于此判断。
- 跨平台同次活动是关联候选，不等于同源主键重复。按时间、距离、时长和设备证据核对，保留来源，确认后统计一次；不能按“同一天”或相似配速自动合并。
- 平台限制持久化或跨源处理时不写通用长期库，也不将结果再包装为自建MCP输出。到期清理、删除/撤权和来源删除分别处理。
- 网络失败/限流时明确说明刷新失败和缓存时间，允许用户在知情条件下分析旧缓存，不写“最新”。云端尚未收到手表数据时也不能由本地程序创造记录。

## 5. 凭据、状态和安全测试

优先延用Windows DPAPI，按provider/account/issuer/client分区保存。仅加密token不等于数据加密；设置数据目录访问权限，后续可选全盘或数据库加密。refresh_token轮换需原子写入和并发锁；撤权、refresh失效需重新授权，不无限重试。Garmin Key到期与Strava/COROS令牌刷新使用不同策略。

OAuth只接收指定回调地址，校验state、防重放；COROS按元数据支持使用PKCE S256。Strava不假定支持尚未验证的PKCE扩展。验证issuer/resource/audience，区域切换后不跨主机转发旧Bearer；元数据URL须HTTPS并限制可信来源，避免SSRF。只用明确允许的MCP读取工具，防止自动调用写入工具。

建议将授权状态、同步结果、缓存新鲜度拆开：

| 状态/错误 | 含义与处理 |
| --- | --- |
| NOT_CONFIGURED / AUTH_REQUIRED | 尚未配置/尚未授权，引导首次连接 |
| AUTH_FAILED / REAUTH_REQUIRED | 授权被拒绝、撤权或刷新凭据无效；不靠循环重试解决 |
| SCOPE_INSUFFICIENT | 已授权但缺必要权限 |
| API_UNSUPPORTED | 官方没有相应能力，禁止伪造实现 |
| POLICY_RESTRICTED / CLIENT_UNSUPPORTED | 用途、平台政策或客户端范围不允许当前路线 |
| NETWORK_ERROR / PROVIDER_UNAVAILABLE | 超时/DNS/TLS/5xx分别记录可重试性，不当作无活动 |
| RATE_LIMITED | 记录可重试时间/额度，停止高频重试 |
| SCHEMA_MISMATCH / PROTOCOL_ERROR | 数据或MCP协议不匹配，不猜字段 |
| SUCCESS / NO_NEW_DATA / PARTIAL | 成功有变化/成功无变化/仅部分取得；同时给覆盖与缓存时间 |

过期token可先作为内部授权状态，刷新成功后不把整次分析标为失败。401与403需要结合具体响应和授权状态判断；未知错误保持UNKNOWN_ERROR，不把所有403写成账号失效。

新增测试清单：OAuth拒绝/错误state/回调重放、过期与撤权、令牌轮换及并发、区域issuer不匹配、日志脱敏；跨平台ID冲突、换账号、时区跨午夜、缺测/单位；重复分页/重试/中途失败/无变化/活动修改及删除；COROS契约样例、读取白名单、未知工具/单位拒绝；限流/超时/旧缓存提示；Strava策略门禁、到期清理和禁止数据再暴露。

Git发布前对暂存文件做密钥/token/私有路径及不应分发的活动文件检查，报告仅给文件和行号，不打印命中内容。CI仅用虚构数据，无真实平台secret；不能因为单元测试通过便标注真实平台已连接。

## 6. 分期验收

1. **先建立边界**：核心模型、状态与能力接口，独立v2存储及虚构契约测试；旧Garmin测试全部通过，旧服务不变。
2. **包装Garmin**：复用现有认证/同步，实现分析前refresh与快照；核对原CLI、七工具和训练汇总回归。
3. **接COROS官方MCP**：先离线协议和映射测试，再由有权限的测试账号完成授权、tools/list、新活动/分圈核对、刷新与撤权；未通过的层级始终标未验证。
4. **处理Strava边界**：优先官方MCP个人使用路线；确认客户端/订阅/用途后再实测。普通OAuth API研究不自动变成当前AI Skill的可用数据桥。
5. **发布**：依赖锁定、无凭据CI、内容扫描、MIT许可证与干净安装；GitHub发布是后续独立步骤，本轮未执行。

## 官方来源

- [Strava OAuth](https://developers.strava.com/docs/authentication/)
- [Strava API Policy](https://www.strava.com/legal/api_policy)，重点3.5、5.3、5.16、6.2。
- [Strava配额与应用人数](https://developers.strava.com/docs/rate-limits/)
- [Strava官方AI连接说明](https://support.strava.com/en-us/articles/15401531-how-do-i-connect-strava-to-an-ai-assistant)
- [COROS MCP自助接入](https://support.coros.com/hc/en-us/articles/53181619102996-Build-on-COROS-MCP)
- [COROS Partner API](https://support.coros.com/hc/en-us/articles/53181766856724-Partner-API-Access)
- [COROS工具指南](https://github.com/coroslab/COROS-MCP/blob/main/docs/en/tools.md)
- [COROS FAQ](https://github.com/coroslab/COROS-MCP/blob/main/docs/en/faq.md)

公开端点探测只证明当时网络与授权发现行为，不保证未来可达性、地区兼容或全部账号能力。官方文档更新时应重新核对。
