// npm run dev        — авто-настройка + Ollama + бэкенд + фронтенд одной командой
// npm start          — авто-настройка + Ollama + сборка фронта + единый сервер на :8000
// npm run dev:api    — только бэкенд
// npm run dev:web    — только фронтенд
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { join } from 'node:path'
import {
  BACKEND, FRONTEND, ROOT, backendPython, backendReady, childEnv, color,
  ensureOllamaAndModel, isWin, killTree, loadEnv, run, runNpm, runPython,
} from './lib.mjs'

const mode = process.argv[2] // 'api' | 'web' | 'prod' | 'docker' | undefined

if (mode === 'docker') {
  if (!existsSync(join(ROOT, '.env'))) {
    const { copyFileSync } = await import('node:fs')
    copyFileSync(join(ROOT, '.env.example'), join(ROOT, '.env'))
  }
  loadEnv(true)
  if (!process.env.ANALYSIS_API_KEY || !process.env.SECRET_KEY) {
    const { randomBytes } = await import('node:crypto')
    const { readFileSync, writeFileSync } = await import('node:fs')
    let text = readFileSync(join(ROOT, '.env'), 'utf8')
    for (const name of ['ANALYSIS_API_KEY', 'SECRET_KEY']) {
      const val = `${name}=${randomBytes(32).toString('base64url')}`
      const re = new RegExp(`^${name}=.*$`, 'm')
      text = re.test(text) ? text.replace(re, val) : `${text.trimEnd()}\n${val}\n`
    }
    writeFileSync(join(ROOT, '.env'), text, 'utf8')
    loadEnv(true)
  }
  const apiPort = process.env.API_PORT || '8000'
  console.log(
    `\n  ${color.bold('ForteWatch Docker')}   http://localhost:${apiPort}` +
      `\n  ${color.bold('Swagger API docs')}    http://localhost:${apiPort}/api/docs` +
      `\n  ${color.bold('X-API-Key (.env)')}    в файле .env (ANALYSIS_API_KEY)\n`,
  )
  const code = await run('docker', ['compose', 'up', '--build'], { cwd: ROOT })
  process.exit(code)
}

const needsBackend = mode !== 'web'
const needsFrontend = mode !== 'api'
if (
  !existsSync(join(ROOT, '.env')) ||
  (needsBackend && !backendReady()) ||
  (needsFrontend && !existsSync(join(FRONTEND, 'node_modules')))
) {
  console.log(color.cyan('▸ Первичный запуск: автоматическая установка окружения (setup)...'))
  const code = await run(process.execPath, [join(ROOT, 'scripts', 'setup.mjs')], { cwd: ROOT })
  if (code !== 0) process.exit(code)
}

loadEnv(true)

if (needsBackend && (!process.env.ANALYSIS_API_KEY || !process.env.SECRET_KEY)) {
  await runPython([join(ROOT, 'scripts', 'init_analysis.py')])
  loadEnv(true)
}

const apiPort = process.env.API_PORT || '8000'
const webPort = process.env.WEB_PORT || '5173'

const children = []

function start(name, paint, cmd, args, opts) {
  const child = spawn(cmd, args, { ...opts, windowsHide: true, env: childEnv({ FORCE_COLOR: '1' }) })
  const tag = paint(`[${name}]`)
  const pipe = (stream, out) => {
    let buf = ''
    stream.on('data', (d) => {
      buf += d.toString()
      const lines = buf.split(/\r?\n/)
      buf = lines.pop()
      for (const line of lines) out.write(`${tag} ${line}\n`)
    })
  }
  pipe(child.stdout, process.stdout)
  pipe(child.stderr, process.stderr)
  child.on('exit', (code) => {
    console.log(`${tag} exited with code ${code}`)
    shutdown(code ?? 0)
  })
  children.push(child)
}

let stopping = false
function shutdown(code = 0) {
  if (stopping) return
  stopping = true
  children.forEach(killTree)
  process.exit(code)
}
process.on('SIGINT', () => shutdown(0))
process.on('SIGTERM', () => shutdown(0))

if (needsBackend) {
  await ensureOllamaAndModel()
  if ((await runPython(['-m', 'alembic', 'upgrade', 'head'])) !== 0) {
    console.error(color.red('Миграции не применились — проверьте DATABASE_URL и backend/migrations'))
    process.exit(1)
  }
}

if (mode === 'prod') {
  console.log(color.cyan('▸ Сборка фронтенда (production)...'))
  if ((await runNpm(['run', 'build'])) !== 0) {
    console.error(color.red('Сборка фронтенда завершилась с ошибкой'))
    process.exit(1)
  }
  const py = backendPython(['-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', apiPort])
  start('app', color.cyan, py.cmd, py.args, { cwd: BACKEND })
  console.log(
    `\n  ${color.bold('ForteWatch UI & API')}  http://localhost:${apiPort}` +
      `\n  ${color.bold('Swagger API docs')}     http://localhost:${apiPort}/api/docs` +
      `\n  ${color.bold('API Key')}              см. ANALYSIS_API_KEY в корневом .env\n`,
  )
} else {
  if (needsBackend) {
    const py = backendPython(['-m', 'uvicorn', 'app.main:app', '--reload', '--host', '127.0.0.1', '--port', apiPort])
    start('api', color.cyan, py.cmd, py.args, { cwd: BACKEND })
  }
  if (needsFrontend) {
    const cmd = isWin ? 'cmd.exe' : 'npm'
    const args = isWin ? ['/d', '/s', '/c', 'npm', 'run', 'dev'] : ['run', 'dev']
    start('web', color.magenta, cmd, args, { cwd: FRONTEND })
  }
  console.log(
    `\n  ${color.bold('Frontend')}  http://localhost:${webPort}` +
      `\n  ${color.bold('API docs')}  http://localhost:${apiPort}/api/docs` +
      `\n  ${color.bold('API Key')}   см. ANALYSIS_API_KEY в корневом .env\n`,
  )
}
