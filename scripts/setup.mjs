// npm run setup — один раз после клонирования. Повторный запуск безопасен.
import { spawnSync } from 'node:child_process'
import { copyFileSync, existsSync } from 'node:fs'
import { join } from 'node:path'
import {
  BACKEND, FRONTEND, ROOT, color, ensureOllamaAndModel, isWin, loadEnv, run, runNpm, runPython, useUv, venvPython,
} from './lib.mjs'

const step = (msg) => console.log(`\n${color.cyan('▸')} ${color.bold(msg)}`)
const fail = (msg) => {
  console.error(`\n${color.red('✖')} ${msg}`)
  process.exit(1)
}

function findSystemPython() {
  const candidates = isWin ? [['py', ['-3']], ['python', []], ['python3', []]] : [['python3', []], ['python', []]]
  for (const [cmd, pre] of candidates) {
    const r = spawnSync(cmd, [...pre, '-c', 'import sys; print(sys.version_info >= (3, 11))'], { encoding: 'utf8' })
    if (r.status === 0 && r.stdout.trim() === 'True') return [cmd, pre]
  }
  return null
}

step('.env и ключи доступа')
const envFile = join(ROOT, '.env')
if (existsSync(envFile)) console.log(color.dim('  .env уже есть — сохраняю текущие настройки'))
else {
  copyFileSync(join(ROOT, '.env.example'), envFile)
  console.log('  создан .env из .env.example')
}

step('Backend: зависимости')
if (useUv()) {
  console.log(color.dim('  найден uv'))
  if ((await run('uv', ['sync', '--extra', 'dev'], { cwd: BACKEND })) !== 0) fail('uv sync завершился с ошибкой')
} else {
  console.log(color.dim('  uv не найден — использую python -m venv + pip'))
  if (!existsSync(venvPython())) {
    const py = findSystemPython()
    if (!py) fail('Нужен Python 3.11+ (https://www.python.org/downloads/) или uv (https://docs.astral.sh/uv/)')
    if ((await run(py[0], [...py[1], '-m', 'venv', '.venv'], { cwd: BACKEND })) !== 0) fail('Не удалось создать venv')
  }
  const pip = (args) => run(venvPython(), ['-m', 'pip', ...args], { cwd: BACKEND })
  await pip(['install', '--upgrade', '--quiet', 'pip'])
  if ((await pip(['install', '-e', '.[dev]'])) !== 0) fail('pip install завершился с ошибкой')
}

if ((await runPython([join(ROOT, 'scripts', 'init_analysis.py')])) !== 0) {
  fail('Не удалось инициализировать ключи в .env')
}
loadEnv(true)

step('Database: migrations')
if ((await runPython(['-m', 'alembic', 'upgrade', 'head'])) !== 0) fail('Миграции не применились')

step('Frontend: зависимости')
if ((await runNpm(['install'], { cwd: FRONTEND })) !== 0) fail('npm install завершился с ошибкой')

step('Ollama: локальная модель Qwen3.5-4B')
await ensureOllamaAndModel()

console.log(`\n${color.green('✔ Готово!')} Запуск одной командой: ${color.bold('npm run dev')} (или ${color.bold('npm start')})\n`)
