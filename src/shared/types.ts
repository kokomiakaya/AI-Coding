// 主进程与渲染进程共享的数据类型

export type BillType = 'expense' | 'income'

/** 一笔账单（保存时由渲染进程传入） */
export interface BillInput {
  type: BillType
  amountCents: number // 金额，单位「分」：用整数存储，避免小数误差
  date: string // 格式 YYYY-MM-DD
  categoryParent: string // 支出的一级大类；收入为空字符串
  category: string // 支出的二级小类 / 收入的分类名
  note: string
}

/** 某月汇总 */
export interface MonthSummary {
  incomeCents: number
  expenseCents: number
}

/** 数据库中的一条账单记录 */
export interface BillRecord extends BillInput {
  id: number
  createdAt: string
}
