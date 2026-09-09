# 安全策略

## 受支持的版本

我们积极为以下 Semantica 版本提供安全更新支持：

| 版本 | 是否支持 |
| ------- | ------------------ |
| 0.2.3   | :white_check_mark: |
| 0.2.2   | :white_check_mark: |
| 0.2.1   | :white_check_mark: |
| 0.2.0   | :white_check_mark: |
| 0.1.1   | :white_check_mark: |
| 0.1.0   | :white_check_mark: |
| < 0.1.0 | :x:                |

## 报告漏洞

我们非常重视安全漏洞。如果您发现安全漏洞，请按照以下步骤操作：

### 1. **请勿**创建公开的 GitHub Issue

安全漏洞应私下报告，以防被恶意利用。

### 2. 报告安全问题

创建 [GitHub 安全公告](https://github.com/semantica-agi/semantica/security/advisories/new)，或通过 `SUPPORT.md` 中列出的安全邮箱联系我们。

请包含以下信息：

- **漏洞类型**（例如 XSS、SQL 注入、身份验证绕过）
- **受影响的组件**（模块、函数或文件）
- **复现步骤**（详细描述或概念验证代码）
- **潜在影响**（攻击者可能做什么？）
- **建议的修复方案**（如果您有）
- **您的联系信息**（用于后续提问）

### 3. 响应时间表

- **初步响应**：严重问题 24 小时内；非严重问题 48 小时内
- **状态更新**：7 天内
- **解决方案**：取决于严重程度与复杂度

### 4. 披露政策

- 我们将在 48 小时内确认收到您的报告
- 我们将定期提供漏洞状态更新
- 修复后，我们将按您的意愿在安全公告中为您署名
- 我们将与您协调公开披露事宜

## 安全更新流程

1. **评估**：我们使用 CVSS 评分评估严重程度
2. **修复开发**：我们开发并测试修复方案
3. **发布**：我们发布安全更新
4. **公告**：我们在 GitHub 上发布安全公告
5. **通知**：我们通过适当的渠道通知用户

## 严重程度级别

### 严重
- 远程代码执行
- 身份验证绕过
- 数据泄露或暴露
- **响应时间**：立即（24 小时内）

### 高
- 权限提升
- 重大数据泄露
- 拒绝服务
- **响应时间**：7 天内

### 中
- 信息泄露
- 跨站脚本（XSS）
- CSRF 漏洞
- **响应时间**：30 天内

### 低
- 轻微信息泄露
- 违反最佳实践
- **响应时间**：下一个发布周期

## 已知安全注意事项

### 依赖项

我们定期更新依赖项以解决安全漏洞。但是，您应该：

- 保持依赖项为最新版本
- 查看我们依赖项的安全公告
- 使用 `pip-audit` 或 `safety` 等工具检查已知漏洞

### API 密钥与凭据

- **切勿将 API 密钥或凭据提交**到仓库
- 使用环境变量或安全的配置管理
- 定期轮换密钥
- 遵循最小权限访问原则

### 数据处理

- 处理不可信数据时要谨慎
- 校验并清理所有输入
- 数据库操作使用参数化查询
- 对公共 API 实施速率限制

### 网络安全

- 所有网络通信均使用 HTTPS
- 校验 SSL/TLS 证书
- 谨慎调用外部 API
- 实施适当的身份验证与授权

## CI/CD 供应链安全

Semantica 的构建与发布流水线针对 CI/CD 供应链攻击进行了显式加固——即 2026 年 3 月 LiteLLM/Trivy 事件背后的那类攻击：一个被攻破的第三方 Action 使用**可变标签**窃取了长期有效的发布令牌，随后恶意包被直接推送到 PyPI，全程未接触源代码仓库。下面的每一项控制措施都直接对应封堵该攻击链中的一个环节。

### 不可变的构建输入

- **风险**：标签（`@v4`、`@release/v1`）被被攻破的上游维护者或账户重新指向，会在不知不觉中改变每个使用方 CI 所运行的内容。
  **控制**：每个工作流中的每个第三方 GitHub Action 均固定到完整的 40 字符提交 SHA，人类可读的标签仅作为尾随注释保留（例如 `actions/checkout@3d3c42e... # v7`）。
- **风险**：SHA 固定值随时间与自身的注释脱节，或被拼写错误。
  **控制**：`verify-action-pins.yml` 对任何不是完整提交 SHA 的 `uses:` 引用执行失败关闭（能捕获新引入的可变标签，而不仅仅是审核现有的固定值）；它在每次工作流变更、每次推送到 `main` 时以及每周通过 GitHub API 解析所有固定的标签，若 SHA 不再与所声称的标签匹配则失败——无法解析的 API 查询会被视为失败，而不是静默跳过。
- **风险**：每次上游发布时，在 8 个工作流文件中手动重新固定约 15 个 Action，很容易出错。
  **控制**：Dependabot（`github-actions` 生态）会在 Action 发布时打开一个分组 PR，同时更新 SHA *和*标签注释——固定值永远无需手工编辑。

### 发布流水线（最高权限路径）

- **风险**：存放在仓库/组织机密中的长期有效 `PYPI_TOKEN` 可能被任何被攻破的步骤窃取。
  **控制**：PyPI 发布使用可信发布（OIDC）（`id-token: write`）——本仓库中不存在任何可供窃取的长期有效的 PyPI 凭据。
- **风险**：被攻破的 CI 运行在无人值守的情况下向 PyPI 发布。
  **控制**：发布作业仅在被保护的 `pypi` GitHub 环境中运行，并配有必需的人工评审者——每次发布都需要在 Actions 界面中手动批准后才可运行。
- **风险**：发布作业可能从任意分支/引用被触发。
  **控制**：`pypi` 环境的部署分支策略仅限于 `v*` 标签。
- **风险**：扫描器或无关作业继承了发布级别的凭据。
  **控制**：`release.yml` 在工作流级别设置 `permissions: contents: read`；`contents: write` / `id-token: write` / `attestations: write` 仅授予发布作业，绝不在工作流范围内开放。
- **风险**：两个标签推送同时竞争通过发布流水线。
  **控制**：`concurrency: group: release-${{ github.ref }}` 按标签串行化发布。
- **风险**：使用方无法验证 PyPI 上的 wheel 确实来自本仓库的 CI。
  **控制**：每次发布均通过 `actions/attest-build-provenance` 声明 SLSA 构建溯源，生成一份已签名、可验证的记录，标明产出该制品的确切提交与工作流运行（可使用 `gh attestation verify` 校验）。

### 仓库控制

- **风险**：未经评审或强制推送的更改进入 `main`。
  **控制**：`main` 要求 1 个批准的 PR 评审（新推送会使过时批准失效）、已解决的对话，并阻止强制推送和分支删除。
- **风险**：PR 在安全/CI 检查未通过的情况下合并。
  **控制**：合并要求 `build`、`Analyze Python`（CodeQL）和 `security-scan` 检查在严格模式下通过（检查必须针对最新的 `main` 重新运行）。
- **风险**：被攻破的扫描作业接触到机密或写访问权限。
  **控制**：扫描作业（`CodeQL`、`security-scan.yml`、`defender-for-devops.yml`）以只读、最小权限运行（通常仅 `contents: read` + `security-events: write`），且绝不与发布作业共享作业、环境或机密范围。
- **风险**：机密被意外提交。
  **控制**：GitHub 机密扫描和推送保护均已在仓库级别启用，在包含可识别凭据模式的推送落地到历史记录之前即予以拒绝。

## 自动化安全扫描

以下每项扫描都在 CI 中持续运行，而非仅在发布时：

- **CodeQL**（`security-and-quality` 查询包）——Python 源码：注入、不安全的反序列化等代码级漏洞类别。在 `codeql.yml` 中对每次向 `main` 的推送/PR 以及每周运行。
- **Bandit**——针对 Python 的安全反模式（硬编码机密、不安全的 `eval`/`pickle`、弱加密等）；CI 在出现任何 HIGH 严重级别发现时即失败。在 `security-scan.yml` 中对每次向 `main` 的推送/PR 以及每周两次运行。
- **Semgrep**（`p/security` 规则集）——跨语言的静态分析安全模式。在 `security-scan.yml` 中对每次向 `main` 的推送/PR 以及每周两次运行。
- **pip-audit**——PyPA 维护、OSV 支撑的漏洞数据库，与 Semantica 固定的依赖树交叉核对，包括可选的 LLM 提供商扩展（如 LiteLLM）；CI 在出现任何匹配项时即失败。在 `security-scan.yml` 中对每次向 `main` 的推送/PR 以及每周两次运行，并可通过 `workflow_dispatch` 按需触发。
- **Microsoft Defender for DevOps**（`eslint`、`templateanalyzer`、`terrascan`）——JavaScript/TypeScript 代码检查安全规则与基础设施即代码错误配置。在 `defender-for-devops.yml` 中对每次向 `main` 的推送/PR 以及每周运行。
- **Checkov**——Kubernetes、Helm、Dockerfile、GitHub Actions 和机密模式 IaC 扫描；结果上传到与 CodeQL 相同的 Security 选项卡。在 `defender-for-devops.yml` 中对每次向 `main` 的推送/PR 以及每周运行。
- **GitGuardian**——对每个拉取请求执行机密检测检查，作为 GitHub App 集成安装（而非仓库本地工作流）。在每个 PR 上运行。
- **GitHub 机密扫描 + 推送保护**——在已知凭据模式被推送之前予以阻止，并持续扫描现有历史记录。平台级别、持续运行。
- **Dependabot**——针对 Python、Docker 和 GitHub Actions 依赖的版本/安全 PR，在相关时分组以降低评审噪音。配置于 `.github/dependabot.yml`，对安全相关包每周运行，对文档依赖每月运行。
- **`verify-action-pins.yml`**——强制每个 Action 引用均为完整提交 SHA（对新引入的可变标签失败），并确认每个 SHA 仍与所声称的标签匹配。在每次工作流变更、每次推送到 `main` 以及每周运行。

所有生成 SARIF 的扫描器（CodeQL、Checkov、Microsoft Defender）都会将发现发布到仓库的 **Security → Code scanning alerts** 选项卡，从而跨工具形成单一的审计跟踪，而不是分散的逐工具报告。

### 在 fork 或下游部署中采用此安全姿态

希望自行部署 Semantica 实例、或为内部/受监管部署而 fork 它的团队，可以直接复用此安全姿态：

1. 保留 Dependabot 的 `github-actions` 生态条目——正是它让 SHA 固定值无需手动维护即可保持最新。
2. 如果您将仓库的 Actions 重新指向自己的镜像，请在重定向后重新运行 `verify-action-pins.yml`。
3. 如果要从 fork 发布您自己的 PyPI 包，请在 PyPI 上配置您自己的 Trusted Publishing 信任关系（Trusted Publishing 的作用范围限定于特定的 `owner/repo` + 工作流文件名），并配置带有您自己必需评审者的受保护环境——这些均无法从本仓库转移。
4. 分支保护、环境保护和仓库机密扫描是仓库*设置*，而非工作流文件——克隆或 fork 仓库**不会**复制它们。必须通过 GitHub 界面或 API 在新仓库上重新应用。
5. GitHub 机密扫描和推送保护同样是不会随 fork 转移的仓库设置——请在新仓库的 Security 设置下重新启用这两项，而不仅仅是 Dependabot。
6. GitGuardian 以 GitHub App 安装的形式运行，作用范围限定于本特定仓库，而非工作流文件——在新仓库单独安装该应用之前，fork 不会获得其任何机密检测覆盖。
7. `codeql.yml` 中的 CodeQL `upload-sarif` 步骤仅在仓库*未*启用 Default Setup 时才有实际意义（否则其设计为优雅跳过）——请检查新仓库当前启用的是 Default Setup 还是 Advanced Setup，并相应调整对 CodeQL 发现出现位置的预期。

## 依赖安全策略

### 定期更新

- 我们监控所有依赖项的安全公告
- 我们定期在我们的开发分支中更新依赖项
- 严重安全更新会向后移植到受支持的版本

### 报告依赖漏洞

如果您在我们的某个依赖项中发现漏洞：

1. 检查它是否已在上游报告
2. 如果它特别影响 Semantica，请向我们报告
3. 如有需要，我们将与上游维护者协调

### 安全扫描

我们使用自动化工具扫描漏洞：

- **Dependabot**：自动化依赖更新与安全警报
- **GitHub 安全公告**：漏洞跟踪
- **人工评审**：定期安全审计

## 用户最佳实践

1. **保持 Semantica 更新**：始终使用最新的稳定版本
2. **审查依赖项**：定期更新您的项目依赖项
3. **安全配置**：使用安全的默认值和正确的配置
4. **监控日志**：留意可疑活动
5. **报告问题**：发现潜在安全问题时，请及时报告

## 安全致谢

我们赞赏负责任的披露。帮助我们提升 Semantica 安全性的安全研究人员将：

- 在安全公告中获得致谢（按您的意愿）
- 列入我们的安全致谢名单
- 因他们的贡献而获得认可

## 联系

如有与安全相关的问题或疑虑：

- **私人报告**：请勿在公开 Issue 中报告漏洞。
- **GitHub 安全公告**：[报告漏洞](https://github.com/semantica-agi/semantica/security/advisories/new)

## 其他资源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python 安全最佳实践](https://python.readthedocs.io/en/latest/library/security.html)
- [GitHub 安全最佳实践](https://docs.github.com/en/code-security)

---

**感谢您帮助维护 Semantica 及其用户的安全！**
