import { app, shell, BrowserWindow, ipcMain, dialog } from 'electron'
import { join } from 'path'
import { spawn, ChildProcess } from 'child_process'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import log from 'electron-log'
import * as fs from 'fs'

// 初始化日志
log.initialize()
// 设置日志文件路径为当前目录
const currentDir = process.cwd()
log.transports.file.resolvePath = () => `${currentDir}/logs/main.log`
log.transports.file.level = 'trace'
log.transports.console.level = 'debug'
log.info('Application starting...')
log.info(`Log file path: ${currentDir}/logs/main.log`)

// Python 进程
let pythonProcess: ChildProcess | null = null
let pythonReady = false
let mainWindow: BrowserWindow | null = null

// 等待 Python 响应队列
const pendingRequests = new Map<string, { resolve: Function; reject: Function }>()

function initPython(): void {
  log.info('Initializing Python process')

  // 查找 Python
  const pythonPath = process.platform === 'win32' ? 'python' : 'python3'
  
  // Python 包目录
  const pythonDir = join(app.getAppPath(), '..', 'python')
  const args = ['-m', 'src.main', '--ipc']

  log.info('Python command:', pythonPath, args)

  try {
    pythonProcess = spawn(pythonPath, args, {
      cwd: pythonDir,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
    })

    // 等待 Python 就绪信号
    let stdoutBuffer = ''
    
    pythonProcess.stdout?.on('data', (data: Buffer) => {
      const raw = data.toString('utf-8')
      
      // 获取主窗口
      const getMainWindow = () => BrowserWindow.getAllWindows()[0]
      
      // 检查进度输出（进度行不进入普通处理）
      if (raw.includes('__PM_PROGRESS__')) {
        try {
          const match = raw.match(/__PM_PROGRESS__(\{.+?\})/)
          if (match) {
            const progress = JSON.parse(match[1])
            getMainWindow()?.webContents.send('organize-progress', progress)
            // 进度行直接返回，不进入普通处理
            return
          }
        } catch (e) {
          log.error('[Progress parse error]:', e)
        }
      }
      
      // data.data 是数组时不打印 debug 日志（数据太长）
      let formattedRaw = raw
      try {
        const rawObj = JSON.parse(raw)
        if (rawObj?.data && Array.isArray(rawObj.data)) {
          // 数组数据太长，不打印
          formattedRaw = `[${rawObj.data.length} items]`
        }
      } catch {}
      log.debug('Raw stdout: ' + formattedRaw)
      stdoutBuffer += raw
      
      // 检查是否有完整的行
      const lines = stdoutBuffer.split('\n')
      stdoutBuffer = lines.pop() || '' // 保留不完整的行
      
      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed) continue
        
        try {
          const response = JSON.parse(trimmed)
          // data.data 是数组时只打印第一个
          const formatted = response?.data && Array.isArray(response.data)
            ? {...response, data: response.data[0]}
            : response
          log.info('Parsed JSON response: ' + JSON.stringify(formatted))
          
          // 处理就绪消息
          if (response.ready) {
            pythonReady = true
            log.info('Python process ready')
            continue
          }
          
          // 处理普通响应
          handlePythonResponse(response)
        } catch (e) {
          log.debug('Non-JSON stdout:', trimmed)
        }
      }
    })

    pythonProcess.stderr?.on('data', (data: Buffer) => {
      const text = data.toString().trim()
      if (!text) return
      
      // 使用 getAllWindows 获取窗口
      const getMainWindow = () => BrowserWindow.getAllWindows()[0]
      
      // 只有以 __PM_PROGRESS__ 开头才尝试解析进度
      if (text.startsWith('__PM_PROGRESS__')) {
        try {
          const match = text.match(/__PM_PROGRESS__(\{.+?\})/)
          if (match) {
            const progress = JSON.parse(match[1])
            getMainWindow()?.webContents.send('organize-progress', progress)
            return
          }
        } catch (e) {
          log.error('[Progress parse error]:', e)
        }
        return
      }
      
      // 只有以 __PM_PROGRESS__ 开头才尝试解析 JSON
      if (text.startsWith('PM_PROGRESS:')) {
        try {
          const match = text.match(/PM_PROGRESS:(\d+)\/(\d+)\|(.+)/)
          if (match) {
            const progress = {
              current: parseInt(match[1]),
              total: parseInt(match[2]),
              status: match[3]
            }
            getMainWindow()?.webContents.send('organize-progress', progress)
            return
          }
        } catch (e) {
          log.error('[Progress parse error]:', e)
        }
        return
      }
      
      // 其他 stderr 日志直接输出
      log.error('Python stderr:', text)
    })

    pythonProcess.on('error', (error) => {
      log.error('Python process error:', error)
      pythonReady = false
    })

    pythonProcess.on('exit', (code) => {
      log.info('Python process exited:', code)
      pythonReady = false
    })
    
    // 超时检测（10秒内必须收到就绪信号）
    setTimeout(() => {
      if (!pythonReady) {
        log.error('Python process did not send ready signal within 10 seconds')
      }
    }, 10000)
    
  } catch (error) {
    log.error('Failed to start Python:', error)
  }
}

function handlePythonResponse(response: any): void {
  const { id, success, data, error } = response
  
  log.debug('Handling response:', { id, success, error })
  
  if (id && pendingRequests.has(id)) {
    const { resolve, reject } = pendingRequests.get(id)!
    pendingRequests.delete(id)
    
    if (success) {
      // 返回完整响应，不只是 data
      resolve(response)
    } else {
      reject(new Error(error || 'Unknown error'))
    }
  } else if (id) {
    log.warn('Received response with unknown id:', id)
  }
}

function pythonExec(command: string, args: object = {}): Promise<any> {
  return new Promise((resolve, reject) => {
    log.info('pythonExec called', { command, pythonReady, hasProcess: !!pythonProcess })
    
    if (!pythonReady || !pythonProcess) {
      log.error('Python not ready', { pythonReady, hasProcess: !!pythonProcess })
      reject(new Error('Python not ready'))
      return
    }

    const id = Date.now().toString() + Math.random().toString(36).substr(2)
    const request = { id, command, args }

    log.info('Sending to Python:', request)

    pendingRequests.set(id, { resolve, reject })

    pythonProcess.stdin?.write(JSON.stringify(request) + '\n')

    // 超时处理（30分钟，长时间任务需要）
    const timeout = setTimeout(() => {
      if (pendingRequests.has(id)) {
        pendingRequests.delete(id)
        log.error('Request timeout for:', command)
        reject(new Error('Request timeout'))
      }
    }, 1800000)
    
    // 清理超时
    pendingRequests.get(id)?.cleanup?.(() => clearTimeout(timeout))
  })
}

function createWindow(): void {
  log.info('Creating main window')

  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    show: false,
    autoHideMenuBar: false,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: false  // 允许加载本地文件
    }
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow.show()
    log.info('Main window shown')
  })

  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  // 加载页面
  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

function setupIpcHandlers(): void {
  log.info('Setting up IPC handlers')

  // 选择目录
  ipcMain.handle('select-directory', async () => {
    const result = await dialog.showOpenDialog({
      properties: ['openDirectory']
    })
    return result.filePaths[0] || null
  })

  // 打开文件夹
  ipcMain.handle('open-in-explorer', async (_, path: string) => {
    shell.showItemInFolder(path)
  })

  // 日志设置
  ipcMain.handle('set-log-level', async (_, level: string) => {
    log.transports.console.level = level.toLowerCase()
    log.info(`Log level changed to: ${level}`)
    return true
  })

  // 照片操作
  ipcMain.handle('organize-photos', async (_, options) => {
    log.info('organize-photos', options)
    try {
      const result = await pythonExec('organize', options)
      log.info('[organize-photos] raw result:', JSON.stringify(result))
      // 确保返回正确的数据结构
      if (!result) return { success: false, total: 0, processed: 0, skipped: 0, failed: 0 }
      // Python 返回 {success: true, data: {...}}
      const data = result.data || result
      const total = data.total ?? 0
      const processed = data.processed ?? 0
      const skipped = data.skipped ?? 0
      const failed = data.failed ?? 0
      log.info('[organize-photos] parsed:', { total, processed, skipped, failed })
      // 直接返回所有统计结果，不判断是否有失败
      return {
        success: true,
        total,
        processed,
        skipped,
        failed,
        errors: data.errors ?? []
      }
    } catch (error) {
      log.error('organize-photos failed:', error)
      throw error
    }
  })

  ipcMain.handle('query-photos', async (_, filters = {}) => {
    try {
      const result = await pythonExec('query-photos', filters)
      return result || []
    } catch (error) {
      log.error('query-photos failed:', error)
      return []
    }
  })

  ipcMain.handle('get-photo', async (_, id: number) => {
    try {
      const result = await pythonExec('get-photo', { id })
      return result
    } catch (error) {
      log.error('get-photo failed:', error)
      return null
    }
  })

  ipcMain.handle('set-rating', async (_, photoId: number, rating: number) => {
    try {
      await pythonExec('set-rating', { photo_id: photoId, rating })
      return true
    } catch (error) {
      log.error('set-rating failed:', error)
      return false
    }
  })

  ipcMain.handle('detect-faces', async (_, photoId: number) => {
    try {
      const result = await pythonExec('detect-faces', { photo_id: photoId })
      return result?.faces || []
    } catch (error) {
      log.error('detect-faces failed:', error)
      return []
    }
  })

  // 标签操作
  ipcMain.handle('add-tag', async (_, photoId: number, tagId: number) => {
    try {
      // TODO: 实现
      return true
    } catch (error) {
      log.error('add-tag failed:', error)
      return false
    }
  })

  ipcMain.handle('remove-tag', async (_, photoId: number, tagId: number) => {
    try {
      const result = await pythonExec('remove-tag', { photo_id: photoId, tag_id: tagId })
      return result?.success || false
    } catch (error) {
      log.error('remove-tag failed:', error)
      return false
    }
  })

  ipcMain.handle('get-tags', async () => {
    try {
      const result = await pythonExec('get-tags', {})
      return result?.data || []
    } catch (error) {
      log.error('get-tags failed:', error)
      return []
    }
  })

  ipcMain.handle('create-tag', async (_, { name, color }) => {
    try {
      const result = await pythonExec('create-tag', { name, color })
      return result?.success ? result.data : null
    } catch (error) {
      log.error('create-tag failed:', error)
      return null
    }
  })

  ipcMain.handle('delete-tag', async (_, { id }) => {
    try {
      const result = await pythonExec('delete-tag', { id })
      return result?.success || false
    } catch (error) {
      log.error('delete-tag failed:', error)
      return false
    }
  })

  ipcMain.handle('get-photo-tags', async (_, { photo_id }) => {
    try {
      const result = await pythonExec('get-photo-tags', { photo_id })
      return result?.data || []
    } catch (error) {
      log.error('get-photo-tags failed:', error)
      return []
    }
  })

  ipcMain.handle('name-face', async (_, { face_id, name, subject_id }) => {
    try {
      const result = await pythonExec('name-face', { face_id, name, subject_id })
      return result?.success || false
    } catch (error) {
      log.error('name-face failed:', error)
      return false
    }
  })

  // 数据操作
  ipcMain.handle('export-json', async (_, outputPath: string) => {
    try {
      const result = await pythonExec('export-json', { output_path: outputPath })
      return result?.success || false
    } catch (error) {
      log.error('export-json failed:', error)
      return false
    }
  })

  ipcMain.handle('import-json', async (_, inputPath: string) => {
    try {
      const result = await pythonExec('import-json', { input_path: inputPath })
      return result?.success || false
    } catch (error) {
      log.error('import-json failed:', error)
      return false
    }
  })

  // 配置操作
  ipcMain.handle('get-settings', async (_, { group = 'organize' }) => {
    try {
      const result = await pythonExec('get-settings', { group })
      if (!result?.success) {
        log.error(`get-settings failed: ${result?.error}`)
        throw new Error(result?.error || '获取配置失败')
      }
      return result.data
    } catch (error) {
      log.error('get-settings failed:', error)
      throw error
    }
  })

  ipcMain.handle('save-settings', async (_, settings) => {
    try {
      const result = await pythonExec('save-settings', settings)
      if (!result?.success) {
        log.error(`save-settings failed: ${result?.error}`)
        throw new Error(result?.error || '保存配置失败')
      }
      return true
    } catch (error) {
      log.error('save-settings failed:', error)
      throw error  // 让前端收到错误
    }
  })

  // 导入记录
  ipcMain.handle('get-import-history', async (_, { limit = 20, offset = 0, status }) => {
    try {
      const result = await pythonExec('get-import-history', { limit, offset, status })
      // 确保返回数组
      if (!result) return []
      if (result.success === false) {
        log.error('get-import-history failed:', result.error)
        return []
      }
      return Array.isArray(result.data) ? result.data : []
    } catch (error) {
      log.error('get-import-history failed:', error)
      return []
    }
  })

  ipcMain.handle('get-import-items', async (_, { import_id, action }) => {
    try {
      const result = await pythonExec('get-import-items', { import_id, action })
      // 确保返回数组
      if (!result) return []
      if (result.success === false) {
        log.error('get-import-items failed:', result.error)
        return []
      }
      return Array.isArray(result.data) ? result.data : []
    } catch (error) {
      log.error('get-import-items failed:', error)
      return []
    }
  })

  // 通用 Python 执行器
  ipcMain.handle('python-exec', async (_, command: string, args: Record<string, unknown> = {}) => {
    log.info(`python-exec: ${command}`, args)
    try {
      const data = await pythonExec(command, args)
      // 如果 data.data 是数组，替换为 data.data[0] 后序列化成单行
      if (data?.data && Array.isArray(data.data)) {
        log.info(`python-exec raw data: [${data.data.length} items] ` + JSON.stringify({...data, data: data.data[0]}))
      } else if (Array.isArray(data)) {
        log.info(`python-exec raw data: [${data.length} items] ` + JSON.stringify(data[0]))
      } else {
        log.info(`python-exec raw data: ` + JSON.stringify(data))
      }
      
      // 直接返回 Python 返回的数据结构
      return data
    } catch (error) {
      log.error(`python-exec error: ${command}`, error)
      return { 
        success: false, 
        error: error instanceof Error ? error.message : String(error) 
      }
    }
  })
}

// 应用启动
app.whenReady().then(() => {
  log.info('App ready')

  // 设置应用 ID（Windows）
  electronApp.setAppUserModelId('com.photo-manager')

  // 开发模式优化
  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  // 设置 IPC
  setupIpcHandlers()

  // 初始化 Python
  initPython()

  // 创建窗口
  createWindow()

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

// 退出
app.on('window-all-closed', () => {
  log.info('All windows closed')
  
  // 关闭 Python 进程
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
  }
  
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

// 全局错误处理
process.on('uncaughtException', (error) => {
  log.error('Uncaught exception:', error)
})

process.on('unhandledRejection', (reason) => {
  log.error('Unhandled rejection:', reason)
})
