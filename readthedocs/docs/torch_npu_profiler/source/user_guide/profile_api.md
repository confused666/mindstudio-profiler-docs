# profile 接口采集

Ascend PyTorch Profiler完全对标PyTorch-GPU场景下的使用方式，支持采集PyTorch框架和昇腾软硬件数据。该方式提供`with`语句和`start/stop`语句两种使能方式，同时用户可以通过设置`schedule`参数灵活控制不同step的Profiling行为。

## 方式一：使用 `with` 语句

该方式会自动创建和释放 Profiler，适合最常见的训练和推理采集场景。

```python
import torch
import torch_npu

experimental_config = torch_npu.profiler._ExperimentalConfig(
    export_type=[torch_npu.profiler.ExportType.Text],
    profiler_level=torch_npu.profiler.ProfilerLevel.Level0,
    mstx=False,
    mstx_domain_include=[],
    mstx_domain_exclude=[],
    aic_metrics=torch_npu.profiler.AiCMetrics.AiCoreNone,
    l2_cache=False,
    op_attr=False,
    data_simplification=False,
    record_op_args=False,
    gc_detect_threshold=None,
    host_sys=[],
    sys_io=False,
    sys_interconnection=False,
)

with torch_npu.profiler.profile(
    activities=[
        torch_npu.profiler.ProfilerActivity.CPU,
        torch_npu.profiler.ProfilerActivity.NPU,
    ],
    schedule=torch_npu.profiler.schedule(wait=0, warmup=0, active=1, repeat=1, skip_first=1),
    on_trace_ready=torch_npu.profiler.tensorboard_trace_handler("./result"),
    record_shapes=False,
    profile_memory=False,
    with_stack=False,
    with_modules=False,
    with_flops=False,
    experimental_config=experimental_config,
) as prof:
    for step in range(steps):
        train_one_step(step, steps, train_loader, model, optimizer, criterion)
        prof.step()
```

## 方式二：手动控制 `start()` 和 `stop()`

该方式适合需要精确控制采集起止位置的场景。

```python
import torch
import torch_npu


experimental_config = torch_npu.profiler._ExperimentalConfig(
    export_type=[torch_npu.profiler.ExportType.Text],
    profiler_level=torch_npu.profiler.ProfilerLevel.Level0,
    mstx=False,
    aic_metrics=torch_npu.profiler.AiCMetrics.AiCoreNone,
    l2_cache=False,
    op_attr=False,
    data_simplification=False,
    record_op_args=False,
    gc_detect_threshold=None,
    host_sys=[],
    sys_io=False,
    sys_interconnection=False,
)

prof = torch_npu.profiler.profile(
    activities=[
        torch_npu.profiler.ProfilerActivity.CPU,
        torch_npu.profiler.ProfilerActivity.NPU,
    ],
    schedule=torch_npu.profiler.schedule(wait=0, warmup=0, active=1, repeat=1, skip_first=1),
    on_trace_ready=torch_npu.profiler.tensorboard_trace_handler("./result"),
    record_shapes=False,
    profile_memory=False,
    with_stack=False,
    with_modules=False,
    with_flops=False,
    experimental_config=experimental_config,
)

prof.start()
for step in range(steps):
    train_one_step()
    prof.step()
prof.stop()
```

## 使用说明

- 建议显式配置 `schedule`，并配合 `prof.step()` 使用，以便采集带step信息的性能数据。请参考 [schedule 说明](schedule_reference.md)。
- 大集群且使用共享存储时，直接通过 `on_trace_ready` 落盘可能带来额外性能膨胀，应根据场景评估是否改用离线解析。
- 当训练Step数超过采集范围后，Profiler将默认自动同步解析，该过程会阻塞训练/推理进程。如需调整，可通过设置[tensorboard_trace_handler](#tensorboard_trace_handler参数)的`analyse_flag=False`关闭解析，或设置`async_mode=True`开启异步解析。

## 采集配置

采集配置主要分为通用和特有两类：`torch_npu.profiler`接口与`torch.profiler`保持兼容，用法一致；而`experimental_config`则是昇腾性能采集的特有配置参数。

### torch_npu.profiler

#### 主要参数

| 参数名称 | 说明 | 是否必选 |
| --- | --- | --- |
| `activities` | CPU、NPU 事件采集列表。默认同时开启 CPU 和 NPU。 | 否 |
| `schedule` | 设置不同 step 的采集行为。`_KinetoProfile` 不支持。 | 否 |
| `on_trace_ready` | 采集结束时自动执行的回调，常用为 `tensorboard_trace_handler`。 | 否 |
| `record_shapes` | 是否采集算子 `InputShapes` 和 `InputTypes`。 | 否 |
| `profile_memory` | 是否采集显存占用信息。 | 否 |
| `with_stack` | 是否采集调用栈。 | 否 |
| `with_modules` | 是否采集 modules 层级的 Python 调用栈。 | 否 |
| `with_flops` | 是否采集浮点操作信息。当前暂不支持解析。 | 否 |
| `experimental_config` | 扩展采集配置。 | 否 |
| `use_cuda` | 昇腾环境不支持。 | 否 |

#### tensorboard_trace_handler参数

| 参数名称 | 说明                                                                           | 是否必选 |
| --- |------------------------------------------------------------------------------| --- |
| `worker_name` | 用于区分唯一的工作线程，string类型，默认为{hostname}_{pid}。路径格式仅支持由字母、数字、下划线和连字符组成的字符串，不支持软链接  | 否 |
| `analyse_flag` | 性能数据自动解析开关，bool类型。取值True（开启自动解析，默认值）、False（关闭自动解析，采集完后的性能数据可以使用离线解析）         | 否 |
| `async_mode` | 控制是否开启异步解析（表示解析进程不会阻塞AI任务主流程），bool类型。取值True（开启异步解析）、False（关闭异步解析，即同步解析，默认值）  | 否 |

### experimental_config

`experimental_config` 用于配置扩展采集项。

#### 主要参数

| 参数 | 说明 |
| --- | --- |
| `export_type` | 导出结果格式，支持 `Text`/`Db` 或配置文件中的 `text`/`db`。 |
| `profiler_level` | 采集等级，支持 `Level_none`、`Level0`、`Level1`、`Level2`。 |
| `aic_metrics` | AI Core 性能指标采集项。 |
| `l2_cache` | 是否采集 L2 Cache 数据。 |
| `op_attr` | 是否采集算子属性信息。 |
| `gc_detect_threshold` | GC 检测阈值，单位 ms。 |
| `data_simplification` | 是否开启数据精简模式。 |
| `record_op_args` | 是否输出算子信息统计结果。 |
| `mstx` / `msprof_tx` | 是否开启自定义打点。 |
| `mstx_domain_include` | 只输出指定 domain 的 mstx 数据。 |
| `mstx_domain_exclude` | 过滤指定 domain 的 mstx 数据。 |
| `host_sys` | 是否采集 Host 侧 CPU、内存、磁盘、网络、OSRT 等系统数据。 |
| `sys_io` | 是否采集 NIC、ROCE、MAC 数据。 |
| `sys_interconnection` | 是否采集集合通信带宽、PCIe、片间传输带宽信息。 |

#### `profiler_level` 建议

- `Level0`：默认值，适合大多数常规采集场景。
- `Level1`：在 `Level0` 基础上增加 AscendCL 和 AI Core 指标，适合进一步分析计算与通信细节。
- `Level2`：在 `Level1` 基础上增加 Runtime 和 AI CPU 数据，适合更深入的问题定位。
- `Level_none`：关闭层级数据采集，常与 mstx 场景配合使用。

#### 注意事项

- `mstx_domain_include` 与 `mstx_domain_exclude` 互斥。
- `record_op_args` 主要面向 AOE 调优场景，不建议与其他性能采集接口同时开启。
- `host_sys` 中的部分采集项依赖第三方工具，如 `iotop`、`perf`、`ltrace`，并需要额外权限配置。

## 典型场景下的推荐配置

| 使用场景 | 配置参数                                                                                        |
| --- |---------------------------------------------------------------------------------------------|
| `常规性能分析场景` | profiler_level=l1<br>aic_metrics 保持默认PipeUtilization<br>activities设置采集CPU和NPU<br>其他开关根据需要开启 |
| `NPU/GPU对比场景` | 该配置用于对比NPU和GPU端到端耗时：<br>profiler_level=l0<br>activities设置仅采集NPU或CPU和NPU（根据需要）<br> 其他开关关闭    |
| `定位代码位置场景` | 如需要定位异常算子代码位置，可在常规场景下开启with_stack或with_modules开关开启调用栈（非必要不开启，性能会膨胀）                         |
