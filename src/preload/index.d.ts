import type { BillInput, MonthSummary } from '../shared/types'

declare global {
  interface Window {
    electron: typeof import('@electron-toolkit/preload').electronAPI
    api: {
      addBill: (bill: BillInput) => Promise<{ ok: boolean; id?: number; error?: string }>
      getMonthSummary: (
        yearMonth: string
      ) => Promise<{ ok: boolean; summary?: MonthSummary; error?: string }>
    }
  }
}

export {}
