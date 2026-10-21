# API 绘制脚本说明

当前工程与器件/页面映射以 ../manifests/design.json 为准。脚本包含分阶段绘制、库导入、排错和读取快照，不能按文件名顺序批量重放；已有连线时移动器件须同时处理导线和标注。

V0.3 自动选择检查：运行 verify-auto-selection.py，读取 ../reports/auto-selector.net。必须先从当前工程重新导出实际网表；历史网表通过不代表当前画布通过。

Invoke-Eda.ps1 会检查本机 Bridge 的服务标识和当前连接窗口。执行前还必须核对工程及页面 UUID。切换页面、变更元件与读取导出结果分开执行，并回读确认；API 返回成功不能替代网表检查。

已停用旧的批量主器件方案、旧 TTL 替换脚本和可能使多单元符号客户端重载的位置修改脚本。createNetLabel 在本环境可能创建属性但返回 undefined；导线已自带网络名称属性，可读取导线属性后修改样式。API 对导线网络属性的 key 返回 Name，源文件使用 NET。新增元件需检查唯一 ID 非空；多单元同一物理元件使用同一 ID，防止网表导出覆盖。

脚本不是全板一键重建程序，不能用于直接生成未审核的生产文件。

V0.11 当前工程 UUID 为 1d7fb27b7ad9306bc25c90ee476429c9e681ffecce79136ba05149eca7bba1b0。revision-v11.json 和实际导出的 V0.11 网表为本版依据。prepare/revise/prune/sync/apply 脚本为阶段性操作记录，不具备幂等性，不可对完成后的工程重放；恢复应使用已导出的 epro2。verify-interface-v11.py 只读核对原理图和 PCB 快照，并生成验证记录及 BOM。
