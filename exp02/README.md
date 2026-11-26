# EXP-02 · 振荡反例与 RCS-4 独立性

这个线程与 EXP-01 共享定性基底，读数在 1 与 2 之间交替。相邻读数之差恒为 1，因此 RCS-1–3 成立而 RCS-4 失败。

在仓库根目录运行 `py .\run_all.py`。环境和依赖见[仓库说明](../README.md#运行)。`RCS-4: False` 是预期结果，报告应同时显示 `EXP-02 acceptance: PASS`。

| `results/exp02/` 中的文件 | 内容 |
| --- | --- |
| `exp02_report.txt` | 定性条件、反例见证与验收结果 |
| `oscillatory_stages.csv`、`oscillatory_witness.csv` | 精确阶段读数和阈值反例 |
| `figures/exp02_readout_sequence.png` | 振荡线程图 |
| `figures/exp01_exp02_readouts.png` | Pell 与振荡线程并列图，由同次批跑的两份 CSV 生成 |

依据为 RCS v1.1 命题 7.2，以及式 (10)–(13)、(47)–(48)、(58)。固定 $k=2$，对任意候选阈值 $N$ 取阶段 $N,N+1$，两项之差为 $1>1/2$。该线程超出完备化映射的稳定线程定义域。
