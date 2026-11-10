# 多平台接入状态

核对日期：2026-11-10。此文件为能力边界与开发路线，不是新增适配器代码。常规截图分析不需要读取完整技术方案。

## 当前可用

- Garmin：用户自己的Personal API Key、本地DPAPI凭据、同步CLI、SQLite缓存与七个只读MCP工具。查询工具读缓存，不会自动联网同步；先检查同步状态和实际日期。
- 运动截图：按screenshots.md读取可见字段，结合analysis.md及training-plans.md生成分析和建议。没有平台账号连接也能使用。
- vivo/Keep文件实验：已有字段映射与有限样本核对，不能宣称通用导入或账号实时连接已完成。

## COROS：公开授权发现通过，真实账号尚未验证

官方入口为https://mcp.coros.com/mcp。本项目无凭据探测收到401授权挑战，随后资源元数据和OAuth元数据返回200；本次发现指向中国区issuer，声明支持S256与refresh_token。这不是MCP握手完成，也没有完成账号授权、tools/list、真实活动读取或令牌更新。

官方自助MCP不要求Partner API申请。获得合法账号授权后须按实际工具列表、inputSchema和单位验证，只用读取工具；不要自动创建或修改训练计划。没有测试账号及真实记录时明确标为未验证，不绕过认证、不使用他人凭据。

## Strava：普通OAuth API不直接接入当前AI数据桥

官方OAuth技术路线存在，但API Policy对普通API数据进入AI上下文、自建MCP暴露和长期缓存有限制。不能把“能够OAuth授权”解释为“允许进入本技能的统一AI分析与长期数据库”。不通过匿名化、汇总或换名字规避限制。

优先评估官方https://mcp.strava.com/mcp及其个人使用、订阅、受支持客户端和缓存条件；未完成授权实测，不承诺当前宿主能够接通。按官方允许范围处理数据，不向未获准的自建MCP转发。

## 待实现，不作为功能宣传

统一Activity/Lap模型、独立平台适配器、跨平台/账号唯一键、每次分析前刷新、授权状态细分、凭据轮换与平台专用缓存政策。新增这些代码并通过相应测试前，不声称它们已在运行。

开发顺序：保留旧Garmin兼容入口 → 核心模型与独立v2缓存 → 包装Garmin及分析前刷新 → COROS官方MCP授权与数据测试 → 在官方许可范围评估Strava。

## 官方来源

- [COROS自助MCP](https://support.coros.com/hc/en-us/articles/53181619102996-Build-on-COROS-MCP)
- [COROS工具文档](https://github.com/coroslab/COROS-MCP/blob/main/docs/en/tools.md)
- [Strava OAuth](https://developers.strava.com/docs/authentication/)
- [Strava API Policy](https://www.strava.com/legal/api_policy)
- [Strava官方AI连接](https://support.strava.com/en-us/articles/15401531-how-do-i-connect-strava-to-an-ai-assistant)
