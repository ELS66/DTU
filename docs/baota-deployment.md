# 宝塔面板部署与 GitHub 更新方案

状态：用户确认宝塔已同步 GitHub 代码；后端构建脚本待在宝塔执行，运行环境和数据库尚未验证。

GitHub 仓库：`https://github.com/ELS66/DTU.git`；发布分支：`main`。

## 现在在宝塔的配置顺序

1. 进入 **网站 → 添加站点 → Git 创建**。如提示安装 Webhook 插件，按面板提示安装。使用上面的仓库地址和 `main` 分支；目标目录必须为空。私有仓库建议用只读 Deploy Key，服务器可以连通 GitHub 后再换 SSH 仓库地址。
2. 该 Git 站点现阶段只负责同步源代码。不要把仓库根目录作为对外网站根目录：它含后端配置、数据库迁移和开发文档。业务域名与 H5/Admin 静态网站需在构建产物出现后分别配置；在此之前保持 Git 站点不对外服务或限制访问。
3. Git 站点创建成功后，在 **站点设置 → Git 管理 → 仓库** 找到并复制 Webhook URL。源码同步已验证后，可填写下面的构建命令；目前不配置数据库迁移或服务重启。
4. 到 GitHub 仓库 **Settings → Webhooks → Add webhook**，填宝塔生成的 URL，Content type 选 `application/json`，事件只选 `push`。优先使用已配置 HTTPS 的接收地址，保持 SSL 验证开启。如果宝塔接收端支持 GitHub 签名密钥，在两端配置同一密钥。仅有 URL 访问密钥时，密钥必须保密并定期轮换；只执行仓库内固定的构建脚本，不允许请求参数拼接成任意命令。数据库迁移和服务重启在验签、备份与回滚能力确认后再接入。
5. 在 GitHub 的 Recent deliveries 和宝塔 Git 管理日志查看投递结果，并确认服务器同步到目标提交。首个测试仅验证代码同步，不代表后端、Admin、H5 已上线。

以上路径来自[宝塔官方 Git 建站与 Webhook 文档](https://docs.bt.cn/practical-tutorials/create-from-git-website)。正式后端服务在构建及数据库准备好后，再按[宝塔 Node 项目文档](https://docs.bt.cn/practical-tutorials/nodejs-pm2-deployment)单独创建。

## 当前阶段的宝塔构建脚本

在宝塔 Git 管理的“部署脚本”中填入：

```bash
bash deploy/baota-build.sh
```

此脚本从自身位置定位仓库根目录，仅在 `main` 分支运行。服务器须已安装 **Node.js 22～26** 和 npm；生产建议 Node.js 24 LTS。如宝塔安装的工具没有加入 `PATH`，可设置 `NODE_BIN` 和 `NPM_BIN` 为实际可执行文件路径。脚本运行 `npm ci`、TypeScript 构建和测试，检查输出文件，并在 Git 管理日志中打印成功或失败。构建产物为 `backend/dist/main.js`。

当前仓库尚无可用的设备管理业务功能，构建成功只证明服务骨架可运行。脚本不连接生产数据库，也不重启现有服务。确认宝塔 webhook 接收端的认证/验签方式后再启用自动执行；不能让匿名公网请求直接触发服务器命令。

构建成功后，如要把当前骨架登记成宝塔 Node 项目，项目目录选仓库下的 `backend`，启动文件选 `dist/main.js`，运行版本建议 Node.js 24 LTS，监听端口默认 3000（可用 `PORT` 环境变量修改）。健康检查路径为 `/health`。此时只提供健康检查接口，设备管理业务功能仍在开发，不应把它当成正式平台。

## 发布路径

```text
开发机提交 -> GitHub 指定分支 -> GitHub webhook -> 宝塔上的受限接收端
  -> 验证 GitHub 签名与仓库/分支 -> 拉取固定提交
  -> 构建与健康检查 -> 切换服务 -> 记录部署结果
```

接收端只接受 GitHub `push` 事件、约定仓库和约定分支；验证 `X-Hub-Signature-256` 和共享密钥。部署进程使用独立的低权限账号，密钥仅放在服务器环境中，不能写入仓库、日志或前端。仅允许串行部署，拒绝重复事件；固定到事件中的 commit SHA，避免部署过程中分支移动。

宝塔 Nginx 负责 HTTPS、反向代理与静态站点；Node 后端以宝塔 Node/PM2 项目运行。PostgreSQL、Redis 和 EMQX 是平台依赖，但实际采用宝塔插件、系统服务还是容器，要先检查服务器现状。生产数据库与 Broker 管理端口不直接开放公网。

部署过程先备份与校验迁移兼容性，构建新版本并做健康检查，通过后再切换流量。数据库迁移不默认可以自动回滚；涉及破坏性迁移时先采用兼容性变更，再单独清理旧字段。发布失败保留当前服务版本，记录错误和可恢复操作。

## 配置前需要的信息

- GitHub 仓库地址、默认分支和推送权限。
- 宝塔服务器操作系统与架构、Node/npm/Docker 是否可用。
- 域名分别如何分配给 Admin、H5、API、MQTT TLS。
- 服务器现有 PostgreSQL、Redis、EMQX 情况与备份位置。
- 宝塔是否已有可信的 GitHub webhook 接收插件；若有，核查签名验证和命令执行范围。

在这些信息明确之前，不将本地 `deploy/compose.yml` 当作宝塔生产部署配置，也不向任何外部 webhook 发送测试请求。
