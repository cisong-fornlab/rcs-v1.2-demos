# RCS v1.2 可复现计算演示仓库

本仓库提供 RCS Framework 论文 v1.2 的配套实验。式号和定理编号以 RCS v1.1 为准。计算使用整数与 `fractions.Fraction`，浮点转换仅用于绘图。

## 运行

需要 Python 3.10 或更高版本。从仓库根目录打开 PowerShell，首次绘图前安装依赖，然后批量运行。

```powershell
py -m pip install -r requirements-plot.txt
py .\run_all.py
```

批量入口按顺序完成 EXP-01 至 EXP-07 的计算和绘图。完整 EXP01–07 基线从空结果目录运行时，预期生成 **7 份报告、21 份 CSV 和 9 张 PNG**。各实验的输出在 `results/exp01/` 至 `results/exp07/`，图在各自的 `figures/` 中。Pell 与振荡线程的并列图位于 `results/exp02/figures/exp01_exp02_readouts.png`，EXP-06 的谱对照图位于 `results/exp06/figures/exp06_spectrum_nonuniqueness.png`，EXP-07 的相对扰动／绝对读数差对照图位于 `results/exp07/figures/exp07_unbounded_ratio.png`。`results/` 是本地生成目录，已由 Git 忽略。

只生成报告和 CSV 时可用 `py .\run_all.py --no-plots`，此时所需依赖均来自 Python 标准库；完整基线预期为 **7 份报告、21 份 CSV、0 张 PNG**。Linux 或 macOS 可使用 `python3 run_all.py`。

## 实验清单

| 编号 | 演示 | 状态 |
| --- | --- | --- |
| EXP-01 | [Pell 稳定线程与无理完备化值](exp01/README.md) | 已实现 |
| EXP-02 | [振荡反例与 RCS-4 独立性](exp02/README.md) | 已实现 |
| EXP-03 | [共尾细化不变性及非共尾对照](exp03/README.md) | 已实现 |
| EXP-04 | [有限计数扰动鲁棒性](exp04/README.md) | 已实现 |
| EXP-05 | [嵌套有理包络证书](exp05/README.md) | 已实现 |
| EXP-06 | [准入谱非唯一性](exp06/README.md) | 已实现 |
| EXP-07 | [去掉比值有界性后的反例](exp07/README.md) | 已实现 |
| EXP-08 | 区间缩宽但任意选值不稳定 | 待实现 |
| EXP-09 | 给定证书不嵌套但任意选值仍稳定 | 待实现 |
| EXP-10 | 稳定历史的分类与渐近等价 | 待实现 |

EXP-01 至 EXP-09 为发布承诺。EXP-10 验收通过后随 v1.2 发布。

EXP-07 保留式 (32)–(34) 的小相对扰动条件，但式 (31) 的统一比值有界性失败，式 (35) 的绝对读数差趋零结论随之失败。两条读数序列均不满足 RCS-4，因此式 (36) 的同值结论不适用，式 (38) 所需的固定 $M$ 估计标为 N/A。EXP-04 的 B 组中，式 (34) 失效，两条 Pell 线程仍稳定，分别实现 $\sqrt{2}$ 和 $\sqrt{2}/2$。

## 验收

完整基线合并后，有图和无图批跑都应显示 `passed: 7`、`skipped: 0`、`failed: 0`。只有一个已注册实验的测试目录应显示 `passed: 1`、`skipped: 6`、`failed: 0`。单元测试用 `py -m unittest discover -s tests -v` 执行。

部分仓库中，缺少实验脚本的相关批跑集成测试会报告 `skipped` 并列出缺失路径。完整仓库验收要求安装绘图依赖、两种批跑均为 7 项通过且无跳过，并确认全仓库测试无跳过。

共用入口的集成测试集中在 `tests/test_run_all.py`，包括只安装部分实验、禁用绘图依赖和计算失败后的绘图行为。EXP-06 与 EXP-07 均覆盖旧 CSV 和 PNG 保留时，本轮计算失败不得触发绘图。EXP-07 的新增产物为 1 份报告、2 份 CSV、1 张 PNG；计算报告的 L3 给出全尾部解析证书，PNG 只用于展示有限前缀或谱成员。

EXP-06 整合版基于 `EXPERIMENTS_01-05(1).zip`。使用增量包时，将其中的 `exp06/`、`tests/`、`run_all.py` 和 `README.md` 合并到仓库根目录。保留 `tests/` 中已有的其他实验测试。EXP-07 增量包对应合并 `exp07/`、`tests/test_exp07.py`、更新后的 `tests/test_run_all.py`、`run_all.py` 和根目录 `README.md`；`requirements-plot.txt` 沿用现有版本。

批跑失败时，以本次退出码和汇总为准。启用绘图时，若本次 EXP01 计算失败而 EXP02 计算成功，批跑仍会生成 EXP02 的独立读数图，并跳过 EXP01／02 比较图。结果目录中可能仍有上一次的同名图。验收产物数量时，应从空的 `results/` 目录运行。

## 历史实测记录：EXP-06 整合版

以下记录保留自 EXP-06 整合版，不是本次 EXP-07 的七项实测结果。

EXP-06 整合版在 Linux、Python 3.12.14 和 Matplotlib 3.10.8 下实测。有图和无图批跑各自从空结果目录开始。

| 命令 | 实测结果 |
| --- | --- |
| `python3 run_all.py` | 6 项通过、0 跳过、0 失败，生成 6 份报告、19 份 CSV、8 张 PNG |
| `python3 -S run_all.py --no-plots` | 6 项通过、0 跳过、0 失败，生成 6 份报告、19 份 CSV |
| `python3 -m unittest discover -s tests -v` | 148 项测试通过 |

## 历史实测记录：EXP-07 增量

2026-11-28 在 Linux x86_64、Python 3.12.12、Matplotlib 3.10.3 下实测。命令在仅加入 EXP-07 计算、绘图和测试的隔离目录执行；除 EXP-07 外的六个注册项因脚本不在该隔离目录而按设计跳过。

| 实际运行的命令 | 实测结果 |
| --- | --- |
| `python3 -S run_all.py --no-plots` | 退出码 0；`passed: 1 / skipped: 6 / failed: 0`；1 份报告、2 份 CSV、0 张 PNG |
| `python3 run_all.py` | 退出码 0；`passed: 1 / skipped: 6 / failed: 0`；1 份报告、2 份 CSV、1 张 PNG |
| `python3 -m unittest tests.test_exp07 -v` | 21 项测试通过，覆盖精确样例、严格边界、大索引见证、CLI、CSV 和 PNG |
| `python3 -m unittest tests.test_run_all.TestBatchEntry.test_run_all_registers_exp07_and_preserves_earlier_entries tests.test_run_all.TestExp07BatchIntegration -v` | 3 项测试通过，覆盖注册顺序与参数、标准库无图批跑、正常绘图、旧产物存在时本轮计算失败跳过绘图 |

另已直接实测 `python3 exp07/exp07_unbounded_ratio.py --max-index 2 --precision 2 --precision 10 --witness-index 100 --output-dir <临时目录>` 及对应 `plot_exp07.py` 命令：计算输出 `EXP-07 acceptance: PASS`，只展示 $n=2$，证书直接使用大索引，PNG 成功生成。

## 完整实测记录（EXP-01 至 EXP-07）

2026-11-28，在隔离的 Linux 工作区中，将本版 EXP-07 的七份文件合入 `EXPERIMENTS_01-06-final.zip` 解包后的 `EXPERIMENTS/` 根目录。基线 ZIP 的 SHA-256 为 `d8b6f6a18d4c537cd8a444c0f85bc4e2029de3ccde195a3be360cda8a3479767`。以下命令均从合并后的根目录执行，环境为 Python 3.12.14、Matplotlib 3.10.8。有图和无图批跑各自从空结果目录开始。

| 命令 | 实测结果 |
| --- | --- |
| `python3 run_all.py` | 7 项通过、0 跳过、0 失败，生成 7 份报告、21 份 CSV、9 张 PNG |
| `python3 -S run_all.py --no-plots` | 7 项通过、0 跳过、0 失败，生成 7 份报告、21 份 CSV、0 张 PNG |
| `python3 -m unittest discover -s tests -v` | 171 项测试，0 跳过，0 失败。日志摘要含 `Ran 171 tests` 和 `OK` |

另用 `--max-index 2 --witness-index 1000000000000 --precision 2 --precision 10` 复核 EXP-07。逐阶段 CSV 仅记录 $n=2$，两条 RCS-4 证书均记录见证索引 $10^{12}$ 和 $2\times10^{12}$。式 (31) 的 $M=N+1$ 样例同时记录命令行阈值 $N=10^{12}$。

## 归档待办

- [ ] 独立数学复核并对照 CSV。
- [ ] 在 Windows 干净目录复跑，记录 Python 与 Matplotlib 版本。
- [ ] 核对论文 v1.2 的式号、图号和术语。
- [ ] 固定 GitHub 提交和 Release，补齐 Zenodo DOI 与双向引用。
