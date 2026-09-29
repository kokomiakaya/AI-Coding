# AI-Coding

AI 编程项目合集。

## 项目列表

- [黑马记账](heima-jizhang/README.md) —— Windows 桌面记账应用（Electron + Vue 3 + SQLite）
- [贪吃蛇](snake/README.md) —— Python 贪吃蛇小游戏（pygame 图形窗口版）
- [LangChain RAG 知识库问答系统](langchain-rag-qa/README.md) —— 毕业设计：电商商品知识库智能问答（FastAPI + LangChain + Vue 3 + Chroma + SQLite）

## 黑马记账

一款 **Windows 桌面记账应用**：记录每一笔收入和支出（人民币），支出支持两级分类，数据全部保存在本机，无需注册账号、不联网上传。

### 主要功能

- **记账**：记录支出（金额、日期、两级分类、备注）和收入（金额、日期、收入分类、备注），分类菜单带 emoji 图标
- **流水明细**：按月份查看全部账单，支持支出/收入筛选、修改、删除
- **月度统计**：本月收入 / 支出 / 结余汇总；支出分类占比（条形列表 + 环形饼图）
- **月度预算**：「发现」页设置每月总预算，实时显示本月支出进度、剩余额度与超支提示
- **游戏彩蛋**：「游戏」页内置网页版贪吃蛇，方向键 / WASD 操作、加速机制，最高分存本机
- **本地存储**：数据保存在本机 SQLite 数据库文件，升级程序不丢账本

### 技术栈

Electron 44 · Vue 3 · Element Plus · ECharts · SQLite · TypeScript

详细文档见 [heima-jizhang/README.md](heima-jizhang/README.md)。

## 贪吃蛇

经典贪吃蛇小游戏，用 **Python + pygame** 编写的图形窗口版。

### 玩法

- 控制小蛇吃食物得分，蛇身变长；每吃 5 个食物加速一次，越吃越快
- 撞墙或咬到自己则游戏结束；最高分自动保存在本机
- 操作：方向键 / WASD 移动 · P 或空格暂停 · 回车重开 · ESC 退出

详细文档见 [snake/README.md](snake/README.md)。

## LangChain RAG 知识库问答系统

基于 **LangChain** 框架的企业级 RAG（检索增强生成）知识库问答系统，毕业设计项目。面向电商商品知识问答：用户通过浏览器提问，系统从知识库检索相关片段，生成**带引用来源**的流式回答。

### 主要功能

- **知识库管理**：多知识库 CRUD、文档上传（PDF/DOCX/TXT/MD/XLSX/CSV）、文本直接录入、后台异步解析入库、分块预览
- **流式问答**：SSE 逐字输出，回答标注 [1][2] 引用角标，点击定位来源卡片（文档名/页码/行号/相关度）
- **多用户多会话**：注册/登录/改密、会话历史持久化（跨登录找回）、多轮追问指代消解
- **管理后台**（admin 专属）：用户管理、统计看板（ECharts）、系统配置热更新、检索调试接口
- **防幻觉**：混合检索（向量 + BM25 中文全文检索）+ 重排 + 阈值过滤 + 引用校验，检索不到时拒绝编造

### 技术栈

FastAPI · LangChain · Vue 3 · Element Plus · Chroma · SQLite（FTS5）· ECharts · DeepSeek + 本地 BGE 嵌入

详细文档见 [langchain-rag-qa/README.md](langchain-rag-qa/README.md)。
