<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import {
  CELL,
  COLS,
  ROWS,
  createInitialState,
  speedFpsFor,
  tryTurn,
  isOpposite,
  step as stepGame
} from '../game/snake-engine'
import type { Point, SnakeState } from '../game/snake-engine'

type GameState = 'idle' | 'running' | 'paused' | 'over'

const canvasRef = ref<HTMLCanvasElement | null>(null)
const state = ref<GameState>('idle')
const score = ref(0)
const highScore = ref(0)
const newRecord = ref(false)

// 游戏局面（蛇、食物、方向、分数），规则全部在 snake-engine.ts 里
let game: SnakeState = createInitialState()
let timer: ReturnType<typeof setInterval> | null = null

/** 当前速度：每吃 5 个食物加速一档，最快 15 格/秒 */
const speedFps = computed(() => speedFpsFor(score.value))

function resetGame(): void {
  game = createInitialState()
  score.value = 0
  newRecord.value = false
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
  const result = stepGame(game)
  score.value = game.score
  if (result.over) {
    gameOver()
    return
  }
  if (result.ate) startTimer() // 分数变化后速度可能提升，重新计时
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
  ctx.arc(
    game.food.x * CELL + CELL / 2,
    game.food.y * CELL + CELL / 2,
    CELL / 2 - 4,
    0,
    Math.PI * 2
  )
  ctx.fill()

  // 蛇身（头部更亮）
  game.snake.forEach((s, i) => {
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
    if (state.value === 'idle' || state.value === 'over') {
      // 按方向键也能直接开局；与当前方向相反的键不生效
      if (isOpposite(want, game.dir)) return
      resetGame()
      game.nextDir = want
      state.value = 'running'
      startTimer()
      return
    }
    tryTurn(game, want)
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
