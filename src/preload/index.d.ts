import type { BillInput, BillRecord, MonthSummary } from '../shared/types'

declare global {
  interface Window {
    electron: typeof import('@electron-toolkit/preload').electronAPI
    api: {
      addBill: (bill: BillInput) => Promise<{ ok: boolean; id?: number; error?: string }>
      getMonthSummary: (
        yearMonth: string
      ) => Promise<{ ok: boolean; summary?: MonthSummary; error?: string }>
      listBills: (
        yearMonth: string
      ) => Promise<{ ok: boolean; bills?: BillRecord[]; error?: string }>
      updateBill: (id: number, bill: BillInput) => Promise<{ ok: boolean; error?: string }>
      deleteBill: (id: number) => Promise<{ ok: boolean; error?: string }>
    }
  }
}

export {}
