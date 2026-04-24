/**
 * 前端日志模块
 * 
 * 提供统一的日志接口，支持日志级别控制和文件存储
 */

type LogLevel = 'trace' | 'debug' | 'info' | 'warn' | 'error'

interface LogEntry {
  timestamp: string
  level: LogLevel
  source: string
  message: string
  data?: unknown
}

class FrontendLogger {
  private static logs: LogEntry[] = []
  private static maxLogs = 500
  private static level: LogLevel = 'info'
  private static logFilePath: string | null = null

  static init(level: LogLevel = 'info'): void {
    this.level = level
    this.initLogFile()
    this.info('Frontend logger initialized', { level })
  }

  private static initLogFile(): void {
    // 尝试使用 Electron API 获取当前目录并创建日志文件
    if (window.electronAPI && window.electronAPI.pythonExec) {
      // 这里我们通过 Python API 来获取当前目录并创建日志文件
      // 实际项目中可以通过专门的 IPC 方法来处理文件操作
      window.electronAPI.pythonExec('get-current-dir').then((result) => {
        if (result && result.data) {
          const currentDir = result.data
          this.logFilePath = `${currentDir}/logs/frontend.log`
          this.info('Frontend log file initialized', { path: this.logFilePath })
        }
      }).catch((error) => {
        console.error('Failed to initialize log file:', error)
      })
    }
  }

  static setLevel(level: LogLevel): void {
    this.level = level
  }

  private static shouldLog(level: LogLevel): boolean {
    const levels: Record<LogLevel, number> = {
      trace: 0,
      debug: 1,
      info: 2,
      warn: 3,
      error: 4
    }
    return levels[level] >= levels[this.level]
  }

  private static log(level: LogLevel, source: string, message: string, data?: unknown): void {
    if (!this.shouldLog(level)) return

    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      source,
      message,
      data
    }

    this.logs.push(entry)
    if (this.logs.length > this.maxLogs) {
      this.logs.shift()
    }

    const prefix = `[${level.toUpperCase()}] ${source}`
    const args = data !== undefined ? [prefix, message, data] : [prefix, message]

    switch (level) {
      case 'trace':
      case 'debug':
        console.debug(...args)
        break
      case 'info':
        console.info(...args)
        break
      case 'warn':
        console.warn(...args)
        break
      case 'error':
        console.error(...args, data instanceof Error ? (data as Error).stack : '')
        break
    }

    // 尝试写入日志文件
    this.writeToFile(entry)
  }

  private static writeToFile(entry: LogEntry): void {
    if (!this.logFilePath || !window.electronAPI || !window.electronAPI.pythonExec) {
      return
    }

    // 通过 Python API 写入日志文件
    const logMessage = `${entry.timestamp} | ${entry.level.toUpperCase()} | ${entry.source} | ${entry.message}`
    window.electronAPI.pythonExec('write-log', {
      file_path: this.logFilePath,
      message: logMessage
    }).catch((error) => {
      console.error('Failed to write log to file:', error)
    })
  }

  // 统一日志方法：自动兼容新旧风格
  // - 新风格: logger.info('message') 或 logger.info('message', data)
  // - 旧风格: logger.info('source', 'message') 或 logger.info('source', 'message', data)
  static info(message: string, dataOrSource?: unknown, arg3?: unknown): void {
    // 旧风格: logger.info('source', 'message') 或 logger.info('source', 'message', data)
    if (typeof dataOrSource === 'string') {
      this.log('info', dataOrSource, message, arg3)
    } else {
      // 新风格: logger.info('message') 或 logger.info('message', data)
      this.log('info', 'App', message, dataOrSource)
    }
  }

  static debug(message: string, dataOrSource?: unknown, arg3?: unknown): void {
    if (typeof dataOrSource === 'string') {
      this.log('debug', dataOrSource, message, arg3)
    } else {
      this.log('debug', 'App', message, dataOrSource)
    }
  }

  static warn(message: string, dataOrSource?: unknown, arg3?: unknown): void {
    if (typeof dataOrSource === 'string') {
      this.log('warn', dataOrSource, message, arg3)
    } else {
      this.log('warn', 'App', message, dataOrSource)
    }
  }

  static error(message: string, dataOrSource?: unknown, arg3?: unknown): void {
    if (typeof dataOrSource === 'string') {
      this.log('error', dataOrSource, message, arg3)
    } else {
      this.log('error', 'App', message, dataOrSource)
    }
  }

  static trace(message: string, dataOrSource?: unknown, arg3?: unknown): void {
    if (typeof dataOrSource === 'string') {
      this.log('trace', dataOrSource, message, arg3)
    } else {
      this.log('trace', 'App', message, dataOrSource)
    }
  }

  static getLogs(): LogEntry[] {
    return [...this.logs]
  }

  static clearLogs(): void {
    this.logs = []
  }
}

export const logger = FrontendLogger

// 初始化
logger.init()
