# 从开工到交付

## P0 环境、范围、来源
使用当前目录作为唯一工作区，自动探测RAM/CPU/磁盘/依赖/LaTeX。优先Python3.11或3.12，项目.venv，不污染Conda base。默认12进程，每进程BLAS1线程。进程启动方式spawn，所有入口有main guard。阅读原文与72小时补充；第一次运行写state/STATUS.md。记录参考链接及实际阅读范围，不伪造已读全文或EI源表核验。

## P1 参考实现与测速
安装requirements，运行pytest、`python scripts/audit_design.py`和smoke。先检查B的解析退化；如上界在大预算下恒饱和，开封前按数学证据退役该B设置，不浪费全量求值。初始SciPy参考后端逐scramble构造引擎，正确但可能慢；可安装requirements-fast用QMCPy replications，明确版本、LMS+DS、比特数、形状和种子。QMCPy在本包构建时未安装成功，不能把其适配器当作已测试。只有本机测试通过后才改config.backend；禁止执行中静默fallback换后端。
`python scripts/run.py --phase benchmark --workers 1` 执行代表任务和完整费用计时；`--workers 8/12/16`做受限吞吐测试。benchmark只用开发案例，不看确认结果。统计各环节并预测完整矩阵；脚本给保守粗估不是实测9950X保证。若明显超预算先实现成熟批量采样，不用50轮科学调参。可用运行平台约束减少确认重复到1000，但必须在开封前写入冻结且诚实报告精度。

## P2 开发
`python scripts/run.py --phase development --workers 12`。仅A/B两条、固定超参和PLUGIN对照。开发结果从results/raw/development.jsonl汇总；不得强迫显著。`python scripts/summarize.py --phase development`。评估含先导费用的宽度与覆盖，查B上界饱和和A全零误判。
选跨开发案例统一主baseline：固定n方法跨case/budget几何平均宽度比（每格权重相同），限定数值正确/无异常空集；不可每个确认case看真值换基线。选主A或B，填写`state/research_review.json`，见模板。无空间直接STOPPED_NO_SIGNAL并写FAILURE_REPORT。

## P3 冻结、正式确认
核对独立实现/论文近邻/参考文献；写审查证据路径。`python scripts/freeze.py --winner A --baseline fixed_4` （示例，必须来自开发）。脚本会检查审查文件各项完成、证据文件存在、开发结果、保存配置/源代码/环境指纹。不要手工创建伪冻结。然后`python scripts/run.py --phase confirmation --workers 12`。确认模式拒绝更改科学配置/源代码；允许相同参数续跑缺失任务，不能覆盖已完成task。
正式case新参数和未用于开发的函数族；主EBCI矩阵和预定HBCI子矩阵。不能见结果不稳后追加第3路线或改重试种子。确认所有方法同预算、同CI口径，不虚报被省略的方法。

## P4 统计与稿件
汇总原始重复、Wilson覆盖区间、差异/MCSE、数值失败及空集合。需要Codex补齐配对结果差、bootstrap/多比较、4主图3主表、图数据导出；起步summary不是完整论文统计。统计配对来自预定外层任务ID，方法随机流不共享，不能声称CRN减方差。单独单进程测速用于延迟比较；并发运行的时间只描述吞吐。
目标Algorithms先核EI Journal/ISSN再取官方模板 `python scripts/fetch_template.py`。网络失败诚实记录，继续实验；未拿到模板不得标格式已合规。正文与补充按docs/PAPER_REQUIREMENTS写齐，无未运行结果。用`python scripts/build_pdf.py`真实编译，render后Codex逐页打开图检查，并记录page review；单纯存在PNG不等于看过。引用核验、作者问题与AI披露、source ZIP干净重编译；完成后handoff/STATUS。

## P5 整理
先通过可复现验证，再`python scripts/safe_clean.py`看候选清单，`--apply`删除允许的缓存。不删原始重复、阶段失败摘要、config/冻结、用户设计、文献证据。无效探索大文件可在.tmp创建和删，不将研究负面结果当垃圾。最终只保留当前有效项目和必要审计，不保存几十版论文。

## 硬停止
两条无用、直接近邻完全覆盖、公式/随机化未验证、预算不可能或确认否定。交付失败报告不是装作论文成功；必要时完整结果比较稿仅在有独立新发现后进入写作。账户或网络中断为BLOCKED/RESUMABLE，不算科学路线失败。
