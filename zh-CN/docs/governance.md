---
title: "治理"
description: "项目治理模型：角色、决策流程、发布节奏与代码评审指南。"
icon: "scale-balanced"
---

> Semantica 由 Semantica 团队维护，并采用开放的治理模式，欢迎社区贡献。


## 角色

- **维护者**：Semantica 团队。负责审查并合并 PR、管理发布和代码质量、制定项目方向与社区标准。
- **贡献者**：提交代码、文档和 Bug 报告，协助处理 issue 与评审工作，并在 [CONTRIBUTORS.md](https://github.com/semantica-agi/semantica/blob/main/CONTRIBUTORS.md) 中获得致谢。
- **社区成员**：使用 Semantica，提供反馈，分享使用案例，并参与 GitHub Discussions 和 Discord。


## 决策流程

### 代码变更

<Steps>
  <Step title="提案">打开一个 GitHub Issue 来描述该变更。</Step>
  <Step title="讨论">社区就方案与范围展开讨论。</Step>
  <Step title="实现">提交包含该变更的拉取请求（pull request）。</Step>
  <Step title="评审">至少一名维护者评审该 PR。</Step>
  <Step title="合并">CI 通过且获得维护者批准后合并。</Step>
</Steps>

### 重大决策

- 在 GitHub Issues 中发布 RFC
- 至少 1 周的社区讨论期
- 维护者根据社区反馈和技术可行性作出决定


## 发布

Semantica 遵循**语义化版本控制**（`MAJOR.MINOR.PATCH`）：

| 级别 | 触发条件 | 节奏 |
| :------- | :--------- | :--------- |
| MAJOR | 破坏性变更 | 每季度或按需 |
| MINOR | 新功能（向后兼容） | 每月或就绪时 |
| PATCH | Bug 修复（向后兼容） | 随 Bug 修复发布 |


## 代码评审

**评审标准：** 功能性、代码质量、测试、文档、性能、安全性。

**时间线：** 首次评审在 48 小时内完成；后续跟进在 7 天内完成。

**评审者准则：** 保持建设性，说明理由，提出替代方案。

**贡献者准则：** 及时回应评审意见，遇到不清楚之处主动提问，对反馈保持开放态度。


## 沟通渠道

- **GitHub Issues**：Bug 报告、功能请求、问题咨询
- **GitHub PR**：代码贡献
- **GitHub Discussions**：社区交流
- **安全公告**：[私下报告安全问题](https://github.com/semantica-agi/semantica/security/advisories/new)


## 项目目标

- **易用性**：提供合理的默认配置、清晰的文档和最少的繁琐流程，易于使用和理解。
- **可靠性**：达到生产就绪的质量，并在多种 Python 版本、平台和真实场景工作负载下进行测试。
- **性能**：从单机 Notebook 到企业级图数据库，均保持高效且可扩展。
- **可扩展性**：通过 `PluginRegistry` 模式，可方便地使用插件和自定义模块进行扩展。
- **社区**：热情开放、兼容并包。欢迎各种背景和经验水平的贡献者，并认可他们的付出。


## 许可证

MIT 许可证：参见 [LICENSE](https://github.com/semantica-agi/semantica/blob/main/LICENSE) 和[许可证页面](/project-license)。


## 另请参阅

- [贡献](/contributing-guide)：如何提交变更。
- [社区](/community)：社区准则与沟通渠道。