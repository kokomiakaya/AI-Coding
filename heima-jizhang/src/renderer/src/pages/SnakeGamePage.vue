<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

// ---------- 常量（与 Python 版玩法保持一致） ----------
const CELL = 24 // 每格像素
const COLS = 28 // 网格列数
const ROWS = 21 // 网格行数
const FPS_BASE = 5 // 初始速度（格/秒）
const FPS_MAX = 15 // 最快速度
const SPEEDUP_EVERY = 5 // 每吃几个食物加速一次

type Point = { x: number; y: number }
type GameState = 'idle' | 'running' | 'paused' | 'over'

const canvasRef = ref<HTMLCanvasElement | null>(null)
const state = ref<GameState>('idle')
const score = ref(0)
const highScore = ref(0)
const newRecord = ref(false)

let snake: Point[] = []
let food: Point = { x: 0, y: 0 }
let dir: Point = { x: 1, y: 0 } // 当前移动方向
let nextDir: Point = { x: 1, y: 0 } // 缓冲方向：一帧内只能改一次，防止瞬间掉头
let timer: ReturnType<typeof setInterval> | null = null

/** 当前速度：每吃 5 个食物加速一档，最快 15 格/秒 */
const speedFps = computed(() =>
  Math.min(FPS_BASE + Math.floor(score.value / SPEEDUP_EVERY), FPS_MAX)
)

function randomFreeCell(): Point {
  while (true) {
    const p = { x: Math.floor(Math.random() * COLS), y: Math.floor(Math.random() * ROWS) }
    if (!snake.some((s) => s.x === p.x && s.y === p.y)) return p
  }
}

function resetGame(): void {
  // 初始蛇：中间偏左，3 节，向右移动（与 Python 版一致）
  snake = [
    { x: 14, y: 10 },
    { x: 13, y: 10 },
    { x: 12, y: 10 }
  ]
  dir = { x: 1, y: 0 }
  nextDir = { x: 1, y: 0 }
  score.value = 0
  newRecord.value = false
  food = randomFreeCell()
  draw()
}

function startTimer(): void {
  stopTimer()
  timer = setInterval(step, 1000 / speedFps.value)
}

function stopTimer(): void {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function step(): void {
  dir = nextDir
  const head = { x: snake[0].x + dir.x, y: snake[0].y + dir.y }
  // 撞墙
  if (head.x < 0 || head.x >= COLS || head.y < 0 || head.y >= ROWS) {
    gameOver()
    return
  }
  // 咬到自己
  if (snake.some((s) => s.x === head.x && s.y === head.y)) {
    gameOver()
    return
  }
  snake.unshift(head)
  if (head.x === food.x && head.y === food.y) {
    score.value += 1
    if (snake.length >= COLS * ROWS) {
      // 蛇占满整个棋盘（几乎不可能达到）：直接结算，避免找空位陷入死循环
      gameOver()
      return
    }
    food = randomFreeCell()
    startTimer() // 分数变化后速度可能提升，重新计时
  } else {
    snake.pop()
  }
  draw()
}

async function gameOver(): Promise<void> {
  stopTimer()
  state.value = 'over'
  draw()
  if (score.value > highScore.value) {
    highScore.value = score.value
    newRecord.value = score.value > 0
    await window.api.setSnakeHighScore(highScore.value)
  }
}

function startGame(): void {
  resetGame()
  state.value = 'running'
  startTimer()
}

function togglePause(): void {
  if (state.value === 'running') {
    state.value = 'paused'
    stopTimer()
    draw()
  } else if (state.value === 'paused') {
    state.value = 'running'
    startTimer()
  }
}

/** 点击按钮后让它失去焦点，避免随后按空格/回车又触发一次按钮 */
function onBtnClick(e: MouseEvent, fn: () => void): void {
  fn()
  ;(e.currentTarget as HTMLElement).blur()
}

// ---------- 绘制 ----------
function draw(): void {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // 浅色背景
  ctx.fillStyle = '#f2f4f7'
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  // 深色网格线（方便看清每一格）
  ctx.strokeStyle = '#8b95a5'
  ctx.lineWidth = 1
  ctx.beginPath()
  for (let x = 1; x < COLS; x++) {
    ctx.moveTo(x * CELL + 0.5, 0)
    ctx.lineTo(x * CELL + 0.5, canvas.height)
  }
  for (let y = 1; y < ROWS; y++) {
    ctx.moveTo(0, y * CELL + 0.5)
    ctx.lineTo(canvas.width, y * CELL + 0.5)
  }
  ctx.stroke()

  // 非进行中时盖一层半透明遮罩，让文字清晰可读
  if (state.value !== 'running') {
    ctx.fillStyle = 'rgba(15, 20, 28, 0.6)'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
  }

  // 食物（红色圆点）
  ctx.fillStyle = '#f56c6c'
  ctx.beginPath()
  ctx.arc(food.x * CELL + CELL / 2, food.y * CELL + CELL / 2, CELL / 2 - 4, 0, Math.PI * 2)
  ctx.fill()

  // 蛇身（头部更亮）
  snake.forEach((s, i) => {
    ctx.fillStyle = i === 0 ? '#85ce61' : '#67c23a'
    ctx.beginPath()
    ctx.roundRect(s.x * CELL + 1.5, s.y * CELL + 1.5, CELL - 3, CELL - 3, 6)
    ctx.fill()
  })

  // 状态提示文字
  if (state.value !== 'running') {
    ctx.textAlign = 'center'
    ctx.fillStyle = '#ffffff'
    ctx.font = 'bold 28px "Microsoft YaHei", sans-serif'
    let title = ''
    if (state.value === 'idle') title = '🐍 贪吃蛇'
    else if (state.value === 'paused') title = '⏸️ 已暂停'
    else title = '💀 游戏结束'
    ctx.fillText(title, canvas.width / 2, canvas.height / 2 - 26)
    ctx.fillStyle = '#c8cdd6'
    ctx.font = '15px "Microsoft YaHei", sans-serif'
    let sub = ''
    if (state.value === 'idle') sub = '点「开始游戏」或按回车开始'
    else if (state.value === 'paused') sub = '按 P 或空格继续'
    else sub = newRecord.value ? `🎉 新纪录！本局 ${score.value} 分` : `本局 ${score.value} 分`
    ctx.fillText(sub, canvas.width / 2, canvas.height / 2 + 14)
  }
}

// ---------- 键盘操作 ----------
function onKeydown(e: KeyboardEvent): void {
  const key = e.key
  const isArrow = key.startsWith('Arrow')
  // 方向键和空格会滚动页面，阻止默认行为
  if (isArrow || key === ' ') e.preventDefault()

  // 方向键 / WASD 转向
  if (isArrow || /^[wasd]$/i.test(key)) {
    const k = key.toLowerCase()
    let want: Point
    if (k === 'arrowup' || k === 'w') want = { x: 0, y: -1 }
    else if (k === 'arrowdown' || k === 's') want = { x: 0, y: 1 }
    else if (k === 'arrowleft' || k === 'a') want = { x: -1, y: 0 }
    else want = { x: 1, y: 0 }
    // 不允许 180 度掉头（以当前实际方向为准，防止一帧内连按两键完成掉头）
    if (want.x === -dir.x && want.y === -dir.y) return
    if (state.value === 'idle' || state.value === 'over') {
      // 按方向键也能直接开局
      resetGame()
      nextDir = want
      state.value = 'running'
      startTimer()
      return
    }
    nextDir = want
    return
  }

  // P / 空格：暂停与继续
  if (key === ' ' || key.toLowerCase() === 'p') {
    if (state.value === 'running' || state.value === 'paused') togglePause()
    return
  }

  // 回车：开始 / 重开
  if (key === 'Enter') {
    if (state.value === 'idle' || state.value === 'over') startGame()
  }
}

onMounted(async () => {
  const res = await window.api.getSnakeHighScore()
  if (res.ok && res.score) highScore.value = res.score
  resetGame() // 先画一帧初始画面
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  stopTimer()
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>游戏</h2>
    </div>

    <div class="card game-card">
      <div class="card-title">🐍 贪吃蛇</div>

      <div class="game-hud">
        <div class="hud-item">
          <span class="hud-label">分数</span>
          <span class="hud-value">{{ score }}</span>
        </div>
        <div class="hud-item">
          <span class="hud-label">最高分</span>
          <span class="hud-value high">{{ highScore }}</span>
        </div>
        <div class="hud-item">
          <span class="hud-label">速度</span>
          <span class="hud-value">{{ speedFps }} 格/秒</span>
        </div>
        <div v-if="newRecord" class="new-record">🎉 新纪录！</div>
      </div>

      <canvas
        ref="canvasRef"
        :width="COLS * CELL"
        :height="ROWS * CELL"
        class="game-canvas"
      ></canvas>

      <div class="game-controls">
        <el-button
          v-if="state === 'idle' || state === 'over'"
          type="primary"
          size="large"
          @click="onBtnClick($event, startGame)"
        >
          {{ state === 'idle' ? '开始游戏' : '再来一局' }}
        </el-button>
        <el-button v-if="state === 'running'" size="large" @click="onBtnClick($event, togglePause)">
          暂停
        </el-button>
        <el-button
          v-if="state === 'paused'"
          type="primary"
          size="large"
          @click="onBtnClick($event, togglePause)"
        >
          继续
        </el-button>
      </div>

      <div class="game-hints">方向键 / WASD 移动 · P 或空格 暂停 · 回车 开始/重开 · 撞墙或咬到自己游戏结束</div>
    </div>
  </div>
</template>

<style scoped>
.game-card {
  max-width: 720px;
  margin: 0 auto;
  text-align: center;
}

.game-hud {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 32px;
  margin-bottom: 12px;
}

.hud-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.hud-label {
  font-size: 13px;
  color: #909399;
}

.hud-value {
  font-size: 22px;
  font-weight: 600;
  color: #303133;
  font-variant-numeric: tabular-nums;
}

.hud-value.high {
  color: #e6a23c;
}

.new-record {
  color: #e6a23c;
  font-size: 15px;
  font-weight: 600;
  animation: blink 1s infinite;
}

@keyframes blink {
  50% {
    opacity: 0.4;
  }
}

.game-canvas {
  display: block;
  margin: 0 auto;
  max-width: 100%;
  height: auto;
  border-radius: 8px;
}

.game-controls {
  margin-top: 14px;
}

.game-hints {
  margin-top: 10px;
  font-size: 13px;
  color: #909399;
}
</style>
