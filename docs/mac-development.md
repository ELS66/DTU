# 在 Mac mini 上继续开发

当前固件入口为 `c5/`，目标 ESP32-C5，开发基线 ESP-IDF **5.5.1**。仓库同时保存平台源码、当前硬件工程、历史资料和厂商资料；大文件通过 Git LFS 管理。

## 获取项目

先安装 Git 和 Git LFS。已安装 Homebrew 时可以执行：

```sh
brew install git-lfs
git lfs install
git clone https://github.com/ELS66/DTU.git
cd DTU
```

正常克隆会下载当前版本的全部 LFS 资料。若想先开始开发，暂缓下载历史资料及厂商大文件：

```sh
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/ELS66/DTU.git
cd DTU
git lfs pull --include="docs/**,output/**,PCB/V0.14.4-最终资料/**,PCB/references/**" --exclude=""
```

以上两组克隆命令任选一组。跳过下载后，其余 LFS 文件暂时是文本指针；需要全部原文件时，在仓库内执行 `git lfs pull --include="" --exclude=""`。

## 安装固件环境

按[乐鑫 ESP-IDF 5.5.1 的 macOS 安装说明](https://docs.espressif.com/projects/esp-idf/en/v5.5.1/esp32c5/get-started/linux-macos-setup.html)安装系统依赖、Python 3、CMake 和 Ninja，然后安装对应版本的工具链：

```sh
mkdir -p ~/esp
cd ~/esp
git clone -b v5.5.1 --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
./install.sh esp32c5
. ./export.sh
```

在同一个终端进入项目的 `c5/` 后运行：

```sh
idf.py build
```

工程已默认指定 `esp32c5`。每次新开终端，先运行 `. ~/esp/esp-idf/export.sh`。不要复制 Windows 的编译器、Python 虚拟环境或 `build/`；Mac 应使用本机工具重新构建。`tools/*.ps1` 和当前 VS Code 任务面向 Windows，Mac 可先直接使用这里的命令。

## 主机自测

在仓库根目录执行，需本机 C 编译器（可通过 Xcode Command Line Tools 安装）和 Python 3：

```sh
mkdir -p c5/build-host
cc -Wall -Werror -std=c99 -Ic5/components/module_core/include \
  c5/tests/test_core.c c5/components/module_core/*.c \
  -o c5/build-host/test_core
./c5/build-host/test_core
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s c5/tests -p 'test_bench.py' -v
```

当前 Windows 基线通过 24,491 项核心检查和 25 项模拟器测试；以上 macOS 流程尚待 Mac mini 实机验证。

## 换机时另外处理

- `.env`、本机编辑器设置、构建缓存和运行数据按现有忽略规则不进入 Git；需要的私有配置应另行安全迁移。
- Windows 的 COM 端口在 Mac 上要换成实际 `/dev/cu.*` 设备；刷写前核对端口、供电和接线，步骤见 `c5/README.md`。
- `ML307R/` 中的 Windows 驱动、烧录工具以及 `PCB/.tools/` 内的平台相关依赖只作资料保存，不能当作 Mac 本机运行环境。
- 后端和网页依赖应在 Mac 上重新安装；Node 版本范围及启动方式见各目录的 `package.json` 和 README。
- 两台机器交替工作时，每次开始先拉取，结束后提交并推送；避免两边同时修改同一文件。

Git LFS 的下载选项见[官方命令说明](https://github.com/git-lfs/git-lfs/blob/main/docs/man/git-lfs-pull.adoc)。
