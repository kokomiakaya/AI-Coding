import { DatabaseSync } from 'node:sqlite'
import { app } from 'electron'
import { join } from 'path'
import type { BillInput, MonthSummary } from '../shared/types'

// 账单数据库（SQLite）
// 数据文件位于系统应用数据目录，例如 C:\Users\用户名\AppData\Roaming\heima-jizhang\heima-jizhang.db
// 升级程序不会丢失账本数据

let db: DatabaseSync | null = null

/** 打开（或创建）数据库并建表，应用启动时调用一次 */
export function initDatabase(): void {
  const dbPath = join(app.getPath('userData'), 'heima-jizhang.db')
  db = new DatabaseSync(dbPath)
  db.exec(`
    CREATE TABLE IF NOT EXISTS bills (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      type TEXT NOT NULL CHECK (type IN ('expense', 'income')),
      amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
      date TEXT NOT NULL,
      category_parent TEXT NOT NULL DEFAULT '',
      category TEXT NOT NULL,
      note TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    CREATE INDEX IF NOT EXISTS idx_bills_date ON bills(date);
  `)
}

/** 保存一笔账单，返回新账单的 id */
export function addBill(bill: BillInput): number {
  if (!db) throw new Error('数据库尚未初始化')
  const stmt = db.prepare(`
    INSERT INTO bills (type, amount_cents, date, category_parent, category, note)
    VALUES (?, ?, ?, ?, ?, ?)
  `)
  const result = stmt.run(
    bill.type,
    bill.amountCents,
    bill.date,
    bill.categoryParent,
    bill.category,
    bill.note
  )
  return Number(result.lastInsertRowid)
}

/** 查询某月（YYYY-MM）的收入与支出总额 */
export function getMonthSummary(yearMonth: string): MonthSummary {
  if (!db) throw new Error('数据库尚未初始化')
  const row = db
    .prepare(
      `
      SELECT
        COALESCE(SUM(CASE WHEN type = 'income' THEN amount_cents ELSE 0 END), 0) AS income_cents,
        COALESCE(SUM(CASE WHEN type = 'expense' THEN amount_cents ELSE 0 END), 0) AS expense_cents
      FROM bills
      WHERE date LIKE ?
    `
    )
    .get(`${yearMonth}%`) as { income_cents: number; expense_cents: number }
  return { incomeCents: row.income_cents, expenseCents: row.expense_cents }
}
