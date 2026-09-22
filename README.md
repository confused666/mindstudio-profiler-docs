# mindstudio-profiler-docs

MindStudio Profiling Tools 文档托管仓库。

这个仓库用于聚合 Ascend 性能工具相关文档，并通过 MkDocs 统一对外提供站点。当前主要聚合的子工具包括：

- `msprof`：性能数据采集、导出与基础解析
- `mspti`：Profiling C API / Python API 接入
- `msmonitor`：在线监控、动态采集与运行时观测
- `msprof-analyze`：基于 Profiling 数据的分析、对比与调优定位
- `msinsight`：性能数据可视化分析
- `msagent`：面向 Ascend NPU 场景的性能问题定位 Agent
- `torch_npu_profiler`：PyTorch / `torch_npu` 场景的框架侧 Profiling（文档直接维护在本仓库，非子模块）

站点还包含本仓库手写维护的总览、指南、Profiling Cases 等页面。

## 目录说明

```text
.
├── readthedocs/
│   ├── docs/                          # MkDocs 文档根目录
│   │   ├── <tool>/                    # 由子模块自动生成，勿手工修改（已被 .gitignore 忽略）
│   │   ├── whats-new/                 # 由脚本自动生成（已被 .gitignore 忽略）
│   │   └── overview|guides|profiling-cases|torch_npu_profiler/  # 本仓库手写维护
│   ├── mkdocs.yml                     # MkDocs 配置（主题、i18n、插件、导航翻译）
│   ├── hooks.py                       # MkDocs 钩子：语言切换链接与英文页相对资源修正
│   ├── overrides/                     # 主题覆盖（关闭头部语言切换器）
│   ├── requirements.txt               # 文档依赖（范围约束）
│   ├── requirements.lock.txt          # 锁定版本，Read the Docs 实际安装此文件
│   └── scripts/
│       ├── build_docs.py              # 预构建：同步子工具文档、过滤、生成导航与首页
│       ├── fetch_release_notes.py     # 预构建：聚合 GitCode Releases 生成「新特性」页
│       ├── release_feature_docs.json  # 新特性条目 → 站内文档的「使用说明」映射表
│       └── release_notes_cache.json   # Releases 抓取失败时的回退缓存
├── .readthedocs.yaml                  # Read the Docs 构建配置
└── .gitmodules                        # 子模块配置
```

> 注意：`readthedocs/docs/` 下的工具目录与 `whats-new/` 都是构建期生成的，修改它们会在下次构建时被覆盖。
> 工具文档请到各自源码仓（`gitcode.com/Ascend/<tool>`）修改。

## 本地准备

建议使用 Python 3.10+。

先拉取仓库和子模块：

```bash
git clone --recurse-submodules <repo-url>
cd mindstudio-profiler-docs
git submodule sync --recursive
git submodule update --init --recursive
git submodule update --remote --recursive
```

安装文档依赖：

```bash
python3 -m pip install -r readthedocs/requirements.lock.txt
```

`requirements.txt` 只写范围约束，`requirements.lock.txt` 是锁定版本（Read the Docs 安装的就是它）。
调整依赖后需要重新生成锁定文件：

```bash
uv pip compile readthedocs/requirements.txt --python .venv/bin/python -o readthedocs/requirements.lock.txt
```

## 本地启动服务

本地预览前需要先执行一次预构建脚本。这个脚本会：

- 从各子工具仓库同步文档（会对每个子模块执行一次 `git fetch`，因此需要能访问 gitcode.com）
- 过滤需要展示的目录与页面
- 生成工具导航与首页入口
- 重写部分站内链接
- 抓取各工具 Releases，生成「新特性」（whats-new）页面（抓取失败时回退到 `scripts/release_notes_cache.json`）

执行命令：

```bash
python3 readthedocs/scripts/build_docs.py
```

然后启动本地服务：

```bash
mkdocs serve -f readthedocs/mkdocs.yml -a 127.0.0.1:8000
```

启动后浏览器访问：

```text
http://127.0.0.1:8000
```

如果 `8000` 端口已被占用，可以改成别的端口，例如：

```bash
mkdocs serve -f readthedocs/mkdocs.yml -a 127.0.0.1:8001
```

## 本地构建

如果只想检查能否成功构建静态站点，可以执行：

```bash
python3 readthedocs/scripts/build_docs.py
mkdocs build -f readthedocs/mkdocs.yml --strict
```

构建产物默认输出到：

```text
readthedocs/site/
```

## 与 RTD 的一致性

Read the Docs 上的构建流程定义在 [.readthedocs.yaml](.readthedocs.yaml)，主要步骤是：

1. 同步并更新子模块
2. 将子工具文档切到指定分支
3. 执行 `python readthedocs/scripts/build_docs.py`
4. 使用 `readthedocs/mkdocs.yml` 构建站点

本地调试时，建议尽量复用同样的顺序。

## 常见问题

### 1. `mkdocs serve` 提示 `Address already in use`

说明默认端口被占用了。可以：

- 结束占用 `8000` 端口的进程
- 或者直接换端口启动，例如 `8001`

### 2. 构建时出现锚点告警

例如：

- `contains a link '#xxx', but there is no such anchor on this page`
- `does not contain an anchor '#xxx'`

这类通常是文档内部链接与标题锚点不一致导致的，不一定会阻塞站点启动，但建议逐步修复。

### 3. 为什么修改了脚本但页面没变化

因为导航和聚合内容不是纯手写的，很多页面是在预构建阶段生成的。修改脚本后需要重新执行：

```bash
python3 readthedocs/scripts/build_docs.py
```

再运行 `mkdocs serve` 或 `mkdocs build`。
