# V0.13 开窗露线修正复查包

当前版 Exposurefix：两个 GND 过孔移位，四项对应位置至开窗的最小间距增至约 0.274/0.470 mm。PCB DRC=0；整板厂家 DFM 尚未通过验收。

导入 Exposurefix-Gerber.zip 重跑 DFM。装配配套使用 Exposurefix-BOM-99.csv 与 Exposurefix-CPL-99-Top.csv（器件坐标与 Maskfix 相同）。原生工程及修正记录均在包内。

60×70 mm、四层、单面贴装、104 个封装/99 件实装，306 个过孔、322 个钻孔。原有 R36 阻焊桥及四角无铜安装孔修正保留。J6/J7 默认裸孔，不装不焊。生产 ZIP 已清除已确认的孔内铜占位及极小阻焊数值残点；原生自行重新导出后需要同样核对。
