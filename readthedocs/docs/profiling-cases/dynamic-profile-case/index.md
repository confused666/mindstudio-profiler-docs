# 集群场景动态 Profile 性能数据采集与分析指导

集群训练或在线推理任务往往运行时间长、重启成本高，常规 Profiling 难以精确卡住问题窗口。`dynamic_profile` 可以在任务运行过程中按需触发采集，避免频繁改脚本和反复重启任务。

本文给出一条面向集群场景的最小闭环实践：先在业务中集成 `dynamic_profile`，在问题时段动态触发采集，再使用 `msprof-analyze` 完成集群拆解与 `advisor` 专家建议分析，最后通过 MindStudio Insight 先看集群汇总结果，再下载指定 rank 的 Profiling 数据做细粒度下钻。完整流程的主要产物包括：`*_ascend_pt` 集群数据目录、`cluster_analysis_output`、`mstt_advisor_*.html/.xlsx`、指定 rank 的本地 Profiling 数据，以及 Insight 可视化视图。

## 1. 整体流程

<style>
.dynamic-profile-flow {
    --dp-border: rgba(15, 23, 42, 0.08);
    --dp-bg: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    --dp-accent: #0f766e;
    --dp-accent-soft: rgba(15, 118, 110, 0.08);
    --dp-text: #0f172a;
    --dp-subtext: #475569;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 16px;
    margin: 20px 0 12px 0;
}

.dynamic-profile-flow .flow-card {
    position: relative;
    padding: 18px 18px 20px 18px;
    border-radius: 18px;
    border: 1px solid var(--dp-border);
    background: var(--dp-bg);
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}

.dynamic-profile-flow .flow-card:not(:last-child)::after {
    content: "→";
    position: absolute;
    right: -13px;
    top: 50%;
    transform: translateY(-50%);
    width: 26px;
    height: 26px;
    border-radius: 999px;
    background: #ffffff;
    border: 1px solid var(--dp-border);
    color: var(--dp-accent);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    z-index: 2;
}

.dynamic-profile-flow .flow-step {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 999px;
    background: var(--dp-accent-soft);
    color: var(--dp-accent);
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 12px;
}

.dynamic-profile-flow h3 {
    margin: 0 0 10px 0;
    color: var(--dp-text);
    font-size: 16px;
}

.dynamic-profile-flow p {
    margin: 0;
    color: var(--dp-subtext);
    font-size: 13px;
    line-height: 1.7;
}

@media (max-width: 1000px) {
    .dynamic-profile-flow {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .dynamic-profile-flow .flow-card:not(:last-child)::after {
        display: none;
    }
}

@media (max-width: 640px) {
    .dynamic-profile-flow {
        grid-template-columns: 1fr;
    }
}
</style>

<div class="dynamic-profile-flow">
    <div class="flow-card">
        <div class="flow-step">01</div>
        <h3>动态 Profile 集成</h3>
        <p>输入：运行中的训练或推理任务、共享配置目录。输出：具备动态触发能力的业务进程与自动生成的 <code>profiler_config.json</code> 模板。</p>
    </div>
    <div class="flow-card">
        <div class="flow-step">02</div>
        <h3>动态触发采集</h3>
        <p>输入：问题时段、推荐采集配置。输出：同一次采集生成的多 rank <code>*_ascend_pt</code> 集群性能数据目录。</p>
    </div>
    <div class="flow-card">
        <div class="flow-step">03</div>
        <h3>集群分析与 Advisor</h3>
        <p>输入：聚合后的集群 Profiling 根目录。输出：<code>cluster_analysis_output</code>、<code>cluster_analysis.db</code>、<code>mstt_advisor_*.html/.xlsx</code>。</p>
    </div>
    <div class="flow-card">
        <div class="flow-step">04</div>
        <h3>Insight 汇总与下钻</h3>
        <p>输入：<code>cluster_analysis_output</code> 与指定 rank 的 Profiling 数据。输出：先完成集群定界，再对目标 rank 做 Timeline 级根因分析。</p>
    </div>
</div>

推荐按照“先汇总、后下钻”的顺序使用工具：先用 `msprof-analyze` 和 MindStudio Insight 快速确定问题集中在哪些 rank、阶段或维度，再把分析范围收敛到指定 rank，避免一开始就直接陷入单卡细节。

## 2. 动态 Profile 功能集成

`dynamic_profile` 适合长时间运行任务和需要按需触发采集的场景。三种方式中，集群最佳实践通常优先考虑环境变量方式和 `dp.init()` 方式：前者零侵入，后者适用范围更广。

### 2.1 非侵入式修改：环境变量方式

环境变量方式适合训练场景，不需要修改用户代码，通过配置文件即可动态触发采集。

```bash
export PROF_CONFIG_PATH="/path/to/profiler_config_path"
```

最小操作链如下：

1. 在所有训练节点配置 `PROF_CONFIG_PATH`，建议指向共享存储路径。
2. 启动训练任务，`dynamic_profile` 会在该目录下自动生成模板文件 `profiler_config.json`。
3. 在新的终端中修改 `profiler_config.json`，写入本次采集的触发参数。
4. 任务运行到目标 step 后自动开始采集，结束后按配置自动解析或后续离线解析。

环境变量方式的限制需要在文中明确说明：

- 不支持采集第一个迭代 `step0`。
- 依赖 PyTorch 原生 `Optimizer.step()` 划分 step，不支持自定义 Optimizer。
- `PROF_CONFIG_PATH` 要求有读写权限，路径仅支持字母、数字、下划线和连字符，不支持软链接。

### 2.2 手动适配集成动态 Profile

如果业务是在线推理场景，或希望以代码方式显式接入动态采集能力，推荐使用 `dp.init()` 方式。

```python
from torch_npu.profiler import dynamic_profile as dp

dp.init("profiler_config_path")

for step in steps:
    train_one_step()
    dp.step()
```

这种方式的特点是：

- 同时支持训练和在线推理。
- `dp.init()` 执行时会自动创建 `profiler_config.json` 模板。
- 运行任务后，可在新的终端中修改 `profiler_config.json`，动态触发采集。
- 如果采集执行期间再次修改配置，会在当前采集结束后启动最后一次修改对应的采集任务。

选择建议可以简化为：

- 希望零侵入改造时，优先选环境变量方式。
- 需要支持在线推理，或希望显式管理步进逻辑时，优先选 `dp.init()`。
- 只想对某个特定代码片段做精确触发时，再补充使用 `dp.start()`。

`dp.start()` 更适合在代码中预置精确触发点，缩小采集范围：

```python
from torch_npu.profiler import dynamic_profile as dp

dp.init("profiler_config_path")

for step in steps:
    if step == 5:
        dp.start("/home/xx/start_config_path/profiler_config.json")
    train_one_step()
    dp.step()
```

使用 `dp.start()` 时需要注意：

- `start_config_path` 需要用户手动准备完整的 `profiler_config.json`。
- 一次任务执行过程中只触发一次采集，不感知后续配置文件修改。
- 如果 `dp.init()` 触发的采集已经在执行中，`dp.start()` 不会生效。

更多接口说明可参考 [dynamic_profile 动态采集](../../torch_npu_profiler/source/user_guide/dynamic_profile.md)。

## 3. 动态 Profile 触发

### 3.1 全量rank采集配置

```json
{
  "activities": ["CPU", "NPU"],
  "prof_dir": "./cluster_profile_output", # 根据实际路径修改
  "analyse": true,
  "async_mode": true, # 开启异步解析
  "record_shapes": false,
  "profile_memory": false,
  "with_stack": false,
  "with_flops": false,
  "with_modules": false,
  "active": 2,
  "warmup": 0,
  "start_step": -1, # 根据实际采集step num修改
  "is_rank": false, # 采集所有rank
  "rank_list": [],
  "experimental_config": {
    "profiler_level": "Level1", # 采集通信task数据
    "aic_metrics": "AiCoreNone",
    "l2_cache": false,
    "op_attr": false,
    "gc_detect_threshold": null,
    "data_simplification": true,
    "record_op_args": false,
    "export_type": ["db"], # 导出为db，降低文件体积
    "mstx": false,
    "mstx_domain_include": [],
    "mstx_domain_exclude": [],
    "host_sys": [],
    "sys_io": false,
    "sys_interconnection": false
  }
}
```

### 3.1 部分rank采集配置

```json
{
  "activities": ["CPU", "NPU"],
  "prof_dir": "./cluster_profile_output", # 根据实际路径修改
  "analyse": true,
  "async_mode": true, # 开启异步解析
  "record_shapes": false,
  "profile_memory": false,
  "with_stack": false,
  "with_flops": false,
  "with_modules": false,
  "active": 2,
  "warmup": 0,
  "start_step": -1, # 根据实际采集step num修改
  "is_rank": true, # 采集部分rank
  "rank_list": [1, 2, 3, 4], # 指定采集rank id
  "experimental_config": {
    "profiler_level": "Level1", # 采集通信task数据
    "aic_metrics": "AiCoreNone",
    "l2_cache": false,
    "op_attr": false,
    "gc_detect_threshold": null,
    "data_simplification": true,
    "record_op_args": false,
    "export_type": ["db"], # 导出为db，降低文件体积
    "mstx": false,
    "mstx_domain_include": [],
    "mstx_domain_exclude": [],
    "host_sys": [],
    "sys_io": false,
    "sys_interconnection": false
  }
}
```

如果需要进一步查看参数含义，可参考 [profiler_config.json 配置文件](../../torch_npu_profiler/source/user_guide/dynamic_profile.md#profiler_configjson-配置文件) 和 [`experimental_config` 参考](../../torch_npu_profiler/source/user_guide/profile_api.md#experimental_config)。

### 3.2 注意事项

下面这些约束直接决定后续集群分析是否顺利，建议以 checklist 方式执行：

- 集群分析和 `advisor` 都要求输入目录中包含同一次采集生成的多 rank 完整数据。
- 更新`profiler_config.json`使用直接修改报错的方式，不要使用删除、文件拷贝覆盖的方式。
- `start_step` 应大于当前已执行 step，且不超过任务的最大 step。
- 如果问题窗口不确定，优先多次短窗口采集，不建议单次拉很长的 `active` 区间。

## 4. `msprof-analyze` 集群分析

### 4.1 输入目录要求

执行集群分析前，需要先把同一次采集的所有 rank 数据汇集到一个目录下，并将 `-d` 指向这个聚合后的集群根目录。该目录下应包含多个同批次生成的 `*_ascend_pt` 子目录。

一个典型输入结构如下：

```text
cluster_data/
├── node1_xxx_ascend_pt
├── node1_yyy_ascend_pt
├── node2_xxx_ascend_pt
└── node2_yyy_ascend_pt
```

建议保证：

- 只包含同一次采集的全量 rank 数据。
- 不要混入不同批次或不同任务的 Profiling 目录。
- 目录层级和命名保持完整，便于工具正确识别 rank 与通信关系。

### 4.2 分析命令

完成数据汇集后，可以先执行集群拆解，再执行 `advisor`。

1. 使用 `cluster_time_summary` 做集群耗时拆解：

```bash
msprof-analyze -m cluster_time_summary -d ./cluster_data -o ./output
```

2. 使用 `slow_rank` 快速识别慢卡：

```bash
msprof-analyze -m slow_rank -d ./cluster_data -o ./output
```

3. 使用 `advisor all` 输出整体瓶颈与优化建议：

```bash
msprof-analyze advisor all -d ./cluster_data -o ./advisor_output
```

其中 `advisor` 在集群场景下，`-d` 需要指向 `*_ascend_pt` 的父目录层级，也就是聚合后的 `cluster_data` 根目录。

### 4.3 输出物与结果解读

执行完成后，重点关注以下输出物：

- `cluster_analysis_output/cluster_analysis.db`
- `mstt_advisor_<timestamp>.html`
- `mstt_advisor_<timestamp>.xlsx`

阅读顺序建议如下：

- `cluster_time_summary`：优先看计算、通信、空闲时间的拆解占比，判断瓶颈更偏向计算、通信还是 Host/调度等待。
- `slow_rank`：看哪些 rank 被投票为慢卡最多，优先锁定重点对象。
- `advisor`：看整体瓶颈归类和对应优化建议，用于辅助判断问题是否已经具备明确方向。

如果只需要一个最小判断路径，可以先看 `cluster_time_summary` 和 `slow_rank` 确定问题集中在哪些 rank，再用 `advisor` 辅助给出下一步优化方向。

`msprof-analyze` 更多说明可参考 [集群性能数据细粒度拆解](../../msprof-analyze/source/advanced_features/cluster_time_summary_instruct.md) 和 [专家建议](../../msprof-analyze/source/user_guide/advisor_instruct.md)。

## 5. MindStudio Insight 可视化

MindStudio Insight 的使用原则建议固定为两步：先导入 `cluster_analysis_output` 查看集群汇总结果，再下载指定 rank 的 Profiling 数据到本地做细节可视化。

### 5.1 先看 `cluster_analysis_output`

`cluster_analysis_output` 适合用于集群级定界，重点查看：

- Summary：看计算、通信、空闲的整体概览。
- Communication：看通信耗时与通信矩阵，判断问题更偏向慢卡还是慢链路。

这一阶段的目标不是直接找根因，而是先回答两个问题：

1. 问题主要集中在哪些 rank、哪些 stage 或哪些通信域。
2. 问题更偏向计算不均、通信异常，还是空闲时间过高。

### 5.2 再下钻指定 rank

当通过集群汇总结果已经锁定目标 rank 后，再下载该 rank 对应的 `*_ascend_pt` Profiling 数据到本地，并导入 MindStudio Insight 做细粒度分析。此时重点查看：

- Timeline：观察目标 rank 在异常时间段前后的行为。
- 必要时结合 Overlap Analysis：判断空闲、通信和计算之间的关系。

推荐操作路径如下：

1. 导入 `cluster_analysis_output`。
2. 在 Summary 和 Communication 中判断问题集中在哪些 rank 或阶段。
3. 下载目标 rank 的 Profiling 数据到本地。
4. 导入该 rank 的 `*_ascend_pt` Profiling 目录。
5. 在 Timeline 中完成根因分析。

> [!NOTE] 实践建议
>
> MindStudio Insight 仅支持本地磁盘数据导入。因此，在集群场景下，建议先基于 `cluster_analysis_output` 完成远端汇总分析，再把目标 rank 的 Profiling 数据下载到本地后继续下钻。

MindStudio Insight 的基础导入方法可参考 [基础操作](../../msinsight/source/user_guide/basic_operations.md#导入数据)，系统调优可参考 [系统调优指南](../../msinsight/source/user_guide/system_tuning.md)。

## 6. 参考链接

- [Ascend PyTorch Profiler 的 dynamic_profile 动态采集](https://www.hiascend.com/document/detail/zh/canncommercial/850/devaids/Profiling/atlasprofiling_16_0033.html#ZH-CN_TOPIC_0000002534478481__section17272160135118)
- [msprof-analyze](https://gitcode.com/Ascend/msprof-analyze)
- [MindStudio Insight](https://gitcode.com/Ascend/msinsight)
