## Git 协同工作流

### 分支策略

| 分支 | 用途 |
|---|---|
| `main` | 稳定发布版本，仅通过 PR 合入 |
| `dev` | 开发主线，所有功能分支合入此处 |
| `feature/<name>` | 新功能开发 |
| `fix/<name>` | Bug 修复 |
| `docs/<name>` | 文档更新 |

### 开发流程

```
1. 拉取最新代码
   git checkout dev
   git pull origin dev

2. 创建功能分支
   git checkout -b feature/ble-scanner

3. 开发 & 提交（小粒度提交）
   git add .
   git commit -m "feat: implement BLE scanner module"

4. 推送并创建 PR
   git push origin feature/ble-scanner
   → GitHub 上创建 Pull Request → dev

5. Code Review → 合并 → 删除功能分支
```

### Commit 规范

```
<type>: <简短描述>

type:
  feat     新功能
  fix      修复
  docs     文档
  refactor 重构
  style    格式调整
  test     测试
  chore    构建/依赖

示例:
  feat: add nearby user discovery via BLE
  fix: resolve chat session timeout logic
  docs: update MVP roadmap
```

### Pull Request 规范

- 标题清晰描述改动内容
- 描述中说明：改了什么 / 为什么改 / 如何测试
- 至少 1 人 Review 后合并
- 合并方式：Squash and Merge

### 发布流程

```
dev 稳定后 → 创建 PR 到 main → Review → 合并 → 打 Tag
git tag v0.1.0
git push origin v0.1.0
```

---

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/<org>/NotePassing.git
cd NotePassing

# 切到开发分支
git checkout dev

# Android: 用 Android Studio 打开 android-app/
# Server: cd server && pip install -r requirements.txt && uvicorn main:app
```

## 开发注意事项

- BLE 功能必须在 **真机** 上调试
- 每次只完成一个小模块，避免大范围改动
- 报错时将 Logcat + 错误栈 + 相关文件一起提交 Issue
- 敏感信息（API Key 等）使用 `.env`，不要提交到仓库

## .gitignore 要点

```
*.apk
*.keystore
local.properties
.env
build/
.gradle/
.idea/
```

---

## 协作规则

1. **不要直接推 main 或 dev**，一律走 PR
2. **冲突自己解决**：合并前先 `git pull origin dev --rebase`
3. **Issue 驱动**：开工前先建 Issue，PR 关联 Issue（`closes #12`）
4. **小步提交**：一个 commit 做一件事