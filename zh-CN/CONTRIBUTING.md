# 为 Semantica 做贡献

感谢您对贡献本项目的兴趣！每一份贡献，无论多么微小，都很有价值。🎉

⭐ **给我们点个 Star** • 🍴 **[Fork Semantica](https://github.com/semantica-agi/semantica/fork)** • 💬 **加入我们的 [Discord](https://discord.gg/sV34vps5hH)**

> **初次贡献？** 从一个 [`good first issue`](https://github.com/semantica-agi/semantica/labels/good%20first%20issue) 开始，或加入我们的 [Discord](https://discord.gg/sV34vps5hH) 社区。

---

## 🚀 快速上手

1. 找一个 [`good first issue`](https://github.com/semantica-agi/semantica/labels/good%20first%20issue)
2. [Fork Semantica](https://github.com/semantica-agi/semantica/fork) 并克隆仓库
3. 进行你的修改
4. 提交一个 pull request！

**需要帮助？** 加入 [Discord](https://discord.gg/sV34vps5hH) 或 [GitHub Discussions](https://github.com/semantica-agi/semantica/discussions)

---

## 🗂️ 处理现有 Issue

如果你想处理一个开放的 GitHub issue，请遵循以下步骤，以保持协调并避免重复劳动：

1. **查看 issue。** 查看该 issue 的指派对象（assignees）和最近的评论。如果已经有人在积极处理它，请考虑选择其他 issue，或在评论中询问是否欢迎帮忙。

2. **若希望保留该 issue，请留言。** 留下类似 *"I'd like to take this on"* 的评论是获得指派的最快方式，但并非必需——维护者也可以直接将该 issue 指派给某个贡献者（例如，根据其最近在仓库中的活动），而无需等待评论。

3. **等待指派。** 无论是否留言，维护者都会在适当时机指派该 issue。在投入大量时间实现之前，请先等待指派，因为优先级和方案可能会变化。

4. **创建分支并实现。** 获得指派后，fork 仓库（如果尚未 fork），创建一个专有分支，然后开始你的工作。

   ```bash
   git checkout -b fix/short-description   # or feature/short-description
   ```

5. **提交一个聚焦的 PR 并关联 issue。** 准备好后，打开一个 pull request，并在描述中引用该 issue（例如 `Closes #123`）。请保持 PR 的范围仅限于该 issue 中描述的工作。

> **为什么这很重要：** 指派（无论是否留言）帮助维护者跟踪谁在做什么，并防止两位贡献者各自独立解决同一个问题。这也让你有机会在写代码之前就预期方案达成一致。

不确定从哪里开始？试试 [`good first issue`](https://github.com/semantica-agi/semantica/labels/good%20first%20issue) 或在 [Discord](https://discord.gg/sV34vps5hH) 中提问。

---

## 🔀 重复 PR 与 Issue 优先级

当多个 pull request 针对同一个 issue 时，维护者按以下优先级顺序进行分诊（triage）。这些规则用于裁决那些本应遵循[上面的指派流程](#-working-on-an-existing-issue)的 PR——在获得指派之前就打开 PR 本身并不会获得优先级，而且一旦其他人被指派到该 issue，一个未指派的 PR 仍可能作为重复 PR 被关闭。

1. **贡献者提出 issue 且已有对应 PR。** 如果提出该 issue 的人同时也为它打开了 PR，则该 PR 获得优先（在合并之前，他们仍需被指派）。
2. **维护者提出 issue 且已有认领评论。** 如果该 issue 是由我们提出的，并且有人评论表示希望处理它，我们会将其指派给他们，并在查看同一 issue 的任何其他 PR 之前先检查他们的 PR。
3. **没有先前的指派或评论。** 如果存在多个 PR，且没有人先被指派或认领该 issue，则优先级归于在过去 60 天内与仓库互动最持续的贡献者（例如，合并的 PR、实质性的评审或参与 issue 分诊）——而不仅仅是 PR 数量。
4. **迟到的重复 PR。** 如果在另一个贡献者已被指派到该 issue 之后才打开 PR，我们会尽早关闭这个重复 PR，而不是任其保持打开，并引导作者转向另一个开放的 issue（或请他们查看 `main` 分支上新打开的 issue）。这可以避免贡献者花时间更新一个不会被合并的 PR。
5. **范围重叠。** 如果一个 PR 涉及多个 issue，或者相互竞争的 PR 之间存在实质性的范围重叠，维护者会在 [Discord](https://discord.gg/sV34vps5hH) 上讨论后再做决定，而不是单方面处理。

**为什么这很重要：** 这使分诊过程可预期，避免贡献者在不会合并的 PR 上浪费精力，并有助于留住活跃的贡献者。

---

## 🎯 贡献方式

### 💻 代码

**你可以做：**
- 修复 bug
- 添加新功能
- 提高代码质量（添加类型注解、docstrings、改进错误消息）
- 优化性能

**位置：** `semantica/` 目录

**适合新手的 issue：** 添加 docstrings、类型注解，或改进错误消息

---

### 📝 文档

**你可以做：**
- 修复拼写和语法错误
- 提高清晰度和可读性
- 添加代码示例和教程
- 创建新的 cookbook 笔记本
- 改进 API 文档（docstrings）
- 创建故障排查指南
- 更新安装说明
- 补充缺失的文档

**位置：** `README.md`、`docs/`、`cookbook/`、代码中的 docstrings

**适合新手的 issue：** 修复错别字、添加示例、创建 cookbook 教程、改进 docstrings

**文档格式：**
- 使用清晰、简洁的语言
- 在有助于理解的地方包含代码示例
- 遵循 markdown 最佳实践
- 使用正确的标题层级
- 添加指向相关章节的链接
- 为 UI 相关文档添加截图

---

### 🧪 测试

**你可以做：**
- 添加单元测试
- 提高测试覆盖率
- 添加集成测试

**位置：** `tests/` 目录

**适合新手的 issue：** 为特定函数或类添加测试

---

### 🐛 Bug 报告

**内容：** 报告你发现的 bug

**方式：** 使用 [bug 报告模板](https://github.com/semantica-agi/semantica/issues/new?template=bug_report.md)

**包含：** 描述、复现步骤、预期与实际行为、环境详情

---

### 💡 功能请求

**内容：** 建议新功能或改进

**方式：** 使用[功能请求模板](https://github.com/semantica-agi/semantica/issues/new?template=feature_request.md)

**包含：** 问题描述、建议方案、使用场景

---

### 🎨 Cookbook 与示例

**内容：** 创建教程和示例

**位置：** `cookbook/` 目录

**示例：** 创建新的笔记本，添加示例，改进现有教程

---

### 💬 社区支持

**内容：** 帮助社区中的其他人

**位置：** [Discord](https://discord.gg/sV34vps5hH)、[GitHub Discussions](https://github.com/semantica-agi/semantica/discussions)

**示例：** 回答问题、评审 PR、分享你的项目

---

### 🎓 教育内容

**内容：** 创建教育材料

**示例：** 博客文章、视频教程、演讲、工作坊、案例研究

---

### 🔧 其他贡献

- **设计与图形：** 标志、图表、可视化
- **工具与集成：** CLI 工具、与其他框架的集成
- **基础设施：** CI/CD 改进、Docker 优化
- **安全：** 报告安全漏洞（私下报告）

---

## 📋 开始贡献

### 1. Fork 与克隆

首先，在 GitHub 上 [fork Semantica](https://github.com/semantica-agi/semantica/fork)，然后：

```bash
git clone https://github.com/your-username/semantica.git
cd semantica
git remote add upstream https://github.com/semantica-agi/semantica.git
```

### 2. 配置环境

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (optional)
pre-commit install
```

### 锁定的 CI 依赖

`requirements-ci.txt` 将每个传递依赖都锁定在精确版本，使 CI、安全扫描和发布构建每次运行时都安装相同的软件包（相当于 Python 版的 `explorer/package-lock.json` + `npm ci`）。它是一个**独立的构建环境**：每个软件包都带有 SHA-256 哈希（`--generate-hashes`），因此安装是可复现的且供应链安全——切勿从它安装到你的本地开发环境中。

在更改 `pyproject.toml` 中的依赖后重新生成它：

```bash
pip install uv==0.12.1
uv pip compile pyproject.toml --python-version 3.11 --extra all --generate-hashes -o requirements-ci.txt
```

`all` extra 是该仓库的跨平台依赖集（`faiss-gpu`/`cupy` 等 GPU extra 被排除在外，并在 Linux 上单独安装——参见 `pyproject.toml`）。请保持锁定的 `uv` 版本与 CI 同步，以便重新生成的结果是确定性的。

CI 的过期检查以已提交的 lockfile 作为约束重新解析，并且只比较版本行：上游软件包的新发布永远不会导致 CI 失败——lockfile 只在 `pyproject.toml` 被有意更改时才发生变化。

如果 `requirements-ci.txt` 相对于 `pyproject.toml` 已过期，CI 将失败（版本行比较能检测到新增、移除或变更的依赖）。

构建系统锁定：`[build-system].requires` 被锁定到精确版本（`setuptools==84.0.0`、`wheel==0.48.0`），发布构建针对 lockfile 运行 `python -m build --no-isolation`——任何地方都不存在未锁定的构建时隔离。

### 3. 创建分支

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 4. 进行修改

- 遵循代码风格（见下文）
- 为新功能添加测试
- 更新文档

### 5. 运行检查

```bash
pytest                          # Run tests
black semantica/ tests/        # Format code
isort semantica/ tests/         # Sort imports
flake8 semantica/ tests/        # Lint
```

或使用 pre-commit 钩子：`pre-commit run --all-files`

### 6. 提交与推送

```bash
git commit -m "feat(module): add new feature"
git push origin feature/your-feature-name
```

然后在 GitHub 上创建 pull request！

---

## 📐 代码风格

我们使用自动化工具：

| 工具     | 用途                    | 命令                    |
|----------|----------------------------|----------------------------|
| **Black** | 代码格式化            | `black semantica/ tests/` |
| **isort** | 导入排序             | `isort semantica/ tests/` |
| **flake8** | 风格强制          | `flake8 semantica/ tests/` |
| **mypy** | 类型检查              | `mypy semantica/`          |

**全部运行：** `black semantica/ tests/ && isort semantica/ tests/ && flake8 semantica/ tests/ && mypy semantica/`

---

## 🧪 测试

```bash
pytest                          # Run all tests
pytest --cov=semantica         # With coverage
pytest tests/test_file.py      # Specific file
```

**覆盖率目标：** 最低 80%，关键模块 90% 以上

---

## 📝 提交消息

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
feat(kg): add temporal graph support
fix(parse): handle empty PDF files
docs(readme): add installation guide
test(extract): add unit tests
```

**类型：** `feat`、`fix`、`docs`、`test`、`refactor`、`perf`、`style`、`chore`

---

## ✅ PR 检查清单

提交之前：

- [ ] 代码遵循风格规范
- [ ] 测试在本地通过
- [ ] 已添加新测试（如适用）
- [ ] 文档已更新
- [ ] 提交消息遵循规范
- [ ] 没有合并冲突

---

## 📖 文档标准

### 代码文档（Docstrings）

**格式：** 使用 Google 风格的 docstrings

```python
def extract_entities(text: str, model: str = "transformer") -> List[Entity]:
    """Extract named entities from text.
    
    Args:
        text: Input text to process
        model: NER model to use (default: "transformer")
    
    Returns:
        List of extracted Entity objects
    
    Raises:
        ValueError: If text is empty or model is invalid
    
    Example:
        >>> from semantica.semantic_extract import NERExtractor
        >>> ner = NERExtractor(method="ml", model="en_core_web_sm")
        >>> entities = ner.extract("Apple Inc. was founded in 1976.")
        >>> len(entities)
        2
    """
```

### Markdown 文档格式

**通用指南：**
- 使用清晰的标题（H1 用于标题，H2 用于主要章节，H3 用于小节）
- 保持段落简短且主题集中
- 使用项目符号列表
- 添加带语法高亮的代码块
- 包含指向相关文档的链接

**代码块：**
- 使用带有语言标识符的三重反引号：` ```python `、` ```bash `
- 在代码示例中加入注释
- 在有助于理解时展示预期输出

**示例：**

```markdown
## Section Title

Brief introduction paragraph.

### Subsection

- Bullet point 1
- Bullet point 2

**Code example:**

```python
from semantica import SomeClass

instance = SomeClass()
result = instance.method()
```

**Note:** Additional context or warnings.
```

**最佳实践：**
- 以概述/引言开头
- 使用一致的术语
- 包含"参见"（See also）链接
- 为复杂概念添加示例
- 保持各文档格式一致

---

## 🆘 获取帮助

- 💬 [Discord](https://discord.gg/sV34vps5hH) - 实时聊天
- 💭 [GitHub Discussions](https://github.com/semantica-agi/semantica/discussions) - 问答
- 🐛 [GitHub Issues](https://github.com/semantica-agi/semantica/issues) - Bug 报告

**提问之前：** 查看现有文档、搜索 issues/discussions、回顾 cookbook 示例

---

## 🏆 贡献者表彰

所有贡献者都将在以下位置被记录：
- [CONTRIBUTORS.md](CONTRIBUTORS.md)
- GitHub 贡献者页面
- 版本发布说明

我们遵循 [all-contributors](https://allcontributors.org) 规范！

---

## 📜 行为准则

本项目遵循[行为准则](CODE_OF_CONDUCT.md)。请保持尊重和包容。

---

## 📚 资源

- [README.md](../README.md) - 项目概览
- [Cookbook](../cookbook) - 教程和示例
- [Documentation](../docs) - 综合指南

---

**感谢你的贡献！** 🚀

每一份贡献都很重要——无论是一行代码、一个错别字修正、一次有帮助的回答，还是一个 bug 报告。我们感谢你！🙏

⭐ **给我们点个 Star** • 🍴 **[Fork Semantica](https://github.com/semantica-agi/semantica/fork)** • 💬 **加入我们的 [Discord](https://discord.gg/sV34vps5hH)**