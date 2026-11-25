# RCS v1.2 可复现计算演示仓库

本仓库承载 RCS Framework 论文 v1.2 的配套数值实验。全部计算使用 Python
整数与 `fractions.Fraction` 精确算术；浮点只出现在独立可选绘图脚本的展示
边界。数学依据为论文 *RCS_zenodo_v1.1*，式号、定义与定理编号以 v1.1 为准。

## 实验清单

|  编号   |             演示             | 脚本目录  |  状态  |
| ------ | ---------------------------- | -------- | ------ |
| EXP-01 | Pell 稳定线程与无理完备化值    | `exp01/` | 已完成 |
| EXP-02 | 振荡反例与 RCS-4 独立性       | `exp02/` | 待实现 |
| EXP-03 | 共尾细化不变性及非共尾对照     | `exp03/` | 待实现 |
| EXP-04 | 有限计数扰动鲁棒性            | `exp04/` | 待实现 |
| EXP-05 | 嵌套有理包络证书              | `exp05/` | 待实现 |
| EXP-06 | 准入谱非唯一性                | `exp06/` | 待实现 |
| EXP-07 | 去掉有界性后的反例            | `exp07/` | 待实现 |
| EXP-08 | 区间缩宽但任意选值不稳定       | `exp08/` | 待实现 |
| EXP-09 | 给定证书不嵌套但任意选值仍稳定 | `exp09/` | 待实现 |
| EXP-10 | 稳定历史的分类与渐近等价       | `exp10/` | 待实现 |

EXP-01 至 EXP-09 为发布承诺；EXP-10 验收通过后随 v1.2 发布。

## 目录结构

```text
.
├── README.md                  # 本文件（仓库总说明）
├── requirements-plot.txt      # 绘图可选依赖（matplotlib）
├── run_all.py                 # 批量入口：顺序运行各实验并汇总验收状态
├── tests/
│   ├── __init__.py
│   └── test_exp01.py
└── exp01/
    ├── exp01_pell_stability.py
    ├── plot_exp01.py
    └── README.md
```

每个实验脚本自包含其必要定义、递推与证书，可独立运行，不依赖其他实验的
输出文件。生成物（CSV、PNG、报告）写入 `results/`，不纳入版本控制。

## 运行环境

- Python 3.10 或更高；计算核心仅依赖标准库。
- 绘图需要 `matplotlib`（可选）：

```powershell
py -m pip install -r requirements-plot.txt
```

## 常用命令（Windows PowerShell，仓库根目录下）

### 运行 EXP-01 主计算

```powershell
py .\exp01\exp01_pell_stability.py --max-index 30 --precision 2 --precision 10 --precision 100 --output-dir .\results\exp01
```

### 独立绘图

```powershell
py .\exp01\plot_exp01.py --stage-csv .\results\exp01\pell_stages.csv --interval-csv .\results\exp01\pell_intervals.csv --output-dir .\results\exp01\figures
```

### 运行测试

```powershell
py -m unittest discover -s tests -v
```

### 批量运行全部已实现实验

```powershell
py .\run_all.py
```

## 数学口径与边界

- **精确算术**：计数为整数，读数与误差为 `Fraction`；CSV 中分数为既约文本，
  不写小数。
- **全尾部结论**来自解析阈值证书；有限前缀计算本身不作为极限定理的证明。
- **完成值符号化**：无理完成值以正根符号刻画及证书表示，不把浮点小数当作
  精确完成值。
- **反例验收**：预期失败的条件输出 `False` 与反例见证；其余核验通过时整体
  验收状态仍为 `PASS`。
- 各实验的结论边界、证书细节与定理—式号映射见对应实验目录下的 `README.md`。

## 归档待办

- [ ] 未参与实现的一方独立数学复核并对照 CSV；
- [ ] Windows 干净目录复跑，记录 Python 与 matplotlib 实测版本；
- [ ] 与论文 v1.2 式号、图号、术语最终一致性检查；
- [ ] 冻结 GitHub 提交与 Release，代码版本与论文版本互引；
- [ ] Zenodo 归档，补齐 DOI 与 GitHub Release 双向引用。
