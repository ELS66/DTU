# 宝塔面板部署与 GitHub 更新方案

状态：宝塔已同步 GitHub 代码，Node.js 24 构建和后端测试已在服务器通过；PM2 进程、站点反向代理及数据库尚未验证。

GitHub 仓库：`https://github.com/ELS66/DTU.git`；发布分支：`main`。

## 现在在宝塔的配置顺序

1. 进入 **网站 → 添加站点 → Git 创建**。如提示安装 Webhook 插件，按面板提示安装。使用上面的仓库地址和 `main` 分支；目标目录必须为空。私有仓库建议用只读 Deploy Key，服务器可以连通 GitHub 后再换 SSH 仓库地址。
2. 该 Git 站点负责同步源代码。不要把仓库根目录作为对外网站根目录：它含后端配置、数据库迁移和开发文档。业务域名与 H5/Admin 静态网站需另行配置；在此之前保持 Git 站点不对外服务或限制访问。
3. Git 站点创建成功后，在 **站点设置 → Git 管理 → 仓库** 找到并复制 Webhook URL。源码同步已验证后，可填写下面的构建命令；PM2 首次启动前不配置服务重启。
4. 到 GitHub 仓库 **Settings → Webhooks → Add webhook**，填宝塔生成的 URL，Content type 选 `application/json`，事件只选 `push`。优先使用已配置 HTTPS 的接收地址，保持 SSL 验证开启。如果宝塔接收端支持 GitHub 签名密钥，在两端配置同一密钥。仅有 URL 访问密钥时，密钥必须保密并定期轮换；只执行仓库内固定的构建脚本，不允许请求参数拼接成任意命令。数据库迁移和服务重启在验签、备份与回滚能力确认后再接入。
5. 在 GitHub 的 Recent deliveries 和宝塔 Git 管理日志查看投递结果，并确认服务器同步到目标提交。首个测试仅验证代码同步，不代表后端、Admin、H5 已上线。

以上路径来自[宝塔官方 Git 建站与 Webhook 文档](https://docs.bt.cn/practical-tutorials/create-from-git-website)。正式后端服务在构建及数据库准备好后，再按[宝塔 Node 项目文档](https://docs.bt.cn/practical-tutorials/nodejs-pm2-deployment)单独创建。

## 当前阶段的宝塔构建脚本

在宝塔 Git 管理的“部署脚本”中填入：

```bash
bash deploy/baota-release.sh
```

发布脚本会先调用原有的 `baota-build.sh`，所以现在仍只构建，不启动或重启服务。它从自身位置定位仓库根目录，仅在 `main` 分支运行。服务器须已安装 **Node.js 22～26** 和 npm；生产建议 Node.js 24 LTS。如宝塔安装的工具没有加入 `PATH`，可设置 `NODE_BIN` 和 `NPM_BIN` 为实际可执行文件路径。脚本运行 `npm ci`、TypeScript 构建和测试，检查输出文件，并在 Git 管理日志中打印成功或失败。构建产物为 `backend/dist/main.js`。

当前仓库尚无可用的设备管理业务功能，构建成功只证明服务骨架可运行。脚本不连接生产数据库，也不重启现有服务。确认宝塔 webhook 接收端的认证/验签方式后再启用自动执行；不能让匿名公网请求直接触发服务器命令。

## 用宝塔 PHP 站点承接 API 域名

可以沿用宝塔的 **PHP 项目/传统站点** 来管理域名和 HTTPS；这里的 PHP 站点只承担 Nginx 入口，后端依旧由 Node.js 运行。当前站点对外监听 `7927`，Node 后端只在本机监听 `7926`，不能让两者监听同一个端口。站点根目录必须是一个不含仓库源码的独立空目录，不能指向 `/www/wwwroot/DTU`。如果现有 Git 站点的根目录已指向仓库，就新建独立 PHP 站点或调整它的对外根目录后再绑定业务域名，例如创建 `/www/wwwroot/dtu-public` 并把站点根目录设为该目录。

先在服务器上用与后续 Git 部署脚本相同的系统用户启动 PM2。确认 `node`、`npm`、`pm2` 都来自预期的 Node.js 24 环境，再执行：

```bash
cd /www/wwwroot/DTU
pm2 start deploy/ecosystem.config.cjs
pm2 save
curl --fail http://127.0.0.1:7926/health
```

健康检查应返回 `{"status":"ok"}`。`deploy/ecosystem.config.cjs` 固定只启动一个进程，默认监听 `127.0.0.1:7926`；需要其他端口时，在启动和部署脚本的环境中使用同一个 `PORT` 值。PM2 必须在开机后恢复进程；按服务器现有 PM2 安装方式配置开机启动，并重启服务器验证一次。

将 PHP 站点的 `listen` 两行改为 `listen 7927;` 和 `listen [::]:7927;`，再到 **设置 → 反向代理** 添加规则，目标 URL 填 `http://127.0.0.1:7926`，代理目录选 `/`。也可以把 `deploy/nginx-api-location.conf.example` 中的 `location /` 放进该站点 Nginx 的 `server` 块，替换原有同名规则；不要在同一个站点重复配置两份 `location /`。保存后先执行 `nginx -t` 检查配置，再重载 Nginx。公网域名和证书在该 PHP 站点中配置，Node 的 7926 端口保持只监听本机。若站点仍使用 IP 和明文 HTTP，验证地址为 `http://114.132.81.183:7927/health`。

以上配置和健康检查都通过后，可把宝塔 Git 管理的部署脚本改为：

```bash
DTU_PM2_RELOAD=1 bash deploy/baota-release.sh
```

这会在每次成功构建后重载已有的 `dtu-api` PM2 进程，再检查 `/health`。如果宝塔安装的 Node 或 PM2 不在部署脚本的 `PATH` 中，先在脚本前设置 `NODE_BIN`、`NPM_BIN`、`PM2_BIN` 的实际可执行文件路径。Webhook 脚本与手动启动 PM2 必须使用同一个系统用户或同一个 `PM2_HOME`，否则会报告找不到 `dtu-api`。当前服务只提供健康检查，设备管理业务功能仍在开发，不应把它当成正式平台。数据库迁移尚未纳入自动部署。

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
