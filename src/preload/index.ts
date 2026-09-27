import { contextBridge, ipcRenderer } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'
import type { BillInput } from '../shared/types'

// 渲染进程可用的业务接口（通过 IPC 调用主进程）
const api = {
  addBill: (bill: BillInput): Promise<{ ok: boolean; id?: number; error?: string }> =>
    ipcRenderer.invoke('bill:add', bill),
  getMonthSummary: (
    yearMonth: string
  ): Promise<{ ok: boolean; summary?: { incomeCents: number; expenseCents: number }; error?: string }> =>
    ipcRenderer.invoke('bill:monthSummary', yearMonth)
}

if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld('electron', electronAPI)
    contextBridge.exposeInMainWorld('api', api)
  } catch (error) {
    console.error(error)
  }
} else {
  // @ts-ignore (define in dts)
  window.electron = electronAPI
  // @ts-ignore (define in dts)
  window.api = api
}
