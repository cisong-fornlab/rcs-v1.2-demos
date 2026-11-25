# EXP-01 · Pell 稳定线程与无理完备化值

RCS v1.2 可复现计算演示的第一个实验。对应论文 *RCS_zenodo_v1.1*：
**Proposition 7.1、Remark 7.1、Theorem 4.2、Theorem 5.2、Postulate 3.1**，
式 **(13)、(47)–(57)**。

本实验展示：由有限正整数发生计数递推生成的发生比协议满足定量稳定性
(RCS-4)，其渐近等价类确定一个正无理完备化值。全部数学计算只使用
Python 整数与 `fractions.Fraction`；浮点只出现在独立绘图脚本的展示边界。

## 1. 审核状态

按照 EXP-01 冻结规格及现有两轮运行审查，本目录脚本可以认定为
**脚本级功能审核通过**：必需的精确计算、有限核验、全尾部解析证书、
CSV 输出、独立绘图和可重复验收测试均已覆盖，未发现阻断采用的数学或
工程缺陷。

这一结论不等同于以下发布工作已经完成：

- 第二位 AI 或人工的独立数学推导与 CSV 对照复核；
- Windows 干净目录复跑；
- GitHub 提交冻结、Release 发布和 Zenodo 归档。

因此，当前准确状态是：**EXP-01 功能实现通过，发布配套与正式独立复核
尚待完成。**

## 2. 实验目的与数据来源

EXP-01 演示一个由有限发生计数形成的稳定线程，其完成值为正无理数 $x$，
满足

$$
x>0,\qquad x^2=2.
$$

脚本不读取外部实验数据，也不使用随机输入。全部数据由初值和整数递推在
程序内部生成：

$$
p_0=q_0=1,
$$

$$
p_{n+1}=p_n+2q_n,\qquad q_{n+1}=p_n+q_n,
$$

$$
x_n=\frac{p_n}{q_n}.
$$

前五项读数为

$$
1,\quad \frac32,\quad \frac75,\quad \frac{17}{12},\quad \frac{41}{29}.
$$

主脚本逐项核验 Pell 恒等式、相邻差、两步单调性、嵌套区间、区间宽度和
非零平方残差，并分别给出幂次上界证书与实际分母证书。

## 3. 文件结构与数据流

```text
exp01/
├── exp01_pell_stability.py   # 精确数学计算、核验、报告与 CSV
├── plot_exp01.py            # 独立读取 CSV 并绘图
└── README.md                 # 本文件
```

运行顺序为：

```text
Pell 整数递推
    ↓
exp01_pell_stability.py
    ↓
exp01_report.txt + 4 份精确 CSV
    ↓
plot_exp01.py 读取其中 1 或 2 份 CSV
    ↓
1 或 2 张 PNG 图
```

| 文件 | 职责 | 依赖 |
|---|---|---|
| `exp01_pell_stability.py` | 计算、核验、解析证书、报告与精确 CSV | 仅 Python 标准库 |
| `plot_exp01.py` | 读取 CSV 并生成读数序列图、区间宽度图 | 仅 `matplotlib`（可选） |

绘图脚本不会导入或重新运行 Pell 模型，也不会修改输入 CSV。主计算不依赖
绘图脚本，未安装 `matplotlib` 时仍可独立完成全部数学核验。

## 4. 环境、依赖与版本记录

### 要求

| 项目 | 主计算脚本 | 独立绘图脚本 | 测试 |
|---|---|---|---|
| Python | 3.10 或更高版本 | 3.10 或更高版本 | 3.10 或更高版本 |
| 标准库 | 必需 | 必需 | 必需 |
| `fractions.Fraction` | 用于精确有理计算 | 用于精确解析和校验 CSV | 用于断言精确值 |
| `matplotlib` | 不需要 | 仅绘图时需要 | 不需要 |

### 当前实测环境

| 字段 | 记录 |
|---|---|
| 实测日期 | 2026-11-25 |
| 操作系统 | Windows（PyCharm 终端，PowerShell 5.1） |
| Python | 3.15.2 |
| `matplotlib` | 3.11.2 |
| 测试 | 8 项 unittest 全部通过 |
| 主计算与绘图 | `EXP-01 acceptance: PASS`；两张 PNG 已生成 |

以上版本是本机复跑记录，不是对所有环境的兼容性承诺。正式归档前仍需在
另一台 Windows 干净目录复跑，并在版本字段表中回填记录。

## 5. Windows PowerShell 运行方法

先进入仓库根目录（本 README 所在 `exp01/` 的上一级）。

### 5.1 检查 Python

```powershell
py --version
```

### 5.2 运行主计算

```powershell
py .\exp01\exp01_pell_stability.py --max-index 30 --precision 2 --precision 10 --precision 100 --output-dir .\results\exp01
```

- `--max-index 30`：展示阶段 `n = 0 … 30`（含端点）。
- 每个 `--precision K`：核验严格精度 `1/K`，可重复指定；默认 `2, 10, 100`。
- `--output-dir`：报告与 CSV 输出目录；省略则只打印到终端。

主脚本只使用 Python 标准库。成功时，报告末尾包含：

```text
EXP-01 acceptance: PASS
```

并在 `.\results\exp01` 中写入报告和四份 CSV。

### 5.3 安装绘图依赖

仅需要绘图时执行：

```powershell
py -m pip install -r requirements-plot.txt
```

可记录实际绘图库版本：

```powershell
py -c "import matplotlib; print(matplotlib.__version__)"
```

### 5.4 从精确 CSV 独立绘图

```powershell
py .\exp01\plot_exp01.py --stage-csv .\results\exp01\pell_stages.csv --interval-csv .\results\exp01\pell_intervals.csv --output-dir .\results\exp01\figures
```

成功时生成：

```text
.\results\exp01\figures\exp01_readout_sequence.png
.\results\exp01\figures\exp01_enclosure_widths.png
```

- 省略 `--interval-csv` 时只生成 `exp01_readout_sequence.png`，不生成区间宽度图。
- 绘图脚本不重跑 Pell 模型；先按 `Fraction` 解析并校验 CSV，浮点转换只发生在绘图函数内部。
- 宽度图含解析上界 `2^{-(4j+1)}` 灰色虚线；实际宽度曲线在该界下方。

### 5.5 运行测试

```powershell
py -m unittest tests.test_exp01 -v
```

退出码 0 表示每个有限核验和证书界都成立；非零退出码表示某个预期关系失败。

## 6. 命令参数

### `exp01_pell_stability.py`

| 参数 | 含义 | 默认值与约束 |
|---|---|---|
| `--max-index N` | 展示并逐项核验 $n=0,\ldots,N$ | 默认 `30`；必须是非负整数 |
| `--precision K` | 为容差 $1/K$ 生成两类全尾部阈值证书 | 可重复；未提供时依次为 `2、10、100`；每个 `K` 必须是正整数 |
| `--output-dir PATH` | 保存 UTF-8 报告和四份精确 CSV | 可省略；省略时只在终端显示报告，不写文件 |

重复的 `--precision` 会按命令行出现顺序全部保留。阈值证书可以超过
`--max-index` 所展示的有限前缀，因为证书不依赖展示范围。

### `plot_exp01.py`

| 参数 | 含义 | 默认值与约束 |
|---|---|---|
| `--stage-csv PATH` | 主脚本生成的 `pell_stages.csv` | 必需 |
| `--interval-csv PATH` | 主脚本生成的 `pell_intervals.csv` | 可省略；省略后只画读数序列 |
| `--output-dir PATH` | PNG 输出目录 | 默认 `.\figures` |

## 7. 输出文件

主计算产生以下文件：

| 文件 | 内容 |
|---|---|
| `exp01_report.txt` | L1 有限精确数据、L2 有限数学核验、L3 全尾部解析证书、L4 结论与范围 |
| `pell_stages.csv` | $p_n,q_n,x_n$、Pell 残差、平方残差、相邻差及两步关系 |
| `pell_intervals.csv` | $I_j=[x_{2j},x_{2j+1}]$ 的端点、精确宽度、幂次宽度界及嵌套关系 |
| `pell_certificates.csv` | 通用幂次上界证书及其阈值 $N(k)=2j$ |
| `pell_denominator_certificates.csv` | 模型专属的实际分母乘积证书及其阈值 |

默认 `--max-index 30` 时，阶段表含 31 行数据，完整区间表含 15 行数据。
需要后继项才能计算的关系在显示末端留空；第一个区间没有前驱区间，其
`nested_in_previous` 字段也为空。这些空白不表示核验失败。

独立绘图产生：

| 文件 | 内容 |
|---|---|
| `exp01_readout_sequence.png` | 有理读数 $x_n$ 的序列；灰色虚线仅为绘图参考线 |
| `exp01_enclosure_widths.png` | 完整区间实际宽度的对数坐标图，叠加解析上界虚线 |

当前 PNG 文件名是实验内部名称，尚未绑定论文正文图号。Pell／振荡线程的
正文并列图需等待 EXP-02 数据，不属于 EXP-01 单独承担的内容。

## 8. 定理—式号—脚本—输出映射

| 论文条目 | 式号 | 脚本内核验 | 输出位置 |
|---|---|---|---|
| RCS-1 / Prop. 3.1 | (10) | `verify_substrate` | 报告 L2 |
| RCS-2 / Axiom 3.1 | — | `verify_substrate` | 报告 L2 |
| RCS-3a / Def. 3.1 | (11) | `verify_substrate` | 报告 L2 |
| RCS-3b / Axiom 3.2 | (12) | `verify_substrate` | 报告 L2 |
| Pell 递推 | (49)–(50) | `pell_stages`、`verify_stages` | `pell_stages.csv` |
| Pell 残差 | (52) | `verify_stages` | `pell_stages.csv` |
| 交叉行列式 | (53) | `verify_stages` | `pell_stages.csv` |
| 相邻读数差 | (54) | `verify_stages` | `pell_stages.csv` |
| 两步关系 / 奇偶单调 | (56) | `verify_stages` | `pell_stages.csv` |
| 嵌套区间 | (55) | `verify_intervals` | `pell_intervals.csv` |
| 平方残差 | (57) | `verify_stages` | `pell_stages.csv` |
| RCS-4 稳定性 | (13) | `stability_certificate`、`denominator_stability_certificate` | 两张证书 CSV |
| 包络稳定性 | Thm. 5.2 | 嵌套区间证书 | 报告 L3–L4 |
| 完备化映射 | Thm. 4.2 | 完成值符号标识 | 报告 L4 |

定性基底的程序核验最多抽样到内部深度 8；所有阶段的一般结论来自报告
L3 中的恒等式和后继论证，而不是把有限样本当作一般证明。

## 9. 两类稳定性证书不得混用

### 9.1 通用幂次上界证书

由 $q_n\ge 2^n$ 得

$$
\operatorname{diam}I_j
=\frac{1}{q_{2j}q_{2j+1}}
\le \frac{1}{2^{4j+1}}.
$$

对每个正整数 $k$，取最小的 $j\ge0$ 使

$$
2^{4j+1}>k,
$$

并令 $N(k)=2j$。则对所有 $m,n\ge N(k)$，

$$
|x_m-x_n|
\le \operatorname{diam}I_j
\le \frac{1}{2^{4j+1}}
<\frac1k.
$$

该证书由 `stability_certificate` 生成，写入 `pell_certificates.csv`。

### 9.2 实际分母乘积证书

针对 Pell 模型，还可以取最小的 $j\ge0$ 使

$$
q_{2j}q_{2j+1}>k,
$$

并令 $N(k)=2j$。此时实际宽度直接满足

$$
\operatorname{diam}I_j
=\frac{1}{q_{2j}q_{2j+1}}
<\frac1k.
$$

该模型专属证书由 `denominator_stability_certificate` 生成，写入
`pell_denominator_certificates.csv`。它使用实际分母，通常比幂次上界更紧，
但不能与通用幂次界混为同一个估计。

默认参数的核验值为：

| $k$ | 幂次证书 $N(k)$ | 幂次宽度界 | 分母证书 $N(k)$ | 分母乘积 | 实际宽度 |
|---:|---:|---:|---:|---:|---:|
| 2 | 2 | $1/32$ | 2 | 60 | $1/60$ |
| 10 | 2 | $1/32$ | 2 | 60 | $1/60$ |
| 100 | 4 | $1/512$ | 4 | 2030 | $1/2030$ |

两类阈值在这三个示例中相同，但这是具体计算结果，不应据此假定它们对
所有 $k$ 都相同。

## 10. 精确算术与浮点隔离

- **精确算术**：计数为整数，读数与误差为 `Fraction`；CSV 中分数为既约
  文本，不写小数。
- 主脚本的全部数学计算使用 Python 整数和 `fractions.Fraction`，不使用
  浮点数表示读数、残差、区间宽度、阈值或完成值。
- 所有核验通过自定义 `require` 执行；即使使用 `python -O`，核验也不会像
  `assert` 那样被移除。
- 绘图脚本先用 `Fraction` 解析并检查 CSV 中的计数、读数、端点和宽度。
- 只有在独立绘图边界，才把已校验的有理数转换为浮点显示值。
- 图中的 $\sqrt2$ 参考线由浮点绘图函数生成，不参与任何数学断言、阈值
  选择或完成值表示。
- 绘图不会回写 CSV；正式数学证据链不依赖 PNG 的视觉效果。

## 11. 可重复的最小复跑检查

### 自动验收测试

```powershell
py -m unittest tests.test_exp01 -v
```

测试只跑计算核心，使用固定小深度和精确算术规则；不涉及浮点核验路径。

### 小固定深度与优化模式（冒烟检查）

```powershell
py -O .\exp01\exp01_pell_stability.py --max-index 2 --precision 2 --output-dir .\results\exp01-smoke
```

应返回退出码 0，并在报告末尾显示 `EXP-01 acceptance: PASS`。该命令同时
检查小索引边界和 `-O` 模式下核验仍然有效。

### 独立绘图

对 `.\results\exp01-smoke\pell_stages.csv` 和 `pell_intervals.csv` 执行
第 5.4 节命令，并确认 PNG 文件实际生成。也可故意省略区间 CSV，检查只生成
读数序列图。

### 预期失败检查

- `--max-index -1` 应失败；
- `--precision 0` 应失败；
- 缺失或损坏的 CSV 应使绘图脚本返回非零退出码；
- 篡改 `p_n`、`q_n` 而不再满足 $x_n=p_n/q_n$ 时，绘图脚本应拒绝输入。

## 12. 结论边界

1. **有限核验不是全尾部证明。** CSV 和有限 `require` 检查展示具体模型并
   捕捉实现错误；RCS-4 的一般结论由 L3 的解析证书保证。
2. **完成值保持符号表示。** 数学结论为 $x>0$ 且 $x^2=2$；任何浮点小数
   都只是图形显示，不是完成值的精确表示。
3. **有限读数不等于完成值。** 每个有限读数都是有理数，且
   $x_n^2-2\ne0$。无理性由既约分数 $m^2=2d^2$ 导致 $m,d$ 同为偶数的
   矛盾论证给出。
4. **Pell 递推不是物理动力学。** 它只是命题 7.1 所需的数学存在性见证。
5. **数学完备化不等于物理准入。** 本实验不单独证明某个物理协议属于模型
   级准入谱 $W_{\mathrm{phys}}$；物理可采纳性仍需独立声明的协议类和
   测量解释。
6. **图形不是数值证据的替代品。** 验收依据是精确数据、恒等式核验和解析
   证书，而不是曲线看起来接近某个浮点参考值。

## 13. 归档前待办与版本字段

- [ ] 由未参与实现的一方独立推导式 (49)–(57) 和两类阈值，再与 CSV 对照；
- [x] 在本机 Windows（Python 3.15.2、matplotlib 3.11.2）按第 5 节命令复跑，测试、主计算、绘图均通过；
- [ ] 在另一台 Windows 干净目录复跑并回填版本记录；
- [ ] 与论文 v1.2 的式号、图号和术语做最终一致性检查；
- [ ] 冻结 GitHub 提交和 Release，并将代码版本与论文版本互相对应；
- [ ] 创建 Zenodo 归档，补齐 DOI 与 GitHub Release 的双向引用；
- [ ] EXP-02 完成后再制作 Pell／振荡并列图，不由本实验提前承担。

归档信息在事实发生后填写，不预造编号：

| 字段 | 当前值 |
|---|---|
| GitHub 仓库 | 待填写 |
| Git 提交号 | 待填写 |
| Release 标签 | 待填写 |
| 对应论文版本 | RCS v1.2 数值配套候选 |
| 独立复核者与日期 | 待填写 |
| Windows 复跑版本记录 | 本机 2026-11-25：Python 3.15.2，matplotlib 3.11.2；第二台干净目录待复跑 |
| Zenodo DOI | 待填写 |
#（注：内容由AI生成）
