import { DatabaseSync } from 'node:sqlite'
import { app } from 'electron'
import { join } from 'path'
import type { BillInput, BillRecord, BillType, CategoryStat, MonthSummary } from '../shared/types'

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
    CREATE TABLE IF NOT EXISTS settings (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    );
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

/** 查询某月（YYYY-MM）的全部账单，按日期倒序（同一天内后记的在前） */
export function listBills(yearMonth: string): BillRecord[] {
  if (!db) throw new Error('数据库尚未初始化')
  const rows = db
    .prepare('SELECT * FROM bills WHERE date LIKE ? ORDER BY date DESC, id DESC')
    .all(`${yearMonth}%`) as Array<Record<string, unknown>>
  return rows.map((r) => ({
    id: Number(r.id),
    type: r.type as BillType,
    amountCents: Number(r.amount_cents),
    date: String(r.date),
    categoryParent: String(r.category_parent),
    category: String(r.category),
    note: String(r.note),
    createdAt: String(r.created_at)
  }))
}

/** 查询某月（YYYY-MM）各支出大类的总金额，按金额从高到低 */
export function getCategoryStats(yearMonth: string): CategoryStat[] {
  if (!db) throw new Error('数据库尚未初始化')
  const rows = db
    .prepare(
      `
      SELECT category_parent, SUM(amount_cents) AS total_cents
      FROM bills
      WHERE type = 'expense' AND date LIKE ?
      GROUP BY category_parent
      ORDER BY total_cents DESC
    `
    )
    .all(`${yearMonth}%`) as Array<Record<string, unknown>>
  return rows.map((r) => ({
    parent: String(r.category_parent),
    totalCents: Number(r.total_cents)
  }))
}

/** 修改一笔账单 */
export function updateBill(id: number, bill: BillInput): void {
  if (!db) throw new Error('数据库尚未初始化')
  db.prepare(
    `
    UPDATE bills
    SET type = ?, amount_cents = ?, date = ?, category_parent = ?, category = ?, note = ?
    WHERE id = ?
  `
  ).run(bill.type, bill.amountCents, bill.date, bill.categoryParent, bill.category, bill.note, id)
}

/** 删除一笔账单 */
export function deleteBill(id: number): void {
  if (!db) throw new Error('数据库尚未初始化')
  db.prepare('DELETE FROM bills WHERE id = ?').run(id)
}

// ---------- 设置（settings 表）----------

const BUDGET_KEY = 'monthly_budget_cents'

/** 读取每月预算（单位：分）；未设置时返回 null */
export function getBudgetCents(): number | null {
  if (!db) throw new Error('数据库尚未初始化')
  const row = db.prepare('SELECT value FROM settings WHERE key = ?').get(BUDGET_KEY) as
    | { value: string }
    | undefined
  return row ? Number(row.value) : null
}

/** 保存每月预算（单位：分） */
export function setBudgetCents(budgetCents: number): void {
  if (!db) throw new Error('数据库尚未初始化')
  db.prepare(
    `INSERT INTO settings (key, value) VALUES (?, ?)
     ON CONFLICT(key) DO UPDATE SET value = excluded.value`
  ).run(BUDGET_KEY, String(budgetCents))
}
