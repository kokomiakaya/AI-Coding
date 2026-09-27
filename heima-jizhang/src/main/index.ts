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
  getCategoryStats
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

app.whenReady().then(() => {
  electronApp.setAppUserModelId('com.heima.jizhang')

  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  initDatabase()
  registerBillHandlers()

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
