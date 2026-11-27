# EXP-05 · 嵌套有理包络证书

本实验依据 RCS v1.1 的定义 5.1、引理 5.1、定理 5.2 和式 (40)–(44)。取 $n\ge2$、$a_n=n+1$、$b_n=n$、$\alpha_n=\beta_n=1$ 和 $M=2$，从计数构造

$$I_n=\left[1-\frac1{n+1},\,1+\frac3{n-1}\right].$$

左端点递增，右端点递减，宽度 $w_n\le12/n$，且每个区间都含 $1$。对任意正整数 $k$，在 $N(k)=12k+1$ 及其后的阶段，任意有理选值都落在 $I_{N(k)}$ 中，任意两点的距离不超过 $w_{N(k)}<1/k$。因此任意选值线程都满足 RCS-4，两两等价并共同实现 $1$。共尾限制 $n=2j$ 保持此值，其充分阈值是 $j\ge\max(1,\lceil N(k)/2\rceil)$。

## 运行

从仓库根目录打开 PowerShell。依赖说明见[仓库说明](../README.md#运行)。

```powershell
py .\exp05\exp05_nested_enclosures.py
py .\exp05\plot_exp05.py
py -m unittest discover -s tests -p test_exp05.py -v
```

计算只需 Python 标准库。默认展示 $n=2$ 到 $10$，精度参数为 $2,10,100$。用 `--max-index` 修改末阶段，用可重复的 `--precision` 指定精度，用 `--output-dir` 指定输出目录，或用 `--stdout-only` 仅打印报告。绘图需要 Matplotlib，可用 `--stage-csv` 和 `--output-dir` 指定路径。

## 输出与验收

| `results/exp05/` 中的文件 | 内容 |
| --- | --- |
| `exp05_report.txt` | L1–L4 精确数据、有限核验、全尾部解析证书及结论 |
| `enclosure_stages.csv` | 计数、端点、宽度、式 (44) 上界、嵌套状态和四种示例选值 |
| `enclosure_certificates.csv` | 相对误差、稳定性、等价性、共同值、共尾限制及等号对照 |
| `figures/exp05_nested_enclosures.png` | 有限阶段的包络、示例选值、宽度及式 (44) 上界 |

报告末尾应显示 `EXP-05 acceptance: PASS`。下表按证书的 `kind` 说明三个阈值字段。稳定性与实现值证书的 `subject=any_selection` 表示任意选值。测试在 $N(k)$ 和 $N(k)+1$ 逐条核对四种示例的有限实例，任意选值的结论由报告中的全尾部证书给出。

| `kind` | `threshold_N`（原阶段充分阈值） | `threshold_j` | `original_stage_2j` |
| --- | --- | --- | --- |
| `relative_error_43` | $\max(2,k+1)$ | 空 | 空 |
| `stability`、`equivalence`、`realization` | $12k+1$ | 空 | 空 |
| `cofinal_restriction` | $12k+1$ | $6k+1$ | $12k+2$ |
| `threshold_boundary` | 空 | 空 | 空 |

`threshold_boundary` 的候选阶段 $12k$ 记在 `threshold`，用于等号对照。`threshold_N` 留空，因为该候选阶段无法通过简化上界证明所需的严格不等式。在此阶段，简化上界 $12/N$ 恰等于 $1/k$，所以 `strict_less_than=False`、`status=BOUNDARY`。实际区间宽度仍小于 $1/k$。这一行解释了充分阈值 $12k+1$ 中的 $+1$。证书可直接计算超出展示范围的阈值。

## CSV 兼容范围

首个整合压缩包 `EXP05_integration.zip` 的阶段表已使用 `q_n`、`L_n`、`U_n`、`w_n`、`bound_44` 等字段。v2 在证书表末尾追加了上表三列。v3 和 v4 沿用 v2 的两张 CSV 表。读取共尾行时优先用上表三列。原有 `threshold` 和 `witness_index` 在共尾行仍分别表示 $j$ 和 $2j$。

某些独立候选稿的阶段表使用 `original_readout`、`lower_from_counts` 或 `width_n` 等不同字段。使用整合版核心和绘图脚本配套生成、读取 CSV。依赖候选稿字段的调用方需更新映射。绘图脚本校验生成图形所需的阶段字段并在渲染时转换为浮点数。计算脚本负责计数、相对误差和证书条件的完整验证。
