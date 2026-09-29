// 贪吃蛇游戏规则（纯逻辑引擎）
// 只负责规则计算：怎么走、怎么吃、怎么结束；不碰界面、不碰计时器
// 由游戏页 SnakeGamePage.vue 调用，本文件可独立做单元测试

export interface Point {
  x: number
  y: number
}

export const CELL = 24 // 每格像素
export const COLS = 28 // 网格列数
export const ROWS = 21 // 网格行数
export const FPS_BASE = 5 // 初始速度（格/秒）
export const FPS_MAX = 15 // 最快速度
export const SPEEDUP_EVERY = 5 // 每吃几个食物加速一次

export type OverReason = 'wall' | 'self' | 'boardFull'

export interface SnakeState {
  snake: Point[] // 蛇身，第 0 节是头
  dir: Point // 当前移动方向
  nextDir: Point // 缓冲方向：一帧内只能改一次，防止瞬间掉头
  food: Point
  score: number
  over: boolean
  overReason: OverReason | null
}

/** 初始局面：中间偏左、3 节、向右（与 Python 版一致） */
export function createInitialState(rng: () => number = Math.random): SnakeState {
  const state: SnakeState = {
    snake: [
      { x: 14, y: 10 },
      { x: 13, y: 10 },
      { x: 12, y: 10 }
    ],
    dir: { x: 1, y: 0 },
    nextDir: { x: 1, y: 0 },
    food: { x: 0, y: 0 },
    score: 0,
    over: false,
    overReason: null
  }
  state.food = randomFreeCell(state.snake, rng)
  return state
}

/** 当前速度：每吃 SPEEDUP_EVERY 个食物加速一档，最快 FPS_MAX 格/秒 */
export function speedFpsFor(score: number): number {
  return Math.min(FPS_BASE + Math.floor(score / SPEEDUP_EVERY), FPS_MAX)
}

/** 两个方向是否完全相反（180° 掉头） */
export function isOpposite(a: Point, b: Point): boolean {
  return a.x === -b.x && a.y === -b.y
}

/** 尝试转向：以当前实际方向为准拒绝掉头，防止一帧内连按两键完成掉头 */
export function tryTurn(state: SnakeState, want: Point): void {
  if (isOpposite(want, state.dir)) return
  state.nextDir = want
}

/** 随机找一个不在蛇身上的空格 */
export function randomFreeCell(snake: Point[], rng: () => number = Math.random): Point {
  while (true) {
    const p = { x: Math.floor(rng() * COLS), y: Math.floor(rng() * ROWS) }
    if (!snake.some((s) => s.x === p.x && s.y === p.y)) return p
  }
}

export interface StepResult {
  ate: boolean // 这一步是否吃到了食物
  over: boolean
  overReason: OverReason | null
}

/** 走一步（核心规则）：撞墙 / 咬到自己 / 占满棋盘则结束；吃到食物得分并加速 */
export function step(state: SnakeState, rng: () => number = Math.random): StepResult {
  if (state.over) return { ate: false, over: true, overReason: state.overReason }

  state.dir = state.nextDir
  const head = { x: state.snake[0].x + state.dir.x, y: state.snake[0].y + state.dir.y }

  // 撞墙
  if (head.x < 0 || head.x >= COLS || head.y < 0 || head.y >= ROWS) {
    state.over = true
    state.overReason = 'wall'
    return { ate: false, over: true, overReason: 'wall' }
  }
  // 咬到自己
  if (state.snake.some((s) => s.x === head.x && s.y === head.y)) {
    state.over = true
    state.overReason = 'self'
    return { ate: false, over: true, overReason: 'self' }
  }

  state.snake.unshift(head)
  const ate = head.x === state.food.x && head.y === state.food.y
  if (ate) {
    state.score += 1
    if (state.snake.length >= COLS * ROWS) {
      // 蛇占满整个棋盘（几乎不可能达到）：直接结算，避免找空位陷入死循环
      state.over = true
      state.overReason = 'boardFull'
      return { ate: true, over: true, overReason: 'boardFull' }
    }
    state.food = randomFreeCell(state.snake, rng)
  } else {
    state.snake.pop()
  }
  return { ate, over: false, overReason: null }
}
