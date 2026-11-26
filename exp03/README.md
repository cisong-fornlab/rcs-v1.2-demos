# EXP-03 · 共尾细化不变性及非共尾对照

取 $q_n=1+(-1)^n/(n+1)$。两个共尾映射 $\phi_0(e)=2e$、$\phi_1(e)=2e+1$ 的拉回均保持原线程的完备化值 1。保序的非共尾映射 $\chi(e)=0$ 的拉回仍稳定，完备化值为 2。

在仓库根目录运行 `py .\run_all.py`。环境和依赖见[仓库说明](../README.md#运行)。报告应同时显示 `cofinal(chi): False`、`RCS-4(q_chi): True` 和 `EXP-03 acceptance: PASS`。

| `results/exp03/` 中的文件 | 内容 |
| --- | --- |
| `exp03_report.txt` | 共尾性、稳定性、等价关系与各线程的完备化值 |
| `cofinal_stages.csv`、`cofinal_thresholds.csv` | 精确阶段读数、共尾阈值和非共尾见证 |
| `cofinal_certificates.csv` | 稳定性、等价与非等价证书 |
| `figures/exp03_cofinal_invariance.png` | 映射阶段与读数的双面板图 |

依据为 RCS v1.1 定义 4.1、定理 4.3、备注 4.3，以及式 (13)–(14)、(28)–(29)。证书分别记录充分阈值 $2k$ 和原线程的最小稳定阈值 $2k-1$。本例表明缺少共尾性时，完备化值可能改变。
