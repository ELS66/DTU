# DTU 模拟器

从仓库根目录运行 `python dtu-simulator/demo.py`，可看到配置应用、绝对值命令、二进制遥测与持久接收 ACK 的一次往返。使用 Python 标准库，无需 MQTT Broker 或真实设备。

测试命令：`python -m unittest discover -s dtu-simulator -p 'test_*.py' -v`。测试覆盖重复命令不再次执行、过期配置、配置版本不匹配、传感器超时、补传标记和 ACK 清除待发送批次。

可选 MQTT 模式：先运行 `pip install -r dtu-simulator/requirements.txt`，启动 `deploy/compose.yml` 中的 EMQX，然后运行 `python dtu-simulator/mqtt_demo.py gateway-test`。模拟器订阅本机网关的 `config/set`、`command/set`、`telemetry/ack`，按 QoS 1 发布对应回复与二进制遥测；收到 STORED ACK 后移除待发送批次，重连与定时重试会保留原 bootId/sequence 并设置补传标志。默认每 5 秒采样、每 10 秒重试，可用 `--sample-interval` 和 `--retry-interval` 调整。远程 Broker 必须使用 `--ca-file` 启用 TLS；可传 `--username`、`--password`。

当前 MQTT 验证使用内存假客户端，尚未在真实 Broker 上联调。模拟器仅保存内存状态，写操作是模拟结果，不会访问串口，也不代表真实 DTU 的掉电持久化或物理回读已验收。EMQX 开发配置尚未设置设备身份认证和 Topic ACL，不可把它当成生产接入配置。
