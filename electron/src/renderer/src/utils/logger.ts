/**
 * 前端日志模块
 * 
 * 提供统一的日志接口，支持日志级别控制
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

  static init(level: LogLevel = 'info'): void {
    this.level = level
    this.info('[Logger]', 'Frontend logger initialized', { level })
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
  }

  static trace(source: string, message: string, data?: unknown): void {
    this.log('trace', source, message, data)
  }

  static debug(source: string, message: string, data?: unknown): void {
    this.log('debug', source, message, data)
  }

  static info(source: string, message: string, data?: unknown): void {
    this.log('info', source, message, data)
  }

  static warn(source: string, message: string, data?: unknown): void {
    this.log('warn', source, message, data)
  }

  static error(source: string, message: string, error?: Error | unknown): void {
    this.log('error', source, message, error instanceof Error ? error.message : error)
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
