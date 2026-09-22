---
hide:
  - navigation
  - toc
---


# 性能调优工具全景

## 性能调优工具链

<style>
.ai-arch-container {
    --ai-accent-blue: #3b82f6;
    --ai-text-dark: #1e293b;
    --ai-bg-section: #f8fafc;
    --ai-transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 20px 20px 40px 20px;
    box-sizing: border-box;
}

.ai-arch-container * {
    box-sizing: border-box;
}

.ai-arch-container .arch-wrapper {
    position: relative;
    display: flex;
    flex-direction: row;
    gap: 24px;
    padding: 40px;
    background: #ffffff;
    border-radius: 24px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.8);
    width: 100%;
    max-width: 1200px;
    margin: 0 auto;
}

.ai-arch-container .main-layers {
    display: flex;
    flex-direction: column;
    gap: 20px;
    flex: 1;
}

.ai-arch-container .layer-section {
    display: flex;
    background: var(--ai-bg-section);
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid rgba(226, 232, 240, 0.7);
    transition: var(--ai-transition);
}

.ai-arch-container .layer-title {
    width: 48px;
    writing-mode: vertical-lr;
    text-orientation: mixed;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #e2e8f0;
    color: #475569;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 2px;
    border-right: 1px solid rgba(203, 213, 225, 0.5);
}

.ai-arch-container .layer-content {
    flex: 1;
    padding: 20px;
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
}

.ai-arch-container .layer-content-3 {
    grid-template-columns: repeat(3, 1fr);
}

.ai-arch-container .module {
    position: relative;
    background: #ffffff;
    padding: 14px 20px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
    transition: var(--ai-transition);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
    color: var(--ai-text-dark);
    border: 1px solid rgba(226, 232, 240, 0.8);
    text-align: center;
}

.ai-arch-container .module:hover {
    background: var(--ai-accent-blue);
    color: #ffffff !important;
    transform: translateY(-3px);
    box-shadow: 0 8px 20px rgba(59, 130, 246, 0.25);
    border-color: var(--ai-accent-blue);
}

.ai-arch-container .tool-card {
    width: 100px;
    background: var(--ai-bg-section);
    border: 1px solid rgba(226, 232, 240, 0.8);
    border-radius: 16px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 20px 10px;
    text-align: center;
    font-size: 14px;
    font-weight: 700;
    transition: var(--ai-transition);
    cursor: pointer;
    color: var(--ai-text-dark);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
}

.ai-arch-container .tool-card:hover {
    background: #1e293b;
    color: #ffffff;
    transform: scale(1.05);
}

.ai-arch-container #dynamic-preview {
    position: absolute;
    width: 260px;
    background: #ffffff;
    border-radius: 14px;
    padding: 18px;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.15);
    pointer-events: none;
    opacity: 0;
    transform: translateX(10px);
    transition: opacity 0.3s, transform 0.3s;
    z-index: 2000;
    border: 1px solid rgba(0, 0, 0, 0.06);
}

.ai-arch-container #dynamic-preview.active {
    opacity: 1;
    transform: translateX(0);
}

.ai-arch-container .preview-h {
    font-weight: 800;
    color: var(--ai-accent-blue);
    margin-bottom: 8px;
    font-size: 15px;
}

.ai-arch-container .preview-p {
    font-size: 13px;
    color: #64748b;
    line-height: 1.6;
    margin: 0;
}

.ai-arch-container .span-2 { grid-column: span 2; }
.ai-arch-container .flex-center { justify-content: center; }
.ai-arch-container .justify-content-around { justify-content: space-around; }

@media (max-width: 850px) {
    .ai-arch-container .arch-wrapper {
        flex-direction: column;
        align-items: stretch;
    }

    .ai-arch-container .tool-card {
        width: 100%;
        flex-direction: row;
        padding: 15px;
        gap: 15px;
    }

    .ai-arch-container #dynamic-preview {
        display: none !important;
    }
}

@media (max-width: 550px) {
    .ai-arch-container {
        padding: 20px 10px;
    }

    .ai-arch-container .layer-content,
    .ai-arch-container .layer-content-3 {
        grid-template-columns: 1fr;
        padding: 12px;
    }

    .ai-arch-container .span-2 {
        grid-column: span 1;
    }

    .ai-arch-container .layer-title {
        width: 36px;
        font-size: 11px;
    }

    .ai-arch-container .module {
        font-size: 13px;
        padding: 12px;
    }
}
</style>

<div class="ai-arch-container">
    <div class="arch-wrapper" id="container">
        <div class="main-layers">
            <div class="layer-section">
                <div class="layer-title">分析工具</div>
                <div class="layer-content">
                    <div class="module" data-title="msprof-analyze" data-desc="面向 AI 训练与推理场景的性能分析工具，具备性能比对、集群分析、专家建议等功能。">
                        msprof-analyze
                    </div>
                    <div class="module" data-title="msAgent" data-desc="专注于性能问题定位的Agent。">
                        msAgent
                    </div>
                </div>
            </div>

            <div class="layer-section">
                <div class="layer-title">性能监控</div>
                <div class="layer-content">
                    <div class="module span-2 flex-center" data-title="msMonitor" data-desc="面向昇腾集群场景的在线性能监控与动态采集工具。">
                        MindStudio Monitor
                    </div>
                </div>
            </div>

            <div class="layer-section">
                <div class="layer-title">AI框架</div>
                <div class="layer-content justify-content-around">
                    <div class="module" data-title="PyTorch Profiler" data-desc="基于PyTorch框架开发的昇腾软硬件性能调优工具。">PyTorch Profiler</div>
                    <div class="module" data-title="MindSpore Profiler" data-desc="基于昇思MindSpore框架开发的昇腾软硬件性能调优工具。">MindSpore Profiler</div>
                </div>
            </div>

            <div class="layer-section">
                <div class="layer-title">基础能力</div>
                <div class="layer-content layer-content-3">
                    <div class="module" data-title="msProf" data-desc="昇腾Profiling命令行工具，支持采集与解析 CANN 平台及昇腾 AI 处理器的软硬件性能数据。">msProf</div>
                    <div class="module" data-title="MSTX" data-desc="MindStudio Tools Extension Library，支持用户自定义打点。">MSTX</div>
                    <div class="module" data-title="MSPTI" data-desc="MindStudio Profiler Tools Interface，面向昇腾设备的 Profiling API 集合。">MSPTI</div>
                </div>
            </div>
        </div>

        <div class="tool-card" data-title="MindStudio Insight" data-desc="全流程可视化性能分析套件，支持 Timeline、算子清单及智能瓶颈定位。">
            MindStudio Insight
        </div>

        <div id="dynamic-preview">
            <div class="preview-h" id="pre-title"></div>
            <p class="preview-p" id="pre-desc"></p>
        </div>
    </div>
</div>

<script>
(function () {
    const targetHrefMap = {
        'msprof-analyze': '../msprof-analyze/',
        'MindStudio Insight': '../msinsight/',
        'msAgent': '../msagent/',
        'msMonitor': '../msmonitor/',
        'PyTorch Profiler': '../torch_npu_profiler/',
        'MindSpore Profiler': 'https://www.mindspore.cn/mindinsight/docs/zh-CN/r2.3/performance_profiling_ascend.html',
        'msProf': '../msprof/',
        'MSTX': '../torch_npu_profiler/source/advanced_features/mstx',
        'MSPTI': '../mspti/'
    };

    function initToolchainMap() {
        const arch = document.querySelector('.ai-arch-container');
        if (!arch || arch.dataset.initialized === 'true') {
            return;
        }

        arch.dataset.initialized = 'true';

        const preview = arch.querySelector('#dynamic-preview');
        const pTitle = arch.querySelector('#pre-title');
        const pDesc = arch.querySelector('#pre-desc');
        const container = arch.querySelector('#container');
        const targets = arch.querySelectorAll('.module, .tool-card');

        if (!preview || !pTitle || !pDesc || !container || !targets.length) {
            return;
        }

        const hidePreview = () => {
            preview.classList.remove('active');
        };

        const showPreview = (target) => {
            if (window.innerWidth <= 850) {
                return;
            }

            pTitle.innerText = target.getAttribute('data-title') || '';
            pDesc.innerText = target.getAttribute('data-desc') || '';

            const rect = target.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();

            preview.style.top = (rect.top - containerRect.top) + 'px';
            preview.style.left = (rect.right - containerRect.left + 15) + 'px';
            preview.classList.add('active');
        };

        const navigateToTarget = (target) => {
            const title = target.getAttribute('data-title') || '';
            const href = targetHrefMap[title];
            if (!href) {
                return;
            }

            window.location.assign(href);
        };

        container.addEventListener('mouseleave', hidePreview);

        targets.forEach((target) => {
            target.setAttribute('role', 'link');
            target.setAttribute('tabindex', '0');

            target.addEventListener('mouseenter', () => showPreview(target));
            target.addEventListener('focus', () => showPreview(target));
            target.addEventListener('mouseleave', hidePreview);
            target.addEventListener('blur', hidePreview);
            target.addEventListener('click', () => navigateToTarget(target));
            target.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    navigateToTarget(target);
                }
            });
        });
    }

    if (typeof document$ !== 'undefined' && typeof document$.subscribe === 'function') {
        document$.subscribe(initToolchainMap);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initToolchainMap, { once: true });
    } else {
        initToolchainMap();
    }
})();
</script>

## 性能数据与采集工具

MindStudio 提供多种性能数据采集能力，可覆盖 AI 框架层、CANN 层和 NPU 硬件层，下图展示了“性能数据”与“采集工具”之间的对应关系。

![profiling-data](../assets/images/profling-data.png)

<style>
.md-typeset table {
    margin-left: auto;
    margin-right: auto;
}
</style>

### 按采集入口选择工具

从采集入口看，性能数据采集主要分为两类：

* msProf 采集工具：主要采集 CANN 层和 NPU 硬件层数据，是其他 Profiling 采集接口的基础能力。
* AI 框架 Profiler 接口采集：在 `msProf` 能力之上，进一步补充 AI 框架层数据采集与解析，是最常用的方式。当前主要包括 Ascend PyTorch Profiler 和 MindSpore Profiler。此外，一些训练或推理套件还会在此基础上进一步封装，例如 MindSpeed-MM、MindFormers、vLLM 等，可直接通过套件接口调用。

| 采集工具 | 特点 | 推荐场景 |
|---|---|---|
| Ascend PyTorch Profiler | 对标 PyTorch GPU 场景的使用方式，支持同时采集 PyTorch 框架层和昇腾软硬件层数据。 | PyTorch 框架模型的常规性能分析 |
| MindSpore Profiler | 与 MindSpore 深度集成，接口简单，使用成本低。 | MindSpore 框架模型的常规性能分析 |
| msProf | 采集 CANN 层与 NPU 层性能数据，不包含 AI 框架层数据，是其他工具的底座。 | 各类训练和推理场景，尤其适合非 PyTorch/MindSpore 框架，或需要精细控制采集过程的场景 |

### 按采集方式选择方案

从功能特性看，性能采集可分为常规采集、动态采集和轻量化在线监测三类。三种方式的侧重点不同：常规采集适合深度分析，动态采集适合长时间运行任务，轻量化采集适合常态化在线监控。

| 采集方式 | 特点 | 推荐场景 |
|---|---|---|
| 常规采集 | 预先设置采集周期或执行全量采集，落盘详细性能数据。 | 常规性能分析 |
| `dynamic_profile` 动态采集 | 在模型训练或推理过程中可按需开启采集、动态修改采集配置，无需频繁改动脚本代码。 | 启停成本高的场景，例如超大规模训练 |
| `msMonitor` 轻量化采集 | 采集关键性能指标，如利用率、带宽等，具有数据量小、解析快、开销低的特点，支持实时运行。 | 实时性能监控，以及大集群场景下的性能问题快速定界；适合发现资源瓶颈或异常，不用于算子级深度定位 |

### 性能数据类型说明

性能数据按层级进行划分，各类型数据的含义如下表所示。

| 数据类型 | 说明 |
|---|---|
| Python 调用栈 | 记录 Python 代码执行过程中的函数调用关系及耗时情况。 |
| AI 框架层 Trace | 记录 AI 框架（如 PyTorch）算子下发耗时。AI 框架层到 CANN 层构成第一级下发流水。 |
| CANN Trace | 包含 AscendCL、GE、Runtime 组件及 Node（算子）的耗时数据。CANN 层到 Device 构成第二级下发流水。 |
| Ascend Hardware | 底层 NPU 任务调度数据，记录 AI 任务运行时各 Task 在不同加速器上的执行耗时，以及 AI Core 性能指标。 |
| Communication | 记录各个通信域下的通信算子信息，包括通信带宽、数据传输量等。 |
| Overlap Analysis | 按 NPU 是否执行通信或计算任务进行划分，拆解为计算、通信、通信未与计算掩盖、空闲四个维度，用于评估计算与通信的并行效率。 |


## 相关入口

<style>
.grid.cards .md-typeset hr {
    width: 100%;
    margin: 0.5rem 0 1rem 0;
    border: none;
    height: 1px;
    background: linear-gradient(90deg,
        rgba(0,0,0,0.08) 0%,
        rgba(0,0,0,0.2) 40%,
        rgba(0,0,0,0.2) 60%,
        rgba(0,0,0,0.08) 100%);
}

.grid.cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
}

.grid.cards .card {
    height: 100%;
    display: flex;
    flex-direction: column;
}

.grid.cards .card hr {
    width: 100%;
}

[data-md-color-scheme="slate"] .grid.cards .md-typeset hr {
    background: linear-gradient(90deg,
        rgba(255,255,255,0.08) 0%,
        rgba(255,255,255,0.2) 40%,
        rgba(255,255,255,0.2) 60%,
        rgba(255,255,255,0.08) 100%);
}
</style>

<div class="grid cards" markdown>

-   **[新特性](../whats-new/)**

    ---

    汇总各工具最新版本的新增特性，掌握工具链最新动态。

-   **[msProf](../msprof/)**

    ---

    采集与解析 CANN 平台及昇腾 AI 处理器的软硬件性能数据。

-   **[PyTorch Profiler](../torch_npu_profiler/index.md)**

    ---

    基于PyTorch框架开发的昇腾软硬件性能调优工具。

-   **[MSPTI](../mspti/)**

    ---

    面向昇腾设备的 Profiling API 集合。

-   **[msMonitor](../msmonitor/index.md)**

    ---

    面向昇腾集群场景的在线性能监控与动态采集工具。

-   **[msprof-analyze](../msprof-analyze/)**

    ---

    面向 AI 训练与推理场景的性能分析工具，具备性能比对、集群分析、专家建议等功能。

-   **[MindStudio Insight](../msinsight/)**

    ---

    面向昇腾场景的可视化性能分析工具，适合查看 Timeline、算子清单及瓶颈定位结果。

-   **[msAgent](../msagent/)**

    ---

    面向性能问题定位场景的智能 Agent 工具，可辅助开发者更快完成分析与归因。
 
- **[Profiling Cases](../profiling-cases/)**

    ---

    典型场景性能调优案例库。


</div>

