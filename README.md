# RCS v1.2 可复现计算演示仓库

本仓库提供 RCS Framework 论文 v1.2 的配套实验。式号和定理编号以 RCS v1.1 为准。计算使用整数与 `fractions.Fraction`，浮点转换仅用于绘图。

## 运行

需要 Python 3.10 或更高版本。从仓库根目录打开 PowerShell，首次绘图前安装依赖，然后批量运行。

```powershell
py -m pip install -r requirements-plot.txt
py .\run_all.py
```

批量入口按顺序完成 EXP-01 至 EXP-06 的计算和绘图，生成 6 份报告、19 份 CSV 和 8 张 PNG。各实验的输出在 `results/exp01/` 至 `results/exp06/`，图在各自的 `figures/` 中。Pell 与振荡线程的并列图位于 `results/exp02/figures/exp01_exp02_readouts.png`，EXP-06 的谱对照图位于 `results/exp06/figures/exp06_spectrum_nonuniqueness.png`。`results/` 是本地生成目录，已由 Git 忽略。

只生成报告和 CSV 时可用 `py .\run_all.py --no-plots`，此时所需依赖均来自 Python 标准库。Linux 或 macOS 可使用 `python3 run_all.py`。

## 实验清单

| 编号 | 演示 | 状态 |
| --- | --- | --- |
| EXP-01 | [Pell 稳定线程与无理完备化值](exp01/README.md) | 已实现 |
| EXP-02 | [振荡反例与 RCS-4 独立性](exp02/README.md) | 已实现 |
| EXP-03 | [共尾细化不变性及非共尾对照](exp03/README.md) | 已实现 |
| EXP-04 | [有限计数扰动鲁棒性](exp04/README.md) | 已实现 |
| EXP-05 | [嵌套有理包络证书](exp05/README.md) | 已实现 |
| EXP-06 | [准入谱非唯一性](exp06/README.md) | 已实现 |
| EXP-07 | 去掉有界性后的反例 | 待实现 |
| EXP-08 | 区间缩宽但任意选值不稳定 | 待实现 |
| EXP-09 | 给定证书不嵌套但任意选值仍稳定 | 待实现 |
| EXP-10 | 稳定历史的分类与渐近等价 | 待实现 |

EXP-01 至 EXP-09 为发布承诺。EXP-10 验收通过后随 v1.2 发布。

## 验收

完整批跑应显示 `passed: 6`、`skipped: 0`、`failed: 0`。单元测试用 `py -m unittest discover -s tests -v` 执行。共用入口的集成测试集中在 `tests/test_run_all.py`，包括只安装部分实验、禁用绘图依赖和计算失败后的绘图行为；EXP-06 还覆盖仅有该实验时的 `passed: 1`、`skipped: 5`、`failed: 0` 汇总，以及旧 CSV 和 PNG 保留时本轮计算失败不得触发绘图。计算报告的 L3 给出全尾部解析证书，PNG 用于展示有限前缀或谱成员。

EXP-06 整合版基于 `EXPERIMENTS_01-05(1).zip`。使用增量包时，将其中的 `exp06/`、`tests/`、`run_all.py` 和 `README.md` 合并到仓库根目录。保留 `tests/` 中已有的其他实验测试。

EXP-06 整合版在 Linux、Python 3.12.14 和 Matplotlib 3.10.8 下实测。有图和无图批跑各自从空结果目录开始。

| 命令 | 实测结果 |
| --- | --- |
| `python3 run_all.py` | 6 项通过、0 跳过、0 失败，生成 6 份报告、19 份 CSV、8 张 PNG |
| `python3 -S run_all.py --no-plots` | 6 项通过、0 跳过、0 失败，生成 6 份报告、19 份 CSV |
| `python3 -m unittest discover -s tests -v` | 148 项测试通过 |

批跑失败时，以本次退出码和汇总为准。启用绘图时，若本次 EXP01 计算失败而 EXP02 计算成功，批跑仍会生成 EXP02 的独立读数图，并跳过 EXP01／02 比较图。结果目录中可能仍有上一次的同名比较图。验收产物数量时，可从空的 `results/` 目录运行。

## 归档待办

- [ ] 独立数学复核并对照 CSV。
- [ ] 在 Windows 干净目录复跑，记录 Python 与 Matplotlib 版本。
- [ ] 核对论文 v1.2 的式号、图号和术语。
- [ ] 固定 GitHub 提交和 Release，补齐 Zenodo DOI 与双向引用。
