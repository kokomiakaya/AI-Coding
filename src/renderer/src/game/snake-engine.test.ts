// 贪吃蛇游戏引擎的「零件质检」（单元测试）
// 运行：npx vitest run

import { describe, it, expect } from 'vitest'
import {
  COLS,
  ROWS,
  FPS_BASE,
  FPS_MAX,
  createInitialState,
  speedFpsFor,
  isOpposite,
  tryTurn,
  randomFreeCell,
  step
} from './snake-engine'

/** 固定随机源：依次返回给定的数（0~1），用完重复最后一个，保证测试结果可预测 */
function fixedRng(values: number[]): () => number {
  let i = 0
  return () => values[Math.min(i++, values.length - 1)]
}

describe('初始局面', () => {
  it('蛇应该有 3 节，头在中间偏左，向右移动', () => {
    const s = createInitialState(fixedRng([0.9, 0.9]))
    expect(s.snake).toHaveLength(3)
    expect(s.snake[0]).toEqual({ x: 14, y: 10 })
    expect(s.dir).toEqual({ x: 1, y: 0 })
    expect(s.score).toBe(0)
    expect(s.over).toBe(false)
  })

  it('食物应该落在棋盘内、且不在蛇身上', () => {
    const s = createInitialState(fixedRng([0.9, 0.9]))
    expect(s.food.x).toBeGreaterThanOrEqual(0)
    expect(s.food.x).toBeLessThan(COLS)
    expect(s.food.y).toBeGreaterThanOrEqual(0)
    expect(s.food.y).toBeLessThan(ROWS)
    expect(s.snake.some((p) => p.x === s.food.x && p.y === s.food.y)).toBe(false)
  })
})

describe('速度规则', () => {
  it('每吃 5 个食物加速一档，最快 15 格/秒封顶', () => {
    expect(speedFpsFor(0)).toBe(FPS_BASE)
    expect(speedFpsFor(4)).toBe(FPS_BASE)
    expect(speedFpsFor(5)).toBe(FPS_BASE + 1)
    expect(speedFpsFor(45)).toBe(FPS_MAX - 1)
    expect(speedFpsFor(50)).toBe(FPS_MAX)
    expect(speedFpsFor(100)).toBe(FPS_MAX)
  })
})

describe('移动规则', () => {
  it('没吃到食物：头向前一格，尾巴缩一格，长度不变', () => {
    const s = createInitialState(fixedRng([0.9, 0.9])) // 食物在 (25,18)，远离蛇
    const r = step(s)
    expect(r.ate).toBe(false)
    expect(r.over).toBe(false)
    expect(s.snake[0]).toEqual({ x: 15, y: 10 })
    expect(s.snake).toHaveLength(3)
    expect(s.score).toBe(0)
  })

  it('吃到食物：分数 +1、长度 +1、食物换到新位置', () => {
    // 初始食物放在蛇头前方 (15,10)；吃到后新食物由固定随机源指定为 (0,0)
    const rng = fixedRng([0.55, 0.5, 0, 0])
    const s = createInitialState(rng)
    const r = step(s, rng)
    expect(r.ate).toBe(true)
    expect(r.over).toBe(false)
    expect(s.score).toBe(1)
    expect(s.snake).toHaveLength(4)
    expect(s.food).toEqual({ x: 0, y: 0 })
  })

  it('撞右边墙：游戏结束', () => {
    const s = createInitialState(fixedRng([0.1, 0.1]))
    s.snake = [
      { x: 27, y: 5 },
      { x: 26, y: 5 },
      { x: 25, y: 5 }
    ]
    s.dir = { x: 1, y: 0 }
    s.nextDir = { x: 1, y: 0 }
    s.food = { x: 0, y: 0 }
    const r = step(s)
    expect(r.over).toBe(true)
    expect(r.overReason).toBe('wall')
  })

  it('撞上边墙：游戏结束', () => {
    const s = createInitialState(fixedRng([0.1, 0.1]))
    s.snake = [
      { x: 5, y: 0 },
      { x: 5, y: 1 },
      { x: 5, y: 2 }
    ]
    s.dir = { x: 0, y: -1 }
    s.nextDir = { x: 0, y: -1 }
    s.food = { x: 0, y: 0 }
    const r = step(s)
    expect(r.over).toBe(true)
    expect(r.overReason).toBe('wall')
  })

  it('咬到自己：游戏结束', () => {
    // 身体绕成一个圈，头向右走会撞到自己的第二节
    const s = createInitialState(fixedRng([0.1, 0.1]))
    s.snake = [
      { x: 10, y: 10 },
      { x: 11, y: 10 },
      { x: 11, y: 11 },
      { x: 10, y: 11 }
    ]
    s.dir = { x: 1, y: 0 }
    s.nextDir = { x: 1, y: 0 }
    s.food = { x: 0, y: 0 }
    const r = step(s)
    expect(r.over).toBe(true)
    expect(r.overReason).toBe('self')
  })

  it('蛇占满整个棋盘：直接结算，不陷入找空位的死循环', () => {
    // 蛇身 587 节（只差最后一格），食物在最后一格 (27,20)，头在 (26,20) 向右
    const s = createInitialState(fixedRng([0.1, 0.1]))
    const body: { x: number; y: number }[] = []
    for (let y = 0; y < ROWS; y++) {
      for (let x = 0; x < COLS; x++) {
        if (x === 27 && y === 20) continue // 留给食物
        body.push({ x, y })
      }
    }
    const head = body.find((p) => p.x === 26 && p.y === 20)!
    s.snake = [head, ...body.filter((p) => !(p.x === 26 && p.y === 20))]
    s.dir = { x: 1, y: 0 }
    s.nextDir = { x: 1, y: 0 }
    s.food = { x: 27, y: 20 }
    const r = step(s)
    expect(r.ate).toBe(true)
    expect(r.over).toBe(true)
    expect(r.overReason).toBe('boardFull')
  })

  it('游戏结束后再走步不会改变局面', () => {
    const s = createInitialState(fixedRng([0.1, 0.1]))
    s.snake = [
      { x: 27, y: 5 },
      { x: 26, y: 5 },
      { x: 25, y: 5 }
    ]
    s.dir = { x: 1, y: 0 }
    s.nextDir = { x: 1, y: 0 }
    s.food = { x: 0, y: 0 }
    step(s)
    expect(s.over).toBe(true)
    const frozen = JSON.parse(JSON.stringify(s))
    const r = step(s)
    expect(r.over).toBe(true)
    expect(s).toEqual(frozen)
  })
})

describe('转向规则', () => {
  it('正常转向生效', () => {
    const s = createInitialState(fixedRng([0.1, 0.1]))
    tryTurn(s, { x: 0, y: 1 }) // 向右时按「下」
    expect(s.nextDir).toEqual({ x: 0, y: 1 })
    step(s)
    expect(s.snake[0]).toEqual({ x: 14, y: 11 })
  })

  it('180° 掉头被拒绝', () => {
    const s = createInitialState(fixedRng([0.1, 0.1]))
    tryTurn(s, { x: -1, y: 0 }) // 向右时按「左」
    expect(s.nextDir).toEqual({ x: 1, y: 0 }) // 方向不变
  })

  it('一帧内连按两键也无法掉头（代码审查修过的 bug）', () => {
    const s = createInitialState(fixedRng([0.1, 0.1]))
    tryTurn(s, { x: 0, y: -1 }) // 先按「上」：缓冲向上
    tryTurn(s, { x: -1, y: 0 }) // 再按「左」：想借缓冲立刻掉头？拒绝
    expect(s.nextDir).toEqual({ x: 0, y: -1 }) // 缓冲仍是向上
    step(s)
    expect(s.snake[0]).toEqual({ x: 14, y: 9 }) // 实际向上走，没有咬到自己
  })
})

describe('方向判断', () => {
  it('isOpposite 识别相反方向', () => {
    expect(isOpposite({ x: 1, y: 0 }, { x: -1, y: 0 })).toBe(true)
    expect(isOpposite({ x: 0, y: 1 }, { x: 0, y: -1 })).toBe(true)
    expect(isOpposite({ x: 1, y: 0 }, { x: 0, y: 1 })).toBe(false)
    expect(isOpposite({ x: 1, y: 0 }, { x: 1, y: 0 })).toBe(false)
  })
})

describe('食物生成', () => {
  it('随机源抽到蛇身位置时会重抽，直到不在蛇身上', () => {
    const snake = [
      { x: 14, y: 10 },
      { x: 13, y: 10 },
      { x: 12, y: 10 }
    ]
    // 第 1 次抽到 (14,10)（蛇头，必须重抽），第 2 次抽到 (5,5)
    const p = randomFreeCell(snake, fixedRng([0.5, 0.5, 0.19, 0.25]))
    expect(p).toEqual({ x: 5, y: 5 })
  })
})
