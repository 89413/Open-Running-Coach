# 参与贡献

欢迎改进技能表达、截图处理、安装流程、虚构样例与测试。实现新平台连接前先核实官方接口、授权、用途和缓存限制；不采用绕过认证或平台限制的方案。

提交PR时说明问题、行为变化、验证方式及限制。功能未实现或未经真实账号验证时保持相应标记。训练建议不以作者个人成绩作为默认值。

仅提交虚构数据。不要提交API Key、OAuth code/token、Cookie、数据库、个人报告、真实运动截图或轨迹；错误报告先移除这些信息。安全问题请勿公开附上密钥或健康记录。

技能格式校验按skill-creator流程；安装器测试运行 `python -m unittest discover -s . -p test_install_skill.py -v`。Garmin测试先在独立环境安装requirements-garmin.txt，再运行test_assistant.py和隔离的test_mcp.py，不需要真实账号。

贡献沿用本项目MIT许可证；第三方依赖保留其自身许可证，平台数据权限不由本项目许可证授予。
