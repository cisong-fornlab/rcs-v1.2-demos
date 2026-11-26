# EXP-04 · 有限计数扰动鲁棒性

A 组取 $q_n=1+1/n$、$q'_n=1+3/(n-1)$（$n\ge2$）。有界且渐近可忽略的计数扰动使两条线程稳定、等价并共同实现 1；统一充分阈值取 $N(k)=7k+2$。B 组自含 Pell 递推并把分母翻倍：两条线程仍稳定，但分别实现 $\sqrt2$ 和 $\sqrt2/2$。式 (34) 预期失败，式 (38) 因 $\eta_n=1$ 而不适用。

在仓库根目录运行 `py .\run_all.py`。环境和依赖见[仓库说明](../README.md#运行)。报告应同时显示 `condition_34(B): False (expected)`、`(38): N/A`、两组各自的 `PASS` 和 `EXP-04 acceptance: PASS`。

| `results/exp04/` 中的文件 | 内容 |
| --- | --- |
| `exp04_report.txt` | A、B 两组的 L1–L4 精确数据、有限核验、全尾部证书与结论 |
| `count_stages.csv` | 两组的精确计数、扰动、读数、实际误差及式 (38) 适用状态 |
| `pell_intervals.csv` | B 组原 Pell 区间与减半扰动区间的宽度、界和嵌套核验 |
| `count_certificates.csv` | A 组全尾部证书，B 组 Pell 区间索引 `j`、稳定阈值 `2j`、式 (38) 状态和非等价见证 |
| `figures/exp04_count_robustness.png` | A 组误差与上界的衰减，B 组两条读数。B 组扰动读数恰等于两条读数的绝对差 |

依据为 RCS v1.1 条件 5.1、定理 5.1、命题 7.1，以及式 (13)–(14)、(31)–(39)、(49)–(57)。解析阈值可以超过展示范围，无需枚举到该阶段。报告和 CSV 中的 `sqrt(2)`、`sqrt(2)/2` 分别是 $\sqrt{2}$、$\sqrt{2}/2$ 的精确 ASCII 记号。

B 组在 $n=0$ 的实际差恰为 $1/2$，因此固定 $k=2$ 时严格比较失败。非等价证书的 `difference` 仅在已知精确差值时填写。未计算对应 Pell 项的见证由 `difference_formula` 和 `lower_bound` 给出解析证据。本例仅说明持续扰动可能改变完备化值，且两条线程在本例中均保持稳定。
