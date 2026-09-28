import { contextBridge, ipcRenderer } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'
import type { BillInput, BillRecord, CategoryStat, MonthSummary } from '../shared/types'

// 渲染进程可用的业务接口（通过 IPC 调用主进程）
const api = {
  addBill: (bill: BillInput): Promise<{ ok: boolean; id?: number; error?: string }> =>
    ipcRenderer.invoke('bill:add', bill),
  getMonthSummary: (
    yearMonth: string
  ): Promise<{ ok: boolean; summary?: MonthSummary; error?: string }> =>
    ipcRenderer.invoke('bill:monthSummary', yearMonth),
  listBills: (
    yearMonth: string
  ): Promise<{ ok: boolean; bills?: BillRecord[]; error?: string }> =>
    ipcRenderer.invoke('bill:list', yearMonth),
  updateBill: (
    id: number,
    bill: BillInput
  ): Promise<{ ok: boolean; error?: string }> =>
    ipcRenderer.invoke('bill:update', id, bill),
  deleteBill: (id: number): Promise<{ ok: boolean; error?: string }> =>
    ipcRenderer.invoke('bill:delete', id),
  getCategoryStats: (
    yearMonth: string
  ): Promise<{ ok: boolean; stats?: CategoryStat[]; error?: string }> =>
    ipcRenderer.invoke('bill:categoryStats', yearMonth),
  getBudget: (): Promise<{ ok: boolean; budgetCents?: number; error?: string }> =>
    ipcRenderer.invoke('budget:get'),
  setBudget: (budgetCents: number): Promise<{ ok: boolean; error?: string }> =>
    ipcRenderer.invoke('budget:set', budgetCents)
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
