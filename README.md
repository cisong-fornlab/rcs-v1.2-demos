# RCS v1.2 可复现计算演示仓库

本仓库提供 RCS Framework 论文 v1.2 的配套实验。式号和定理编号以 RCS v1.1 为准。计算使用整数与 `fractions.Fraction`，浮点转换仅用于绘图。

## 运行

需要 Python 3.10 或更高版本。从仓库根目录打开 PowerShell，首次绘图前安装依赖，然后批量运行。

```powershell
py -m pip install -r requirements-plot.txt
py .\run_all.py
```

批量入口按顺序完成计算和绘图，生成 3 份报告、9 份 CSV 和 5 张 PNG。各实验的输出在 `results/exp01/`、`results/exp02/`、`results/exp03/`，图在各自的 `figures/` 中。Pell 与振荡线程的并列图位于 `results/exp02/figures/exp01_exp02_readouts.png`。`results/` 是本地生成目录，已由 Git 忽略。

只生成报告和 CSV 时可用 `py .\run_all.py --no-plots`，此时所需依赖均来自 Python 标准库。Linux 或 macOS 可使用 `python3 run_all.py`。

## 实验清单

| 编号 | 演示 | 状态 |
| --- | --- | --- |
| EXP-01 | [Pell 稳定线程与无理完备化值](exp01/README.md) | 已实现 |
| EXP-02 | [振荡反例与 RCS-4 独立性](exp02/README.md) | 已实现 |
| EXP-03 | [共尾细化不变性及非共尾对照](exp03/README.md) | 已实现 |
| EXP-04 | 有限计数扰动鲁棒性 | 待实现 |
| EXP-05 | 嵌套有理包络证书 | 待实现 |
| EXP-06 | 准入谱非唯一性 | 待实现 |
| EXP-07 | 去掉有界性后的反例 | 待实现 |
| EXP-08 | 区间缩宽但任意选值不稳定 | 待实现 |
| EXP-09 | 给定证书不嵌套但任意选值仍稳定 | 待实现 |
| EXP-10 | 稳定历史的分类与渐近等价 | 待实现 |

EXP-01 至 EXP-09 为发布承诺。EXP-10 验收通过后随 v1.2 发布。

## 验收

完整批跑应显示 `passed: 3`、`skipped: 0`、`failed: 0`。单元测试用 `py -m unittest discover -s tests -v` 执行。计算报告的 L3 给出全尾部解析证书，PNG 用于展示有限前缀。已在 Linux、Python 3.12.14、Matplotlib 3.10.8 下从空结果目录验证批跑。

## 归档待办

- [ ] 独立数学复核并对照 CSV。
- [ ] 在 Windows 干净目录复跑，记录 Python 与 Matplotlib 版本。
- [ ] 核对论文 v1.2 的式号、图号和术语。
- [ ] 固定 GitHub 提交和 Release，补齐 Zenodo DOI 与双向引用。
