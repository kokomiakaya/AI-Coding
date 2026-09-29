// 提交闸门核心脚本（黑马记账项目专属）
//
// 两种用法：
//   1. 算工作区指纹（质检技能写标记时用）：
//        node .claude/scripts/commit-gate.mjs fingerprint
//      输出一行 SHA-1 编号：对「工作区相对 HEAD 的全部改动 + 未跟踪文件内容」计算
//   2. 默认模式（由 Claude Code 的 PreToolUse 钩子调用，stdin 传入钩子 JSON）：
//      命令里含 git commit 时检查质检标记：通过则退出码 0，不通过则退出码 2 并输出中文原因；
//      命令不含 git commit 直接放行；含 --no-verify 放行（应急后门）

import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

// 仓库根目录：优先用钩子环境变量，其次当前目录
const ROOT = process.env.CLAUDE_PROJECT_DIR || process.cwd()
const CHECKS_DIR = join(ROOT, '.claude', 'checks')

const MARKERS = [
  { file: 'unit-test.txt', label: '单元测试' },
  { file: 'quality.txt', label: '质量检查（安全+注释）' }
]

/** 执行 git 命令，二进制安全（stderr 静音，避免换行警告等噪音） */
function git(args) {
  return execFileSync('git', args, {
    cwd: ROOT,
    encoding: 'buffer',
    maxBuffer: 128 * 1024 * 1024,
    stdio: ['ignore', 'pipe', 'ignore']
  })
}

/**
 * 内容指纹：对「每个有改动的文件」累计哈希「路径 + 文件内容编号」。
 * 工作区与暂存区内容一致时，两种模式算出的指纹相同；不一致则不同。
 *
 * - working：工作区相对 HEAD（改动文件 + 未跟踪文件；内容编号用 git hash-object，
 *   即文件实际存进 git 时的编号，自动应用换行符等过滤器）
 * - staged：暂存区相对 HEAD（内容编号取索引里的文件编号）
 */
function contentFingerprint(mode) {
  const names =
    mode === 'working'
      ? [
          ...git(['diff', 'HEAD', '--name-only', '-z']).toString('utf8').split('\0').filter(Boolean),
          ...git(['ls-files', '--others', '--exclude-standard', '-z'])
            .toString('utf8')
            .split('\0')
            .filter(Boolean)
        ]
      : git(['diff', '--cached', '--name-only', '-z']).toString('utf8').split('\0').filter(Boolean)
  const unique = [...new Set(names)].sort()
  const hash = createHash('sha1')
  for (const p of unique) {
    let contentId = 'DELETED'
    if (mode === 'working') {
      if (existsSync(join(ROOT, p))) {
        contentId = git(['hash-object', '--', p]).toString('utf8').trim()
      }
    } else {
      // 索引里的文件编号：ls-files -s 输出形如 "100644 <40位编号> 0\t路径"
      const m = /^\d+\s+([0-9a-f]{40})\s/.exec(git(['ls-files', '-s', '-z', '--', p]).toString('utf8'))
      if (m) contentId = m[1]
    }
    hash.update(`${p}\n${contentId}\n`)
  }
  return hash.digest('hex')
}

/** 检查一份标记文件是否有效，返回问题描述（空字符串 = 通过） */
function checkMarker(file, label, stagedFp) {
  const path = join(CHECKS_DIR, file)
  if (!existsSync(path)) {
    return `缺少「${label}」质检记录（没有跑过 .claude/checks/${file}）`
  }
  const lines = readFileSync(path, 'utf8').split(/\r?\n/)
  const first = (lines[0] || '').trim()
  if (!first.startsWith('PASS')) {
    const reason = first.replace(/^FAIL\s*原因[:：]?\s*/i, '') || '未说明原因'
    return `「${label}」质检未通过：${reason}`
  }
  const fp = (lines[1] || '').trim()
  if (!fp || fp !== stagedFp) {
    return `「${label}」的质检记录与当前要提交的改动不一致（质检后又改过代码）`
  }
  return ''
}

// ---------- 模式一：算工作区指纹 ----------

if (process.argv[2] === 'fingerprint') {
  console.log(contentFingerprint('working'))
  process.exit(0)
}

// ---------- 模式二：钩子检查 ----------

// 非钩子场景（手动运行、stdin 不是钩子 JSON）：放行
let input
try {
  input = JSON.parse(readFileSync(0, 'utf8') || '{}')
} catch {
  process.exit(0)
}
const command = String(input?.tool_input?.command ?? '')

// 不是 git commit：放行
if (!/\bgit\s+commit\b/.test(command)) process.exit(0)

// 应急后门：--no-verify 明确绕过
if (command.includes('--no-verify')) process.exit(0)

// 真正检查（git 本身出错时放行，避免误伤其他命令）
let problems = []
try {
  const stagedFp = contentFingerprint('staged')
  problems = MARKERS.map((m) => checkMarker(m.file, m.label, stagedFp)).filter(Boolean)
} catch (err) {
  process.stderr.write(`提交闸门运行出错（已放行，请检查）：${err.message}\n`)
  process.exit(0)
}

if (problems.length === 0) {
  process.stdout.write('✅ 质检标记齐全，放行提交\n')
  process.exit(0)
}

process.stderr.write('⛔ 提交被拦截（提交闸门）：\n')
for (const p of problems) process.stderr.write(`  - ${p}\n`)
process.stderr.write('\n解决办法：在 Claude Code 里说「提交」，让 gitcommit-agent 先跑单元测试和质量检查。\n')
process.stderr.write('（紧急情况可用 git commit --no-verify 跳过，但请先确认质检通过）\n')
process.exit(2)
