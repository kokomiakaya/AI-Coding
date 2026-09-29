# 黑马记账（Heima Jizhang）

![Electron](https://img.shields.io/badge/Electron-44-47848F?logo=electron&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3.5-42b883?logo=vue.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178c6?logo=typescript&logoColor=white)
![Element Plus](https://img.shields.io/badge/Element_Plus-2.14-409eff)
![ECharts](https://img.shields.io/badge/ECharts-6.1-aa344d)
![License](https://img.shields.io/badge/license-MIT-green)

一款 **Windows 桌面记账应用**：记录每一笔收入和支出（人民币），支出支持两级分类，数据全部保存在本机，无需注册账号、不联网上传。

> 本应用由 AI 辅助开发（Claude Code），从需求讨论、技术选型到编码测试全流程协作完成，开发过程与决策记录见 [CLAUDE.md](CLAUDE.md)。

## ✨ 主要功能

### 📝 记账
- 记一笔**支出**：金额（元，最多两位小数）、日期、两级分类（10 个一级大类 + 41 个二级小类，带 emoji 图标）、可选备注
- 记一笔**收入**：金额、日期、收入分类（6 类）、可选备注
- 记账页顶部实时显示**本月结余**

### 📋 流水明细
- 按时间倒序展示全部账单，支出/收入颜色区分
- 按月份、收支类型筛选
- 支持修改、删除（删除需二次确认）

### 📊 月度统计
- 本月总收入 / 总支出 / 结余汇总
- 支出分类占比：条形列表 + 环形饼图（ECharts）

### 🎯 月度预算
- 「发现」页设置每月固定预算
- 实时显示本月支出进度条、剩余额度与超支提示

### 🎮 游戏彩蛋
- 「游戏」页内置网页版贪吃蛇：方向键 / WASD 操作、P/空格暂停、回车重开
- 支持加速机制，最高分保存在本机

### 🔒 数据安全
- 数据保存在本机 **SQLite** 数据库文件（Windows 应用数据目录），与程序分离，升级不丢账本
- 不联网、不上传、无需注册——账本完全属于你自己

## 🛠 技术栈

| 类别 | 技术 | 说明 |
|---|---|---|
| 桌面框架 | **Electron 44** | 用网页技术构建 Windows 桌面应用 |
| 界面框架 | **Vue 3**（组合式 API） | 响应式 UI |
| 组件库 | **Element Plus** | 中文资料丰富、开箱即用 |
| 图表 | **ECharts 6** | 支出构成饼图等统计图表 |
| 开发语言 | **TypeScript 5** | 全栈类型安全 |
| 数据存储 | **SQLite**（Node 内置 `node:sqlite`） | 单文件数据库，零外部依赖 |
| 构建工具 | **electron-vite** | Electron + Vue 的标准构建方案 |
| 打包发布 | **electron-builder**（NSIS） | 生成 Windows 安装包（中文安装向导） |
| 单元测试 | **Vitest** | 25 项测试覆盖分类表与贪吃蛇规则引擎 |

## 🏗 项目结构

```
src/
├── main/                      # 主进程（应用管家）
│   ├── index.ts               # 创建窗口、注册数据接口
│   └── db.ts                  # SQLite 数据库（bills 账单表 + settings 设置表）
├── preload/                   # 预加载脚本（传话筒）
│   └── index.ts               # 把主进程接口包装成 window.api，隔离渲染层与数据库
├── renderer/src/              # 渲染层（界面）
│   ├── pages/                 # 5 个页面：记账 / 明细 / 统计 / 发现 / 游戏
│   ├── data/categories.ts     # 分类表（10 大类 + 41 小类，含 emoji 图标）
│   ├── game/snake-engine.ts   # 贪吃蛇纯规则引擎（界面只负责画）
│   └── App.vue                # 主布局（侧边栏 + 页面路由）
└── shared/types.ts            # 主进程与渲染层共用的数据类型
```

数据流动方向：

```
页面 → window.api.xxx → IPC 通道（bill:* / budget:* / game:*）
→ 主进程 index.ts 对应接口 → db.ts → SQLite
```

## 🚀 快速开始

```bash
npm install        # 安装依赖
npm run dev        # 开发模式运行
npm run typecheck  # 类型检查
npx vitest run     # 运行单元测试
npm run build:win  # 打包 Windows 安装包
```

> 国内网络环境下开发 / 打包的镜像配置，见 [CLAUDE.md](CLAUDE.md) 第 9 节「开发注意事项」。

## 📦 当前版本

**v0.3.1**（2026-09-29）—— 发布形态：Windows 安装版（约 125MB，双击安装，可自选安装目录，无需管理员权限）

## 📜 版本历史

### v0.3.1（2026-09-29 发布）

工程工具链版本：产品功能无变化、无新安装包。

- 新增：单元测试（Vitest）—— 25 项测试覆盖分类表与贪吃蛇规则引擎；贪吃蛇玩法规则抽取为独立引擎 `snake-engine.ts`（界面只负责画）
- 新增：Claude Code 工程工具链 —— 代码审查员、质量工程师、提交专员三位专员；单元测试、安全审查、注释审查、提交存档四个技能
- 新增：提交闸门 —— 提交前必须通过「单元测试 + 质量检查」，否则拒绝提交并报告原因
- 修正：文档中二级小类数量 46 → 41（与代码实际一致）

### v0.3（2026-09-28 发布）

- 新增：「游戏」页内置网页版贪吃蛇（JS + Canvas 重写 Python 版玩法：加速机制、暂停、最高分存本机）
- 优化：棋盘浅色底 + 深色网格线（用户反馈深色背景看不清网格后调整）

### v0.2（2026-09-28 发布）

- 新增：发现页 —— 设置固定每月预算、显示本月支出进度、剩余额度与超支提示
- 新增：记账页支出分类菜单 emoji 图标（10 个一级大类 + 41 个二级小类）
- 优化：医疗健康 💊→🩺、人情往来 🎁→🤝（避免与小类图标重复）；侧边栏新增「发现」菜单

### v0.1（2026-09-27 发布）

- 新增：记账（支出 / 收入 + 两级分类）
- 新增：流水明细（按月份查看、支出/收入筛选、修改、删除）
- 新增：月度统计（本月收入 / 支出 / 结余汇总 + 分类占比条形列表 + 环形饼图）
- 新增：打包为 Windows 安装版（中文安装向导）

## 🔮 规划中

- 数据备份与导出 Excel
- 超支主动提醒（打开应用时弹出）
- 年度统计报表
- 自定义分类

## 📚 相关文档

- [CLAUDE.md](CLAUDE.md) —— 产品文档、协作规则、分类体系、技术决策记录、踩坑记录
