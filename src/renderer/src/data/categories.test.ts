// 分类数据的「零件质检」（单元测试）
// 运行：npx vitest run
// 说明：分类是记账功能的底座，任何分类的改动都应当让这里全部通过

import { describe, it, expect } from 'vitest'
import {
  expenseCategories,
  incomeCategories,
  expenseIcon,
  expenseSubIcon,
  incomeIcon
} from './categories'

describe('支出分类', () => {
  it('应该有 10 个一级大类', () => {
    expect(expenseCategories).toHaveLength(10)
  })

  it('应该有 41 个二级小类', () => {
    const total = expenseCategories.reduce((n, c) => n + c.children.length, 0)
    expect(total).toBe(41)
  })

  it('每个一级大类都应该有 emoji 图标', () => {
    for (const c of expenseCategories) {
      expect(expenseIcon(c.name), `「${c.name}」缺少图标`).not.toBe('')
    }
  })

  it('每个二级小类都应该有 emoji 图标', () => {
    for (const c of expenseCategories) {
      for (const sub of c.children) {
        expect(expenseSubIcon(sub.name), `「${sub.name}」缺少图标`).not.toBe('')
      }
    }
  })

  it('二级小类的名字应该全局唯一（程序是按名字找图标的）', () => {
    const names = expenseCategories.flatMap((c) => c.children.map((s) => s.name))
    expect(new Set(names).size).toBe(names.length)
  })

  it('未知分类应该有兜底图标 💸，而不是报错或空白', () => {
    expect(expenseIcon('不存在的分类')).toBe('💸')
    expect(expenseSubIcon('不存在的小类')).toBe('💸')
  })

  it('抽查几个具体图标映射', () => {
    expect(expenseIcon('餐饮饮食')).toBe('🍚')
    expect(expenseSubIcon('早餐')).toBe('🍳')
    expect(expenseSubIcon('房租/房贷')).toBe('🏡')
  })
})

describe('收入分类', () => {
  it('应该有 6 个收入分类', () => {
    expect(incomeCategories).toHaveLength(6)
  })

  it('每个收入分类都有名字', () => {
    for (const name of incomeCategories) {
      expect(name.trim()).not.toBe('')
    }
  })

  it('收入的统一图标应该存在', () => {
    expect(incomeIcon).not.toBe('')
  })
})
