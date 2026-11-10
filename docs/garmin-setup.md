# 可选：Windows佳明个人连接

只使用截图时跳过本文件。此指南面向用户在自己的Windows电脑读取自己的数据；不需要项目作者的账号、密钥或服务器。

## 1. 准备运行环境

需要Python 3.12或更新版本，以及能运行本地MCP的宿主。进入本项目目录，在PowerShell执行：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-garmin.txt
```

确认`py -3 --version`符合版本要求。此安装命令由使用者运行，安装skill不会自动安装依赖；Windows专用的DPAPI与文件锁实现尚未移植到macOS/Linux。

## 2. 配置自己的区域和密钥

从`config.example.json`新建自己的`config.json`，不要覆盖已有配置。中国版填写`{"region":"cn"}`，国际版填写`{"region":"com"}`。本地日期当前按Asia/Shanghai（UTC+8）计算，其他时区的日界线统计尚未验证。

在本人Garmin Connect网页账号的Personal API Key设置页创建密钥，并按平台条款和有效期使用。[官方个人接口说明](https://developer.garmin.com/gc-developer-program/personal/personal-api)。不要把密钥发到聊天、放入命令参数或提交Git。

```powershell
.\.venv\Scripts\python.exe -X utf8 assistant.py configure
.\.venv\Scripts\python.exe -X utf8 assistant.py check
```

`configure`在本地终端读取密钥且不回显，用当前Windows用户的DPAPI加密保存。`check`会联网获取一小份活动列表验证授权，不修改平台记录。报错时核对区域、网络、密钥状态；不要切换到来源不明的登录脚本。

## 3. 同步与覆盖检查

```powershell
.\.venv\Scripts\python.exe -X utf8 assistant.py sync --days 7 --limit 200
.\.venv\Scripts\python.exe -X utf8 assistant.py status
```

程序读取平台数据并写入本机缓存；不改平台记录。只有同步成功且所需活动实际存在，才能分析新跑步。`running`、`partial`、`failed`以及达到活动上限均不能当作完整更新；按状态和实际日期处理。默认同步多种活动和健康数据，只需活动时增加`--activities-only`。不默认请求所有可选敏感接口。

手表须先上传活动至Garmin Connect。MCP查询只读缓存，不触发联网刷新，也没有运行时零延迟承诺。本项目不会自动创建后台定时任务；电脑不开机时无法运行本地同步。

## 4. 注册本地MCP（Codex示例）

先运行`codex mcp list`检查已有连接；已能用现有Garmin工具的用户保留原配置，不重复注册或替换。

新用户在项目目录取得两个绝对路径，再注册：

```powershell
$garminCoachPython = (Resolve-Path '.\.venv\Scripts\python.exe').Path
$garminCoachServer = (Resolve-Path '.\server.py').Path
codex mcp add garmin-running -- "$garminCoachPython" -X utf8 "$garminCoachServer"
```

该命令会修改用户的Codex MCP配置，路径内不含密钥。执行前确认名称尚未使用；不要把作者机器的绝对路径原样复制进去。CLI不在PATH或宿主不同，则用其本地MCP设置填入同样的可执行程序及参数。

语法已据[OpenAI官方MCP说明](https://learn.chatgpt.com/docs/extend/mcp)及本地`codex mcp add --help`核对；本文未替使用者执行注册。

## 5. 调用技能

安装README中的skill后，在已加载MCP的聊天中输入：

> 使用 $open-running-coach，先检查佳明同步状态和实际覆盖日期，再分析我最近一次跑步；如缺恢复数据请说明。

七个只读工具：`get_sync_status`、`get_recent_activities`、`get_activity_detail`、`get_activity_laps`、`get_health_trends`、`get_training_summary`、`compare_periods`。首次尚无缓存时返回空数据，不代表已有活动或授权成功。

## 数据和发布范围

`.secrets`是加密凭证缓存，`data`是活动及健康数据缓存；健康数据库本身不因DPAPI凭证加密而自动加密。不要分享这两个目录、密钥原文件或`config.json`。工具输出交给AI宿主后会参与宿主处理，不代表完全离线。

本地功能测试用虚构数据；其他账号、区域和全新环境安装仍需用户实际试验。个人API密钥只用于本人访问；将本项目改造成多人商业服务须另核实平台方案。[Garmin个人接口FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/)。
