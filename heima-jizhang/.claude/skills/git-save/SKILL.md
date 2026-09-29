---
name: git-save
description: 提交存档：把当前改动存入 git（add + commit），提交前自检质检标记是否齐全有效。当用户要求「提交」「存档」「commit」或输入 /git-save 时使用。
---

# 提交存档技能（git-save）

把当前改动存进 git 存档点（git add + git commit）。提交会经过「提交闸门」检查：没有合格的质检标记会被拦下。

## 步骤

### 1. 查看当前改动
- `git status`，把改动清单展示给用户（新增 / 修改 / 删除分清楚）

### 2. 自检质检标记（先于提交的预检）
- 检查 `.claude/checks/unit-test.txt` 和 `.claude/checks/quality.txt` 都存在
- 两份标记第 1 行都是 `PASS`
- 两份标记第 2 行的指纹都与当前工作区一致：执行 `node .claude/scripts/commit-gate.mjs fingerprint`，与标记第 2 行逐字比对
- **有任何一条不过 → 停止提交**，把不过的原因用中文转达给用户，并建议：说「提交」让 gitcommit-agent 走完整质检流程
- 绝不使用 `git commit --no-verify` 绕过闸门

### 3. 存档
- `git add -A`
- `git commit -m "说明"`：提交说明用一句中文，风格参考历史提交（如「M8：v0.3.0 —— 新增贪吃蛇游戏页（代码审查通过）」；工具链类改动可写「工具：提交闸门与质检流程」）
- 提交若被闸门拦截：读取拦截信息里的中文原因，转达给用户，不擅自绕过

### 4. 报告
- 报告存档结果：提交编号（git log 前 7 位）、提交说明、改了哪些文件
- 提醒：上传 GitHub 不包含在本技能内，按 CLAUDE.md 第 11 节步骤单独进行

### 5. 收尾：删除质检标记
- 提交成功后，删除 `.claude/checks/unit-test.txt` 和 `.claude/checks/quality.txt`（标记去留规则：提交成功后自动删，用户 2026-09-29 拍板；质检失败时不会走到提交，标记自然保留作修复依据）
- 标记文件已被 .gitignore 排除，从不进版本库
