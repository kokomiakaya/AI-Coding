import { app, shell, BrowserWindow, ipcMain } from 'electron'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import {
  initDatabase,
  addBill,
  getMonthSummary,
  listBills,
  updateBill,
  deleteBill,
  getCategoryStats,
  getBudgetCents,
  setBudgetCents,
  getSnakeHighScore,
  setSnakeHighScore
} from './db'
import type { BillInput } from '../shared/types'

function createWindow(): void {
  const mainWindow = new BrowserWindow({
    width: 1080,
    height: 720,
    minWidth: 900,
    minHeight: 600,
    show: false,
    autoHideMenuBar: true,
    title: '黑马记账',
    backgroundColor: '#f5f6f8',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false
    }
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow.show()
  })

  // 外部链接用系统默认浏览器打开，不在应用内跳转
  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

// 注册账单相关的接口：渲染进程通过 window.api 调用
function registerBillHandlers(): void {
  ipcMain.handle('bill:add', (_event, bill: BillInput) => {
    try {
      const id = addBill(bill)
      return { ok: true, id }
    } catch (error) {
      return { ok: false, error: String(error) }
    }
  })

  ipcMain.handle('bill:monthSummary', (_event, yearMonth: string) => {
    try {
      const summary = getMonthSummary(yearMonth)
      return { ok: true, summary }
    } catch (error) {
      return { ok: false, error: String(error) }
    }
  })

  ipcMain.handle('bill:list', (_event, yearMonth: string) => {
    try {
      const bills = listBills(yearMonth)
      return { ok: true, bills }
    } catch (error) {
      return { ok: false, error: String(error) }
    }
  })

  ipcMain.handle('bill:update', (_event, id: number, bill: BillInput) => {
    try {
      updateBill(id, bill)
      return { ok: true }
    } catch (error) {
      return { ok: false, error: String(error) }
    }
  })

  ipcMain.handle('bill:delete', (_event, id: number) => {
    try {
      deleteBill(id)
      return { ok: true }
    } catch (error) {
      return { ok: false, error: String(error) }
    }
  })

  ipcMain.handle('bill:categoryStats', (_event, yearMonth: string) => {
    try {
      const stats = getCategoryStats(yearMonth)
      return { ok: true, stats }
    } catch (error) {
      return { ok: false, error: String(error) }
    }
  })
}

// 注册预算相关的接口
function registerBudgetHandlers(): void {
  ipcMain.handle('budget:get', () => {
    try {
      const budgetCents = getBudgetCents()
      return { ok: true, budgetCents }
    } catch (error) {
      return { ok: false, error: String(error) }
    }
  })

  ipcMain.handle('budget:set', (_event, budgetCents: number) => {
    try {
      if (!Number.isInteger(budgetCents) || budgetCents <= 0) {
        return { ok: false, error: '预算必须是大于 0 的整数（单位：分）' }
      }
      setBudgetCents(budgetCents)
      return { ok: true }
    } catch (error) {
      return { ok: false, error: String(error) }
    }
  })
}

// 注册贪吃蛇游戏相关的接口
function registerGameHandlers(): void {
  ipcMain.handle('game:getHighScore', () => {
    try {
      const score = getSnakeHighScore()
      return { ok: true, score }
    } catch (error) {
      return { ok: false, error: String(error) }
    }
  })

  ipcMain.handle('game:setHighScore', (_event, score: number) => {
    try {
      if (!Number.isInteger(score) || score < 0) {
        return { ok: false, error: '分数必须是大于等于 0 的整数' }
      }
      setSnakeHighScore(score)
      return { ok: true }
    } catch (error) {
      return { ok: false, error: String(error) }
    }
  })
}

app.whenReady().then(() => {
  electronApp.setAppUserModelId('com.heima.jizhang')

  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  initDatabase()
  registerBillHandlers()
  registerBudgetHandlers()
  registerGameHandlers()

  createWindow()

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
