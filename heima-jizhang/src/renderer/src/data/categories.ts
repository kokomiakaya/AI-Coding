// 记账分类数据
// 与 CLAUDE.md 第 4 节保持一致；调整分类前必须先征得用户同意

export interface SubCategory {
  name: string
}

export interface ExpenseCategory {
  name: string
  children: SubCategory[]
}

/** 支出：两级分类（10 个一级大类） */
export const expenseCategories: ExpenseCategory[] = [
  {
    name: '餐饮饮食',
    children: [
      { name: '早餐' },
      { name: '午餐' },
      { name: '晚餐' },
      { name: '外卖' },
      { name: '零食饮料' },
      { name: '聚餐请客' }
    ]
  },
  {
    name: '交通出行',
    children: [
      { name: '公交地铁' },
      { name: '打车' },
      { name: '加油充电' },
      { name: '停车费' },
      { name: '火车高铁' },
      { name: '飞机票' }
    ]
  },
  {
    name: '购物消费',
    children: [
      { name: '日用品' },
      { name: '服装鞋包' },
      { name: '数码家电' },
      { name: '美妆护肤' },
      { name: '母婴用品' }
    ]
  },
  {
    name: '居住生活',
    children: [
      { name: '房租/房贷' },
      { name: '水电燃气' },
      { name: '物业费' },
      { name: '家居用品' },
      { name: '维修养护' }
    ]
  },
  {
    name: '休闲娱乐',
    children: [
      { name: '电影演出' },
      { name: '游戏充值' },
      { name: '运动健身' },
      { name: '旅游度假' }
    ]
  },
  {
    name: '医疗健康',
    children: [
      { name: '门诊就医' },
      { name: '药品购买' },
      { name: '体检保健' },
      { name: '牙科眼科' }
    ]
  },
  {
    name: '学习教育',
    children: [
      { name: '书籍资料' },
      { name: '课程培训' },
      { name: '考试报名' },
      { name: '文具用品' }
    ]
  },
  {
    name: '人情往来',
    children: [
      { name: '礼物赠送' },
      { name: '红包礼金' },
      { name: '随礼请客' }
    ]
  },
  {
    name: '通讯网络',
    children: [
      { name: '手机话费' },
      { name: '宽带网费' },
      { name: '会员订阅' }
    ]
  },
  {
    name: '其他支出',
    children: [{ name: '其他' }]
  }
]

/** 收入：单级分类 */
export const incomeCategories: string[] = [
  '工资',
  '奖金',
  '理财收益',
  '兼职外快',
  '红包',
  '其他收入'
]

/** 支出大类对应的图标（用于明细列表、统计页、分类菜单） */
const expenseIcons: Record<string, string> = {
  餐饮饮食: '🍚',
  交通出行: '🚌',
  购物消费: '🛍️',
  居住生活: '🏠',
  休闲娱乐: '🎮',
  医疗健康: '🩺',
  学习教育: '📚',
  人情往来: '🤝',
  通讯网络: '📱',
  其他支出: '📦'
}

/** 根据支出大类取图标 */
export function expenseIcon(parent: string): string {
  return expenseIcons[parent] ?? '💸'
}

/** 支出小类对应的图标（用于分类选择菜单；小类名全局唯一，可直接按名字查） */
const expenseSubIcons: Record<string, string> = {
  早餐: '🍳',
  午餐: '🍱',
  晚餐: '🍲',
  外卖: '🛵',
  零食饮料: '🧋',
  聚餐请客: '🍻',
  公交地铁: '🚇',
  打车: '🚕',
  加油充电: '⛽',
  停车费: '🅿️',
  火车高铁: '🚄',
  飞机票: '✈️',
  日用品: '🧻',
  服装鞋包: '👗',
  数码家电: '💻',
  美妆护肤: '💄',
  母婴用品: '🍼',
  '房租/房贷': '🏡',
  水电燃气: '💡',
  物业费: '🏢',
  家居用品: '🛋️',
  维修养护: '🔧',
  电影演出: '🎬',
  游戏充值: '🕹️',
  运动健身: '⚽',
  旅游度假: '🏖️',
  门诊就医: '🏥',
  药品购买: '💊',
  体检保健: '📋',
  牙科眼科: '🦷',
  书籍资料: '📖',
  课程培训: '🎓',
  考试报名: '📝',
  文具用品: '✏️',
  礼物赠送: '🎁',
  红包礼金: '🧧',
  随礼请客: '🥂',
  手机话费: '📞',
  宽带网费: '🌐',
  会员订阅: '⭐',
  其他: '🗂️'
}

/** 根据支出小类取图标 */
export function expenseSubIcon(name: string): string {
  return expenseSubIcons[name] ?? '💸'
}

/** 收入的图标 */
export const incomeIcon = '💰'
