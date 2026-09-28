# 离线 DTU 模拟器（第一步）

从仓库根目录运行 `python dtu-simulator/demo.py`，可看到配置应用、绝对值命令、二进制遥测与持久接收 ACK 的一次往返。使用 Python 标准库，无需 MQTT Broker 或真实设备。

测试命令：`python -m unittest discover -s dtu-simulator -p 'test_*.py' -v`。测试覆盖重复命令不再次执行、过期配置、配置版本不匹配、传感器超时、补传标记和 ACK 清除待发送批次。

这个模拟器仅保存内存状态，写操作是模拟结果，不会访问串口，也不代表真实 DTU 的掉电持久化、物理回读或 MQTT TLS 已验收。后续在 MQTT 身份与数据库接入完成后，为它增加 Broker 连接、断网重投递和完整闭环测试。
