---
title: "核心模块"
description: "框架编排、生命周期管理、配置与插件系统。"
icon: "gear"
---

**`semantica.core`** 是框架的**协调层**：

- `Semantica` 编排器从 YAML 配置协调完整的知识图谱构建流水线
- `ConfigManager` 加载 YAML 配置，支持深度合并、校验和环境变量覆盖
- `PluginRegistry` 支持在运行时动态注册和加载组件
- `LifecycleManager` 管理启动/关闭，并提供健康监控与生命周期钩子

<Tip>
  绝大多数使用场景下，请直接使用各独立模块。只有在需要应用级生命周期管理、集中式配置或插件系统时，才使用 `semantica.core`。
</Tip>


## 你将获得

- **Semantica** — 高层编排器：从单个 `config.yaml` 协调完整的知识图谱构建流水线。应用级部署的入口点。
- **ConfigManager** — YAML 配置，支持深度合并、`SEMANTICA_` 环境变量覆盖和点号记法的嵌套键访问。将机密信息排除在源文件之外。
- **LifecycleManager** — 有序的启动/关闭钩子、健康监控，以及六状态状态机。对 FastAPI 应用等长期运行的服务至关重要。
- **PluginRegistry** — 注册自定义摄取器、解析器、导出器或任何组件。运行时按名称加载即可，无需导入。

## 导出的类

| 类 | 作用 |
| :--- | :--- |
| `Semantica` | 编排入口点：协调完整的知识图谱构建流水线 |
| `ConfigManager` | YAML 配置加载、深度合并、校验和环境变量覆盖 |
| `LifecycleManager` | 带健康监控和生命周期钩子的启动/关闭状态机 |
| `PluginRegistry` | 动态插件发现、注册与加载 |
| `method_registry` | 全局 `MethodRegistry` 实例：注册和调度自定义编排方法 |


## Semantica（编排）

**`Semantica`** 是高层入口点，负责协调**完整的知识图谱构建流水线**：

```python
from semantica.core import Semantica, ConfigManager

config_manager = ConfigManager()
config = config_manager.load_from_file("config.yaml")

framework = Semantica(config=config)
framework.initialize()

try:
    result = framework.build_knowledge_base(
        sources=["doc1.pdf", "doc2.docx"],
        embeddings=True,
        graph=True,
    )
    status = framework.get_status()
    print(f"State: {status['state']}")
finally:
    framework.shutdown(graceful=True)
```

### 核心方法

| 方法 | 说明 |
| :------ | :----------- |
| `initialize()` | 初始化所有框架组件 |
| `build_knowledge_base(sources, **kwargs)` | 编排完整的知识图谱构建流水线 |
| `run_pipeline(pipeline, data)` | 执行现有的 `Pipeline` 实例 |
| `get_status()` | 返回系统健康状况与当前状态 |
| `shutdown(graceful=True)` | 优雅关闭：等待进行中的操作完成 |

## ConfigManager

集中式配置加载，支持深度合并和环境变量覆盖：

```python
from semantica.core import ConfigManager

manager = ConfigManager()
config = manager.load_from_file("config.yaml")

# Merge base config with environment-specific overrides
merged = manager.merge_configs(
    manager.load_from_file("base.yaml"),
    manager.load_from_file("prod.yaml"),
)

# Nested key access with dot notation
batch_size = config.get("processing.batch_size", default=16)
config.set("processing.batch_size", 64)
config.validate()
```

### YAML 配置

```yaml
llm_provider:
  name: openai
  model: gpt-4o
  # Do not put API keys in YAML: use environment variables instead.
  # ConfigManager loads YAML with yaml.safe_load(), which does not
  # interpolate ${...} expressions. Set secrets via env vars (see below).

processing:
  batch_size: 32
  max_workers: 4

quality:
  min_confidence: 0.7

logging:
  level: INFO
```

环境变量覆盖（前缀 `SEMANTICA_`）：

使用双下划线（`__`）生成嵌套键访问所需的点号分隔符。实现会去除 `SEMANTICA_` 前缀、将结果转为小写，并把 `__` 替换为 `.`，然后再对配置字典调用 `set_nested_value()`。

```bash
# Double underscores map to nested keys:
export SEMANTICA_LLM_PROVIDER__MODEL=gpt-4o
export SEMANTICA_LLM_PROVIDER__NAME=openai
export SEMANTICA_PROCESSING__BATCH_SIZE=64
export SEMANTICA_QUALITY__MIN_CONFIDENCE=0.8
export SEMANTICA_LOGGING__LEVEL=DEBUG
```

## LifecycleManager

通过明确定义的状态机和有序的启动/关闭钩子来管理框架状态：

**状态机：** `UNINITIALIZED` → `INITIALIZING` → `READY` → `RUNNING` → `STOPPING` → `STOPPED`

```python
from semantica.core import LifecycleManager

manager = LifecycleManager()

def init_db():
    print("Initializing database...")

def cleanup_db():
    print("Closing database connections...")

# Lower priority values run first during startup
# Higher priority values run first during shutdown
manager.register_startup_hook(init_db,     priority=10)
manager.register_shutdown_hook(cleanup_db, priority=10)

manager.startup()

# Component health monitoring
class DatabaseComponent:
    def health_check(self):
        return {"healthy": True, "message": "Connected"}

manager.register_component("database", DatabaseComponent())
summary = manager.get_health_summary()
# → {
#     "state": "ready",
#     "is_healthy": True,
#     "total_components": 1,
#     "healthy_components": 1,
#     "unhealthy_components": 0,
#     "last_check": 1234567890.0,
#     "components": {
#         "database": {"healthy": True, "message": "Connected", "timestamp": ...}
#     }
#   }

manager.shutdown(graceful=True)
```

## PluginRegistry

注册参与完整流水线的自定义组件：包括溯源追踪、重试策略和并行执行：

```python
from semantica.core import PluginRegistry

class MyPlugin:
    def initialize(self):
        print("Plugin initialized")

    def execute(self, data):
        return {"processed": True}

registry = PluginRegistry(plugin_paths=["./plugins"])
registry.register_plugin("my_plugin", MyPlugin, version="1.0.0")

plugin = registry.load_plugin("my_plugin", api_key="xxx")
result = plugin.execute("sample data")

for info in registry.list_plugins():
    print(f"{info['name']}: {info['version']}")
```

## MethodRegistry

注册自定义编排方法，并按名称调度它们：

```python
from semantica.core import method_registry
from semantica.core.methods import build_knowledge_base

def fast_kb_builder(sources, **kwargs):
    # Custom logic: skip embeddings for speed
    ...

method_registry.register("knowledge_base", "fast", fast_kb_builder)

result = build_knowledge_base(sources=["doc.pdf"], method="fast")
```

## 何时使用 Core 与独立模块

| 场景 | 推荐做法 |
| :-------- | :-------------------- |
| 单一提取任务 | `from semantica.semantic_extract import NERExtractor` |
| 构建知识图谱 | `from semantica.kg import GraphBuilder` |
| 多步骤流水线 | `from semantica.pipeline import Pipeline` |
| 应用级生命周期 + 配置 | `from semantica.core import Semantica, ConfigManager` |
| 自定义调度 / 插件 | `from semantica.core import method_registry, PluginRegistry` |

<Tip>
  只有在构建需要有序启动、健康检查和优雅关闭的长期运行应用（例如 FastAPI 服务）时，才使用 `Semantica` 和 `LifecycleManager`。对于脚本和 notebook，请直接使用各独立模块。
</Tip>

- [Pipeline](../../../docs/reference/pipeline) — 流水线执行与步骤编排。
- [Utils](/reference/utils) — Core 内部使用的共享工具。
- [入门指南](../getting-started) — 使用 Core 之前，先了解基础知识。
- [LLMs](/reference/llms) — 通过 ConfigManager 配置 LLM 提供商。
