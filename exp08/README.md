# EXP-08 · 区间缩宽但任意选值不稳定

本实验对应 RCS v1.1 定义 5.1、引理 5.1、定理 5.2、备注 5.2 及式 (40)–(44)、(13)，数学规格见 RCS v1.2 实验规范第 10 节。它展示：**有理包络的宽度趋于零，并不足以推出细化相干性，也不足以推出任意选值线程的 RCS-4 稳定性。**

## 模型与精确关系

从整数 $n\ge2$ 开始，偶数阶段取 $c_n=1$，奇数阶段取 $c_n=2$，并令

$$
a_n=c_nn,\qquad b_n=n,\qquad \alpha_n=1,\qquad \beta_n=0,\qquad M=2.
$$

所有原始计数均为正，$b_n>\beta_n$，且 $a_n/b_n=c_n\le M$；奇数阶段取到 $a_n/b_n=M$。由于 $a_n-\alpha_n=c_nn-1>0$，式 (41) 的 `max` 截断不生效：

$$
I_n=[L_n,U_n]=\left[c_n-\frac1n,c_n+\frac1n\right],\qquad w_n=\frac2n.
$$

令 $u_n=\alpha_n/b_n=1/n$、$v_n=\beta_n/b_n=0$。式 (44) 的中项、最终上界和实际宽度全部相等：

$$
w_n=\frac{2(a_n\beta_n+\alpha_nb_n)}{b_n^2-\beta_n^2}
=\frac{2(Mv_n+u_n)}{1-v_n^2}=\frac2n.
$$

因此引理 5.1 的前提和缩宽结论均成立。

## 相邻区间与全尾部反证

闭区间距离按实际左右顺序计算：

$$
\operatorname{dist}(I_n,I_{n+1})
=\max\{0,L_{n+1}-U_n,L_n-U_{n+1}\}
=1-\frac1n-\frac1{n+1}
=\frac{n^2-n-1}{n(n+1)}.
$$

对任意 $n\ge2$，该距离严格为正，所以相邻区间始终不相交，式 (42) 失败。同奇偶的区间具有相同中心并逐步缩宽，因此 $I_{n+2}\subsetneq I_n$。两个方向的精确样例为

$$
\operatorname{dist}(I_2,I_3)=\frac16,\qquad
\operatorname{dist}(I_3,I_4)=\frac5{12}.
$$

特别地，

$$
I_4=\left[\frac34,\frac54\right],\qquad
I_5=\left[\frac95,\frac{11}5\right],\qquad
\operatorname{dist}(I_4,I_5)=\frac{11}{20}>\frac12.
$$

固定 $k=2$。对任意非负候选阈值 $N$，直接取

$$
s=\max\{4,N\},
$$

并检查 $s$ 与 $s+1$。两个阶段均在候选尾部。对任意有理选值 $z_s\in I_s$ 和 $z_{s+1}\in I_{s+1}$，都有

$$
|z_s-z_{s+1}|\ge\operatorname{dist}(I_s,I_{s+1})
\ge\frac{11}{20}>\frac12.
$$

该证书覆盖每一条有理选值序列。定理 5.2 因式 (42) 的嵌套前提缺失而不适用。所有选值序列均不稳定，因此 RCS 完备化映射在本例中没有可作用的选值序列。

式 (42) 和式 (13) 的失败是预期数学结果。其余检查及全部证书通过时，报告输出 `EXP-08 acceptance: PASS`，程序退出码为 0。

## 宽度阈值与严格边界

对任意正整数精度 $k$，宽度证书取

$$
N_w(k)=2k+1.
$$

当 $n\ge N_w(k)$ 时，$w_n=2/n\le2/(2k+1)<1/k$。但在前一阶段 $n=2k$，$w_n=1/k$ 恰好取等，严格小于不成立。任意选值的不稳定由上一节的区间距离证书独立证明。

## 参数与运行

计算核心兼容 Python 3.10+，只使用标准库；绘图另需现有 `requirements-plot.txt` 中的 Matplotlib。以下命令从仓库根目录在 PowerShell 中执行。

默认计算：

```powershell
py .\exp08\exp08_shrinking_unstable.py
```

最小展示范围配合大阈值：

```powershell
py .\exp08\exp08_shrinking_unstable.py --max-index 2 --precision 2 --precision 10 --witness-index 1000000000000
```

| 参数 | 默认值 | 约束与用途 |
| --- | --- | --- |
| `--max-index` | 10 | 不小于 2 的整数；逐阶段 CSV 只展示 $2$ 至该索引；阶段 2–5 的参考关系始终核验 |
| `--precision K` | 2、10、100 | 可重复指定的正整数；用于宽度阈值及等号边界，不改变固定 $k=2$ 的稳定性反证 |
| `--witness-index N` | 0 | 非负整数；直接计算 $s=\max\{4,N\}$ 与 $s+1$，无需枚举至 $N$ |
| `--output-dir` | `results/exp08` | 报告及两份 CSV 的输出目录 |
| `--stdout-only` | 关闭 | 只打印报告，不写入产物 |

单独绘图：

```powershell
py .\exp08\plot_exp08.py --stage-csv .\results\exp08\shrinking_stages.csv --output-dir .\results\exp08\figures
```

只运行本实验及其批跑集成测试：

```powershell
py -m unittest tests.test_exp08 tests.test_run_all.TestExp08BatchIntegration -v
```

全仓库测试命令见[根目录 README](../README.md#验收)。绘图程序拒绝缺失、为空、含非既约分数或数学关系不一致的 CSV；无图形界面也可生成 PNG。

## 产物与证书对应

| `results/exp08/` 中的文件 | 内容 |
| --- | --- |
| `exp08_report.txt` | L1 有限精确数据、L2 有限关系核验、L3 全尾部量词与解析证书、L4 结论和范围 |
| `shrinking_stages.csv` | 中心、原始计数、误差界、相对误差、精确端点、宽度、式 (44) 中项与上界，以及相对前一阶段的包含、相交和距离 |
| `shrinking_certificates.csv` | 各精度的宽度阈值与等号边界、$n=2,3,4$ 的相邻距离、任意 $N$ 的 RCS-4 反证和定理 5.2 的 N/A 状态 |
| `figures/exp08_shrinking_unstable.png` | 上图显示中心交替和分离区间，下图显示 $w_n=2/n$ 缩宽及式 (44) 的相同上界 |

首行没有对应的相邻阶段，其 `nested_in_previous`、`intersects_previous`、`distance_to_previous` 均为空；后续行的 `nested_in_previous=False` 和 `intersects_previous=False` 是已核验的数学结论，不与空值混用。PNG 只展示有限样本，不能替代报告中的任意 $N$、任意有理选值证书。精确整数和既约分数仅在绘图坐标生成时转换为浮点数。
