# 贪吃蛇（Snake）

用 Python + pygame 编写的经典贪吃蛇小游戏（图形窗口版）。

## 玩法

- 控制小蛇吃食物，每吃一个得 1 分，蛇身变长
- 每吃 5 个食物加速一次，越吃越快
- 撞墙或咬到自己则游戏结束
- 最高分自动保存在本机 `highscore.json` 文件中

## 操作

| 按键 | 作用 |
|---|---|
| 方向键 / WASD | 移动 |
| P 或 空格 | 暂停 / 继续 |
| 回车 | 游戏结束后重新开始 |
| ESC | 退出游戏 |

## 运行方式

```bash
pip install pygame-ce   # 安装游戏图形库（只需一次）
python snake_game.py    # 启动游戏
```

> 依赖库使用 pygame-ce（pygame 的社区维护版），安装后代码中仍以 `pygame` 名称导入。
