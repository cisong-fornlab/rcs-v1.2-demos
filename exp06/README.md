# EXP-06：准入谱非唯一性

本实验对应 RCS v1.1 的定义 3.3、定义 6.1、定理 6.1、推论 7.1、备注 6.1，核心式为 (15)、(45)。Pell 递推与区间证书独立取自命题 7.1 及式 (47)–(57)，不导入其他实验，也不读取其他实验的输出。

## 数学内容与验收

三个协议共享式 (47)–(48) 的定性细化基底：

- `Pu`：每阶段计数 `(1,1)`，读数恒为 `1`；
- `Pv`：每阶段计数 `(2,1)`，读数恒为 `2`；
- `Px`：由式 (49) 生成 `(p_n,q_n)`，读数为精确分数 `p_n/q_n`。

预先按协议身份声明 `C1={Pu}`、`C2={Pu,Pv}`、`C3={Pu,Px}`。程序先按式 (15) 同时检查协议成员资格和 RCS-4，再按式 (14) 划分准入线程的等价类，最后按式 (45) 取得实现谱。正确结果为 `{1}`、`{1,2}`、`{1,x}`，其中 `x>0` 且 `x²=2`；程序还核验 `C1≠C2` 和 `C1≠C3`。

常值线程的阈值均为 `N(k)=0`。Pell 线程选择满足 `2^(4j+1)>k` 的最小非负整数 `j`，取 `N(k)=2j`。在 `k=2` 时，`j=0` 只给出与 `1/k` 相等的宽度上界，不能通过严格不等号，必须继续到 `j=1`，故 `N(2)=2`。

不等价证书分别为：`Pu/Pv` 固定 `k=2`；`Pu/Px` 使用 `I1=[7/5,17/12]`、固定 `k=3`，并对任意候选阈值 `N` 取 `n=max(N,2)`。即使 `--max-index 0`，程序也会额外生成 Pell 索引 `1,2,3`，在 CSV 中以 `in_display=False` 标明，并在报告中说明。

所有数学计算使用整数和 `fractions.Fraction`。结论仅限于抽象发生计数通道的模型级实现谱，不替代具体物理系统的准入规则。

## 从仓库根目录运行（PowerShell）

单独计算，使用默认的 `--max-index 30`、精度 `2,10,100` 和输出目录 `results/exp06/`：

```powershell
py .\exp06\exp06_spectrum_nonuniqueness.py
```

指定展示深度、两个精度和输出目录：

```powershell
py .\exp06\exp06_spectrum_nonuniqueness.py --max-index 0 --precision 2 --precision 10 --output-dir .\results\exp06
```

单独绘图（需要先完成本轮计算并安装绘图依赖）：

```powershell
py -m pip install -r .\requirements-plot.txt
py .\exp06\plot_exp06.py --spectrum-csv .\results\exp06\spectrum_members.csv --output-dir .\results\exp06\figures
```

完整批跑（EXP-01 至 EXP-06，计算成功后调用对应绘图）：

```powershell
py .\run_all.py
```

无图批跑，仅需 Python 标准库：

```powershell
py -S .\run_all.py --no-plots
```

运行全部测试：

```powershell
py -m unittest discover -s tests -v
```

仅运行 EXP-06 单元测试或批跑集成测试：

```powershell
py -m unittest discover -s tests -p "test_exp06.py" -v
py -m unittest discover -s tests -p "test_run_all.py" -v
```

Linux 或 macOS 可将 `py` 换成 `python3`，路径分隔符换成 `/`。

## 产物

计算脚本生成 UTF-8 报告及 5 份精确 CSV：

- `results/exp06/exp06_report.txt`：L1 有限精确数据、L2 有限关系核验、L3 全尾部解析证书、L4 结论与范围；
- `results/exp06/protocol_stages.csv`：三个协议的整数计数、精确读数及 Pell 残差；
- `results/exp06/pell_intervals.csv`：成对区间、精确宽度、宽度上界和嵌套状态；
- `results/exp06/stability_certificates.csv`：各协议在指定精度下的阈值与严格不等式证书；
- `results/exp06/inequivalence_certificates.csv`：两对线程的固定精度、任意候选阈值适用的见证规则、具体见证及精确下界；
- `results/exp06/spectrum_members.csv`：准入类、线程等价类、谱成员及其有理数或符号身份。

绘图脚本只从 `spectrum_members.csv` 读取成员归属，生成：

- `results/exp06/figures/exp06_spectrum_nonuniqueness.png`。

有理数在 CSV 中保持既约整数或分数；无理成员以 `√2` 和 `x > 0 and x^2 = 2` 表示。浮点转换只发生在绘图定位阶段。CSV 缺失、字段错误、成员归属错误或验收失败均返回非零退出码。
