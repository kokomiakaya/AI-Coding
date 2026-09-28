"""贪吃蛇游戏（pygame-ce 编写）

运行方式：
    python snake_game.py

操作：
    方向键 / WASD  移动
    P 或 空格      暂停 / 继续
    回车           游戏结束后重新开始
    ESC            退出
"""

import json
import math
import os
import random
import sys

import pygame

# ---------- 常量 ----------
CELL = 24                      # 每格像素大小
COLS, ROWS = 28, 21            # 网格列数 / 行数
HUD_H = 64                     # 顶部信息栏高度
WIN_W, WIN_H = COLS * CELL, ROWS * CELL + HUD_H

FPS_BASE = 5                   # 初始速度（格/秒）
FPS_MAX = 15                   # 最快速度
SPEEDUP_EVERY = 5              # 每吃几个食物加速一次

# 颜色
BG = (255, 255, 255)           # 背景（白色）
GRID = (232, 234, 238)         # 网格线
SNAKE_HEAD = (110, 200, 90)    # 蛇头
SNAKE_BODY = (74, 160, 66)     # 蛇尾（身体做渐变）
FOOD = (235, 80, 80)           # 食物
LEAF = (150, 210, 100)         # 食物叶子
TEXT = (40, 44, 52)            # 主文字
DIM = (125, 131, 142)          # 次要文字
OVERLAY_TEXT = (235, 238, 242)  # 遮罩层文字（遮罩是深色的）

# 按键 -> 方向
DIRS = {
    pygame.K_UP: (0, -1), pygame.K_w: (0, -1),
    pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1),
    pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0),
    pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
}

SCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.json")


def load_font(size: int) -> pygame.font.Font:
    """加载支持中文的字体（Windows 上优先使用微软雅黑）。"""
    for name in ("microsoftyahei", "msyh", "simhei"):
        path = pygame.font.match_font(name)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


class SnakeGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("贪吃蛇 Snake")
        self.clock = pygame.time.Clock()
        self.font_big = load_font(32)
        self.font_mid = load_font(22)
        self.font_small = load_font(16)
        self.high_score = self._load_high_score()
        self.reset()

    # ---------- 存档 ----------
    def _load_high_score(self) -> int:
        try:
            with open(SCORE_FILE, "r", encoding="utf-8") as f:
                return int(json.load(f).get("high_score", 0))
        except (OSError, ValueError, json.JSONDecodeError):
            return 0

    def _save_high_score(self):
        try:
            with open(SCORE_FILE, "w", encoding="utf-8") as f:
                json.dump({"high_score": self.high_score}, f)
        except OSError:
            pass

    # ---------- 游戏状态 ----------
    def reset(self):
        cx, cy = COLS // 2, ROWS // 2
        self.snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.direction = (1, 0)          # 当前移动方向
        self.pending = []                # 方向队列，防止快速按键导致 180° 掉头
        self.food = self.spawn_food()
        self.score = 0
        self.fps = FPS_BASE
        self.state = "playing"           # playing / paused / over
        self.win = False

    def spawn_food(self):
        """在蛇身以外的位置随机生成食物；棋盘占满时返回 None。"""
        free = [(x, y) for x in range(COLS) for y in range(ROWS)
                if (x, y) not in self.snake]
        return random.choice(free) if free else None

    # ---------- 输入 ----------
    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self._quit()
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self._quit()
                elif self.state == "playing":
                    if e.key in DIRS:
                        self._queue_dir(DIRS[e.key])
                    elif e.key in (pygame.K_p, pygame.K_SPACE):
                        self.state = "paused"
                elif self.state == "paused":
                    if e.key in (pygame.K_p, pygame.K_SPACE):
                        self.state = "playing"
                elif self.state == "over":
                    if e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                        self.reset()

    def _queue_dir(self, new):
        """把新方向放入队列：不能与参照方向相反，最多缓存两个。"""
        ref = self.pending[-1] if self.pending else self.direction
        if (new[0] + ref[0], new[1] + ref[1]) != (0, 0) and new != ref \
                and len(self.pending) < 2:
            self.pending.append(new)

    @staticmethod
    def _quit():
        pygame.quit()
        sys.exit()

    # ---------- 逻辑 ----------
    def update(self):
        if self.state != "playing":
            return
        if self.pending:
            self.direction = self.pending.pop(0)

        head = self.snake[0]
        nxt = (head[0] + self.direction[0], head[1] + self.direction[1])

        # 撞墙
        if not (0 <= nxt[0] < COLS and 0 <= nxt[1] < ROWS):
            self._game_over()
            return

        if nxt == self.food:
            # 吃到食物：只加头，不去尾，加速并刷新食物
            self.snake.insert(0, nxt)
            self.score += 1
            self.fps = min(FPS_MAX, FPS_BASE + self.score // SPEEDUP_EVERY)
            if self.score > self.high_score:
                self.high_score = self.score
            self.food = self.spawn_food()
            if self.food is None:  # 蛇占满棋盘，通关
                self._game_over(win=True)
                return
        else:
            # 咬到自己（蛇尾本回合会移走，允许追尾进入，所以排除最后一格）
            if nxt in self.snake[:-1]:
                self._game_over()
                return
            self.snake.insert(0, nxt)
            self.snake.pop()

    def _game_over(self, win=False):
        self.state = "over"
        self.win = win
        self._save_high_score()

    # ---------- 绘制 ----------
    def draw(self):
        self.screen.fill(BG)
        self._draw_hud()
        self._draw_grid()
        self._draw_food()
        self._draw_snake()

        if self.state == "paused":
            self._overlay("已暂停", "按 P 或空格继续")
        elif self.state == "over":
            title = "你赢了！" if self.win else "游戏结束"
            self._overlay(title, f"得分 {self.score}    按回车重新开始")
        pygame.display.flip()

    def _draw_hud(self):
        left = self.font_mid.render(f"得分: {self.score}", True, TEXT)
        right = self.font_mid.render(f"最高分: {self.high_score}", True, DIM)
        hint = self.font_small.render("方向键 / WASD 移动 · P 暂停 · ESC 退出", True, DIM)
        self.screen.blit(left, (16, (HUD_H - left.get_height()) // 2))
        self.screen.blit(right, right.get_rect(midright=(WIN_W - 16, HUD_H // 2)))
        self.screen.blit(hint, hint.get_rect(midbottom=(WIN_W // 2, HUD_H - 8)))

    def _draw_grid(self):
        for x in range(COLS + 1):
            pygame.draw.line(self.screen, GRID,
                             (x * CELL, HUD_H), (x * CELL, WIN_H))
        for y in range(ROWS + 1):
            pygame.draw.line(self.screen, GRID,
                             (0, HUD_H + y * CELL), (WIN_W, HUD_H + y * CELL))

    def _draw_food(self):
        if self.food is None:
            return
        cx = self.food[0] * CELL + CELL // 2
        cy = HUD_H + self.food[1] * CELL + CELL // 2
        # 半径随时间轻微脉动
        r = CELL // 2 - 5 + int(2 * math.sin(pygame.time.get_ticks() / 250))
        pygame.draw.circle(self.screen, FOOD, (cx, cy), max(4, r))
        pygame.draw.rect(self.screen, LEAF, (cx - 2, cy - r - 8, 4, 9),
                         border_radius=2)

    def _draw_snake(self):
        n = len(self.snake)
        for i, (x, y) in enumerate(self.snake):
            # 头部到尾部颜色渐变
            t = i / max(1, n - 1)
            color = tuple(int(SNAKE_HEAD[c] + (SNAKE_BODY[c] - SNAKE_HEAD[c]) * t)
                          for c in range(3))
            rect = pygame.Rect(x * CELL + 2, HUD_H + y * CELL + 2,
                               CELL - 4, CELL - 4)
            pygame.draw.rect(self.screen, color, rect, border_radius=8)

        # 蛇头眼睛，随移动方向转动
        hx, hy = self.snake[0]
        cx = hx * CELL + CELL // 2
        cy = HUD_H + hy * CELL + CELL // 2
        dx, dy = self.direction
        px, py = -dy, dx              # 垂直于移动方向
        off = CELL // 5
        fwd = CELL // 5
        for s in (-1, 1):
            ex = cx + px * off * s + dx * fwd
            ey = cy + py * off * s + dy * fwd
            pygame.draw.circle(self.screen, (255, 255, 255), (ex, ey), 4)
            pygame.draw.circle(self.screen, (20, 20, 20),
                               (ex + dx * 2, ey + dy * 2), 2)

    def _blit_center(self, text, font, y, color=TEXT):
        surf = font.render(text, True, color)
        self.screen.blit(surf, surf.get_rect(center=(WIN_W // 2, y)))

    def _overlay(self, title, subtitle):
        veil = pygame.Surface((WIN_W, WIN_H - HUD_H), pygame.SRCALPHA)
        veil.fill((10, 12, 18, 170))
        self.screen.blit(veil, (0, HUD_H))
        mid = HUD_H + (WIN_H - HUD_H) // 2
        self._blit_center(title, self.font_big, mid - 24, OVERLAY_TEXT)
        self._blit_center(subtitle, self.font_mid, mid + 24, OVERLAY_TEXT)

    # ---------- 主循环 ----------
    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(self.fps)


if __name__ == "__main__":
    SnakeGame().run()
