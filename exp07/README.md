# EXP-07 · 去掉比值有界性后的反例

本实验对应 RCS v1.1 备注 5.1，并对照条件 5.1、定理 5.1 与式 (13)、(31)–(38)。它展示：**保留分子、分母的小相对扰动条件，但缺少原始比值的统一有界性时，式 (35) 的读数差趋零结论可以失败。**

## 模型与精确关系

从整数 $n\ge2$ 开始，取

$$
a_n=a'_n=n^3,\qquad b_n=n,\qquad b'_n=n-1,\qquad \eta_n=\frac1n.
$$

因此

$$
q_n=\frac{a_n}{b_n}=n^2,\qquad q'_n=\frac{a'_n}{b'_n}=\frac{n^3}{n-1},
$$

$$
\Delta_n=|q'_n-q_n|=\frac{n^2}{n-1}=n+1+\frac1{n-1}>n.
$$

分子、分母的绝对扰动分别为 $0$ 和 $1$，相对扰动 $|a'_n-a_n|/a_n$ 和 $|b'_n-b_n|/b_n$ 分别为 $0$ 和 $1/n$。式 (32) 的校准上界仍为 $\eta_n b_n$。式 (32)、(33) 成立。式 (33) 在每个阶段都取等号，因为 $|b'_n-b_n|=1=\eta_n b_n$。另有 $b'_n=(1-\eta_n)b_n=n-1>0$，式 (37) 成立。对任意正整数 $k$，式 (34) 的充分阈值取 $N(k)=\max(2,k+1)$，因为 $n\ge N(k)$ 时 $1/n\le1/(k+1)<1/k$。在 $k=2,n=2$ 处，$\eta_2=1/2$ 不满足严格小于，故阈值从 $n=3$ 起才适用。

起点核验为

| $n$ | $q_n$ | $q'_n$ | $\Delta_n$ |
| ---: | ---: | ---: | ---: |
| 2 | 4 | 8 | 4 |
| 3 | 9 | 27/2 | 9/2 |

## 全尾部证书与预期结论

- **式 (31) 失败。** 对任意正有理数 $M$，取 $n=\lfloor M\rfloor+2$。此时 $n\ge2$ 且 $n>\max(1,M)$，所以 $q_n=n^2>M$。不存在可供任意尾部使用的固定 $M$，式 (38) 的估计标为 **N/A**，程序不会计算该估计。
- **式 (35) 失败。** 对任意正有理误差上界 $H$ 和任意非负候选尾部阈值 $N$，取 $n=\max(2,N,\lceil H\rceil)$。此时 $n\ge N$，且 $\Delta_n>n\ge\lceil H\rceil\ge H$，从而严格有 $\Delta_n>H$。该构造对所有这类 $H,N$ 成立，不需要枚举中间阶段。
- **两条线程均违反式 (13) 的 RCS-4。** 固定 $k=2$，对任意候选阈值 $N$ 取 $n=\max(2,N)$，检查 $n$ 与 $2n$。原线程满足 $q_{2n}-q_n=3n^2>1/2$。扰动线程满足 $q'_n=n^2\cdot n/(n-1)\le2n^2$，同时 $q'_{2n}=4n^2\cdot2n/(2n-1)>4n^2$，故 $q'_{2n}-q'_n>2n^2>1/2$。
- **式 (36) 不适用。** 两条读数序列都不稳定，因而不存在本例中两条稳定线程的完备化值同值比较。

式 (31)、(35) 和两条线程的 RCS-4 失败都是**预期数学结果**；其余核验及证书通过时，报告仍应输出 `EXP-07 acceptance: PASS`，程序退出码为 0。

EXP-04 的 B 组与此不同：该组是式 (34) 的渐近可忽略性失效，两条 Pell 线程仍然稳定，分别实现 $\sqrt{2}$ 和 $\sqrt{2}/2$。本实验则是式 (34) 成立、式 (31) 和式 (35) 失效，且两条线程都不稳定。

## 参数与运行

计算核心兼容 Python 3.10+，只使用标准库；绘图另需 `requirements-plot.txt` 中的 Matplotlib。以下命令均从仓库根目录在 PowerShell 中执行。

单独计算（使用默认参数）：

```powershell
py .\exp07\exp07_unbounded_ratio.py
```

指定最小展示范围、重复精度和很大的见证阈值：

```powershell
py .\exp07\exp07_unbounded_ratio.py --max-index 2 --precision 2 --precision 10 --witness-index 1000000
```

参数含义：

| 参数 | 默认值 | 约束与用途 |
| --- | --- | --- |
| `--max-index` | 10 | 不小于 2 的整数；有限 CSV 只展示 $2$ 至该索引 |
| `--precision K` | 2、10、100 | 可重复指定的正整数；生成式 (34) 的衰减证书，不改变固定 $k=2$ 的 RCS-4 反证 |
| `--witness-index N` | 0 | 非负整数；直接构造候选阈值 $N$ 处的见证，可远大于展示范围 |
| `--output-dir` | `results/exp07` | 报告和两份 CSV 的输出目录 |

证书 CSV 对式 (31) 记录 $M=1/2$ 和 $M=N+1$ 两个样例，对式 (35) 记录给定阈值 $N$ 下的 $H=1/2$ 和 $H=5/2$ 两个样例。报告 L3 给出对任意正有理 $M,H$ 和非负整数 $N$ 的解析推导。

单独绘图：

```powershell
py .\exp07\plot_exp07.py --stage-csv .\results\exp07\unbounded_stages.csv --output-dir .\results\exp07\figures
```

只运行本实验及批跑入口的相关测试：

```powershell
py -m unittest tests.test_exp07 tests.test_run_all.TestExp07BatchIntegration -v
```

全仓库测试命令见[根目录 README](../README.md#验收)。无图形界面也可绘图；缺失、为空、含非既约分数或数学关系不一致的 CSV 会被拒绝并返回非零退出码。

## 证书与产物对应

| `results/exp07/` 中的文件 | 内容 |
| --- | --- |
| `exp07_report.txt` | L1 有限精确数据、L2 有限关系核验、L3 全尾部解析证书、L4 结论与适用范围 |
| `unbounded_stages.csv` | 展示阶段的整数计数、两种相对扰动、精确读数、$\Delta_n$、$\Delta_n-n$ 及式 (32)、(33)、(37) 状态 |
| `unbounded_certificates.csv` | 各精度的式 (34) 阈值，式 (31)、(35) 和两条 RCS-4 的直接见证，以及式 (38)、(36) 的 N/A 状态 |
| `figures/exp07_unbounded_ratio.png` | 左图为 $\eta_n=1/n$ 的相对分母扰动下降，右图为 $\Delta_n$ 的绝对读数差增长及下界 $n$ |

PNG 只展示有限样本，不能替代报告中的全尾部证书。绘图程序在边界读取并复核精确整数和既约分数，仅在绘制坐标时转换为浮点数。
