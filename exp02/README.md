# EXP-02 · 振荡反例与 RCS-4 独立性

EXP-02 复现 RCS v1.1 命题 7.2，验收依据是《RCS v1.2 实验规范》第 2、4、13 节。它在满足 RCS-1、RCS-2、RCS-3a 和 RCS-3b 的定性基底上构造正整数计数，使读数 $q_n$ 在 1 和 2 之间交替。式 (13) 在固定精度参数 $k=2$ 处失败，报告同时给出 `RCS-4: False` 与 `EXP-02 acceptance: PASS`。

## 文件与环境

| 文件 | 用途 |
| --- | --- |
| `exp02/exp02_oscillatory_countermodel.py` | 构造计数、核验定性结构与读数，输出 L1–L4 报告及两份精确 CSV |
| `exp02/plot_exp02.py` | 默认绘制 EXP-02 单图，可根据 EXP-01 的阶段 CSV 另绘正文并列图 |
| `tests/test_exp02.py` | 检查数学关系、命令行、输出文件和绘图 CSV 解析 |
| `run_all.py`（仓库根目录） | 批量入口，已注册 EXP-01 与 EXP-02，无需再打补丁 |

主脚本和核心测试使用 Python 3.10+ 标准库。绘图使用 `matplotlib`，实际渲染和检查刻度的测试在未安装该依赖时跳过。计算、见证、CSV 及绘图输入校验使用整数与 `Fraction`，传给绘图接口的读数才转换为浮点数。

## Windows PowerShell 运行

将压缩包解压到实验目录根部，保留 `exp02` 与 `tests` 目录结构。运行 EXP-02 的计算、测试和单图只需本包中的文件。

```powershell
py .\exp02\exp02_oscillatory_countermodel.py
py -m unittest discover -s tests -p test_exp02.py -v
```

| 主脚本参数 | 默认值 | 含义 |
| --- | --- | --- |
| `--max-index M` | `10` | 展示阶段 `0..M`，包含两端 |
| `--witness-index N` | `0` | 为候选阈值 `N` 构造阶段 `N` 和 `N+1` |
| `--output-dir PATH` | `results\exp02` | 保存 UTF-8 报告和两份精确 CSV |
| `--stdout-only` | 关闭 | 只打印报告，可在结果目录不可写时使用 |

默认路径以 `exp02` 的上一级目录为基准，因此从其他工作目录调用脚本时，默认结果仍写入同一个实验目录。显式传入的相对路径以调用时的工作目录为基准。重复执行会覆盖同名文件。`--stdout-only` 与显式 `--output-dir` 互斥。

```powershell
py .\exp02\exp02_oscillatory_countermodel.py --stdout-only
```

以下命令隔离单阶段示例的输出，保留默认目录中的 11 个展示阶段。

```powershell
py .\exp02\exp02_oscillatory_countermodel.py --max-index 0 --witness-index 1000000000001 --output-dir .\results\exp02-single
```

## 可选绘图

```powershell
py -m pip install matplotlib
py .\exp02\plot_exp02.py
```

若使用自定义目录生成 CSV，可以指定绘图输入和图片目录。

```powershell
py .\exp02\plot_exp02.py --stage-csv .\results\exp02-single\oscillatory_stages.csv --output-dir .\results\exp02-single\figures
```

## 批量运行与正文并列图

将本包叠加解压到原始 `EXP01.zip` 的解压目录，使用本包根目录中的完整 `run_all.py`。批量脚本依次运行两项实验，生成并列图所需的精确 CSV。

```powershell
py .\run_all.py
py -m unittest discover -s tests -v
py .\exp02\plot_exp02.py --exp01-csv .\results\exp01\pell_stages.csv
```

传入 `--exp01-csv` 后，同一命令生成 EXP-02 单图与 Pell／振荡并列图。脚本先校验两份 CSV，再开始绘图。请使用两个主脚本直接导出的阶段 CSV，阶段索引须从 0 开始连续排列。绘图输入的读数与相邻差采用整数字符串或既约分数，例如 `1`、`3/2`。脚本核对 EXP-01 的初值和式 (49) 递推，以及两项实验的精确读数。

并列图共用纵轴尺度，各横轴对应输入 CSV 的阶段范围。单阶段面板只显示阶段刻度 `0`。标有 `(plot only)` 的 √2 虚线仅用于阅读图形。实验验收以精确 CSV 与解析证书为依据。

## 输出

| 默认路径 | 内容 |
| --- | --- |
| `results\exp02\exp02_report.txt` | L1–L4 报告，同时打印到终端 |
| `results\exp02\oscillatory_stages.csv` | 列为 `n,a_n,b_n,q_n,adjacent_difference`。最后一行的相邻差留空 |
| `results\exp02\oscillatory_witness.csv` | 一行见证，列为 `N,m,n,q_m,q_n,abs_difference,k,one_over_k,strict_less_than` |
| `results\exp02\figures\exp02_readout_sequence.png` | EXP-02 单图 |
| `results\exp02\figures\exp01_exp02_readouts.png` | 提供 `--exp01-csv` 时额外生成的正文并列图 |

见证取 `m=N`、`n=N+1`，CSV 记下该顺序的读数。阈值为偶数时读数是 `1,2`，奇数时是 `2,1`。两种情况下差都是 `1`，容差为 `1/2`，严格比较结果为 `False`。单图只需 `oscillatory_stages.csv`，支持单行 CSV。可用绘图脚本的 `--output-dir` 指定两张图的目标目录。

主脚本退出码 `0` 表示核验与输出完成，`2` 表示命令行参数无效，`1` 表示核验或输出出现意外错误。绘图退出码 `0` 表示生成成功，`1` 表示数据、文件或绘制过程出错，`2` 用于无效参数或缺少绘图依赖。若在生成并列图时遇到写入错误，已经生成的单图可能保留。

## 论文对应关系

| 论文依据 | 核验及报告位置 |
| --- | --- |
| 式 (7)、(58) | L1 给出 $b_n=1$、$a_n=1$ 或 $2$ 的计数及精确读数。L2 检查正性、交替性及相邻差 |
| 命题 3.1、式 (10) | RCS-1 的像及基数，逐项检查 $R_n(j)=j$，其中 $j\in Y_n$ |
| 公理 3.1 | RCS-2 对任意阶段都有严格后继 $n+1>n$ |
| 定义 3.1、式 (11) | RCS-3a 的恒等与复合 |
| 公理 3.2、式 (12) | RCS-3b 的定性读取相容性 |
| 式 (47)–(48) | L2 核验 `0..min(max_index,8)` 范围内的定性实例，L4 的定性状态取自这些检查。L3 给出各关系对任意阶段成立的依据 |
| 公设 3.1、式 (13) | L3 固定 $k=2$ 并对任意 $N\ge 0$ 取 $m=N,n=N+1$。相邻阶段奇偶相反，所以 $\lvert q_m-q_n\rvert=1>1/2$ |
| 定义 3.2、定理 4.2、命题 7.2 | L4 记录各条件状态。本读数历史位于 `Real_RCS` 的稳定线程定义域之外。它与 EXP-01 共享定性基底，证明定性条件 RCS-1–3 无法推出 RCS-4 |

## 本版实测

### Linux 完整仓库复跑

Linux，Python 3.12.14，Matplotlib 3.10.8。EXP-02 独立测试 **24 项通过**，与原始 EXP-01 合并后 **32 项通过**。批量运行汇总为 `passed: 2`、`skipped: 0`、`failed: 0`。

测试覆盖默认落盘、`--stdout-only`、空定性核验在 `python -O` 下被拒、浮点参数被拒、非既约 CSV 输入和两张 PNG 的实际生成。新增测试在实际渲染时检查单图和并列图的单阶段面板，验证横轴只有刻度 `0`。另在隔离目录用原始 EXP-01 与 EXP-02 的 CSV 复跑了并列绘图。

### 送审报告与 Windows 验证

数学复验所用的 `exp02_report.txt` 中，解释器版本行记为 `Python 3.15.2`。该版本行记录的是生成这份报告所用的解释器。上述测试统计来自独立的 Linux 完整仓库复跑。上文提供了 PowerShell 命令，Windows 完整联合测试尚无已核实记录。
