# 发布到 GitHub：xiao-yue-running

目标仓库：https://github.com/89413/xiao-yue-running
版本：v0.1.0-beta.1。项目与技能名为Open Running Coach，仓库名xiao-yue-running不影响技能调用。

## 上传源码

1. 打开仓库。已有文件时选择 **Add file → Upload files**；空仓库点击初始化提示中的 **uploading an existing file**。
2. 打开本次生成的干净上传目录，将里面的文件与子文件夹上传到仓库根目录。根目录应直接显示README.md、LICENSE、scripts、skills等，而不是再套一层本机文件夹。
3. 核对上传清单。网页上传不会执行.gitignore，因此只使用这份干净目录，不拖入整个个人工作区或原始项目。
4. 若仓库已有README、LICENSE或其他同名文件，先核对差异；仅替换本项目相关文件，不覆盖无关工作。MIT为本项目选定许可。
5. 提交说明填写 `Prepare v0.1.0-beta.1: Garmin and screenshot skill`，提交至你准备发布的分支；受保护分支按页面要求创建分支/PR。
6. 提交后检查README渲染、许可证识别及skills/open-running-coach/SKILL.md是否可打开。

不要只上传源码ZIP就结束：GitHub不会把作为普通文件上传的ZIP展开成仓库源码。上传目录包含的文件数量低于网页单次100文件限制，各文件也低于25MiB限制。

## 发布技能下载包

1. 仓库页面选择 **Releases → Draft a new release**。
2. 新建标签 `v0.1.0-beta.1`，目标分支选择已上传并核对的源码分支。
3. 标题填写 `Open Running Coach v0.1.0-beta.1`。
4. 将根目录RELEASE_NOTES.md的正文复制到描述。
5. 在附件区上传 `open-running-coach-v0.1.0-beta.1-skill.zip`；源码ZIP可选，GitHub也会生成标签对应的源码归档。
6. 勾选 **This is a pre-release**，检查后选择 **Publish release**。

## 分享与使用

分享仓库首页链接即可。使用者可下载仓库ZIP并解压，在含scripts目录的项目根目录执行 `python scripts/install_skill.py`。技能目录包则解压得到open-running-coach文件夹，手动放入当前用户的`.codex/skills`。已有同名技能时先备份或使用项目安装器的`--update`功能，不直接覆盖未知修改。

安装技能不等于已接通Garmin。截图模式可直接附图使用；Garmin需按docs/garmin-setup.md配置自己的凭据。不要把密钥、数据库或个人截图发到Issues。

## 官方操作依据

- https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository
- https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository

本说明不表示仓库已经上传或Release已经发布。若GitHub页面提示需要登录，由使用者在GitHub完成；不要向聊天发送密码或令牌。
