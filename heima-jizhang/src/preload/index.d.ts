import type { BillInput, BillRecord, CategoryStat, MonthSummary } from '../shared/types'

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
      getCategoryStats: (
        yearMonth: string
      ) => Promise<{ ok: boolean; stats?: CategoryStat[]; error?: string }>
      getBudget: () => Promise<{ ok: boolean; budgetCents?: number; error?: string }>
      setBudget: (budgetCents: number) => Promise<{ ok: boolean; error?: string }>
    }
  }
}

export {}
