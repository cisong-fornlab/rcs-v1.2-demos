# EXP-01 · Pell 稳定线程与无理完备化值

实验用 Pell 递推生成精确有理读数，验证 RCS-4 稳定性。有限阶段的读数都是有理数，完备化值是满足 $x>0$、$x^2=2$ 的正根。

在仓库根目录运行 `py .\run_all.py`。环境和依赖见[仓库说明](../README.md#运行)。成功时报告显示 `EXP-01 acceptance: PASS`。

| `results/exp01/` 中的文件 | 内容 |
| --- | --- |
| `exp01_report.txt` | 模型、数学核验、解析证书与结论 |
| `pell_stages.csv`、`pell_intervals.csv` | 精确阶段读数与嵌套区间 |
| `pell_certificates.csv`、`pell_denominator_certificates.csv` | 通用幂次界和实际分母乘积证书 |
| `figures/exp01_readout_sequence.png`、`figures/exp01_enclosure_widths.png` | 读数序列与区间宽度 |

依据为 RCS v1.1 命题 7.1、备注 7.1、定理 4.2 和 5.2，以及式 (13)、(47)–(57)。分母证书的最小阈值相对于完整区间的宽度准则。稳定性和完备化值由报告中的解析证书给出。
