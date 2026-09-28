# AI-Coding

AI 编程项目合集。

## 项目列表

- [黑马记账](heima-jizhang/README.md) —— Windows 桌面记账应用（Electron + Vue 3 + SQLite）

## 黑马记账

一款 **Windows 桌面记账应用**：记录每一笔收入和支出（人民币），支出支持两级分类，数据全部保存在本机，无需注册账号、不联网上传。

### 主要功能

- **记账**：记录支出（金额、日期、两级分类、备注）和收入（金额、日期、收入分类、备注），分类菜单带 emoji 图标
- **流水明细**：按月份查看全部账单，支持支出/收入筛选、修改、删除
- **月度统计**：本月收入 / 支出 / 结余汇总；支出分类占比（条形列表 + 环形饼图）
- **月度预算**：「发现」页设置每月总预算，实时显示本月支出进度、剩余额度与超支提示
- **本地存储**：数据保存在本机 SQLite 数据库文件，升级程序不丢账本

### 技术栈

Electron 44 · Vue 3 · Element Plus · ECharts · SQLite · TypeScript

详细文档见 [heima-jizhang/README.md](heima-jizhang/README.md)。
