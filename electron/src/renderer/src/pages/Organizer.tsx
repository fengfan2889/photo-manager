import { useState, useEffect } from 'react'
import { logger } from '../utils/logger'
import { ErrorToast } from '../components/ErrorToast'
import { useError } from '../hooks/useError'

export default function Organizer() {
  const [sourceDir, setSourceDir] = useState('')
  const [destDir, setDestDir] = useState('')
  const [mode, setMode] = useState<'copy' | 'move' | 'link'>('copy')
  const [duplicateMode, setDuplicateMode] = useState<'skip' | 'update'>('skip')
  const [organizing, setOrganizing] = useState(false)
  const [progress, setProgress] = useState({ current: 0, total: 0, status: '' })
  const { error, showError, clearError } = useError()

  // 初始化时读取配置
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const config = await window.electronAPI.getSettings('organize')
        if (config) {
          setSourceDir(config.source || '')
          setDestDir(config.base || '')
          setMode(config.mode || 'copy')
          setDuplicateMode(config.duplicate_mode || 'skip')
          logger.debug('Config loaded', config)
        }
      } catch (error) {
        const msg = error instanceof Error ? error.message : String(error)
        showError('加载配置失败', msg)
      }
    }
    loadConfig()
  }, [])

  const selectSource = async () => {
    try {
      const dir = await window.electronAPI.selectDirectory()
      if (dir) setSourceDir(dir)
      logger.debug('Source directory selected', { path: dir })
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      showError('选择目录失败', msg)
    }
  }

  const selectDest = async () => {
    try {
      const dir = await window.electronAPI.selectDirectory()
      if (dir) setDestDir(dir)
      logger.debug('Destination directory selected', { path: dir })
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      showError('选择目录失败', msg)
    }
  }

  const saveConfig = async () => {
    try {
      const success = await window.electronAPI.saveSettings({
        source: sourceDir,
        base: destDir,
        mode,
        duplicate_mode: duplicateMode
      })
      if (success) {
        logger.debug('Config saved', { source: sourceDir, base: destDir, mode, duplicate_mode: duplicateMode })
      } else {
        showError('保存配置失败')
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      showError('保存配置失败', msg)
    }
  }

  const startOrganize = async () => {
    if (!sourceDir || !destDir) {
      showError('请选择源目录和目标目录')
      return
    }

    setOrganizing(true)
    logger.info('Starting organize', { source: sourceDir, dest: destDir, mode })

    // 监听进度
    window.electronAPI.onProgress((p) => {
      setProgress({ current: p.current, total: p.total, status: p.status })
    })

    try {
      // 保存配置
      await saveConfig()

      const result = await window.electronAPI.organizePhotos({
        source: sourceDir,
        dest: destDir,
        mode,
        duplicate_mode: duplicateMode
      })
      logger.info('Organize completed', result)
      
      alert(`整理完成！总数: ${result.total}, 成功: ${result.processed}, 跳过: ${result.skipped}, 失败: ${result.failed}`)
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      showError('整理失败', msg)
    } finally {
      setOrganizing(false)
      window.electronAPI.removeProgressListener()
    }
  }

  return (
    <>
      <ErrorToast error={error} onClose={clearError} />
      
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">整理照片</h1>

        <div className="space-y-6">
          {/* 源目录 */}
          <div>
            <label className="block text-sm font-medium mb-2">源目录</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={sourceDir}
                onChange={(e) => setSourceDir(e.target.value)}
                className="flex-1 px-3 py-2 border rounded-lg bg-gray-50"
                placeholder="选择要整理的照片目录"
              />
              <button
                onClick={selectSource}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                浏览
              </button>
            </div>
          </div>

          {/* 目标目录 */}
          <div>
            <label className="block text-sm font-medium mb-2">目标目录</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={destDir}
                onChange={(e) => setDestDir(e.target.value)}
                className="flex-1 px-3 py-2 border rounded-lg bg-gray-50"
                placeholder="选择整理后的输出目录"
              />
              <button
                onClick={selectDest}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                浏览
              </button>
            </div>
          </div>

          {/* 整理模式 */}
          <div>
            <label className="block text-sm font-medium mb-2">整理模式</label>
            <div className="flex gap-4">
              {(['copy', 'move', 'link'] as const).map((m) => (
                <label key={m} className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="mode"
                    checked={mode === m}
                    onChange={() => setMode(m)}
                    className="w-4 h-4"
                  />
                  <span>
                    {m === 'copy' && '复制'}
                    {m === 'move' && '移动'}
                    {m === 'link' && '链接'}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* 重复文件处理 */}
          <div>
            <label className="block text-sm font-medium mb-2">重复文件处理</label>
            <div className="flex gap-4">
              {(['skip', 'update'] as const).map((m) => (
                <label key={m} className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="duplicateMode"
                    checked={duplicateMode === m}
                    onChange={() => setDuplicateMode(m)}
                    className="w-4 h-4"
                  />
                  <span>
                    {m === 'skip' ? '跳过重复文件' : '覆盖重复文件'}
                  </span>
                </label>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-1">
              按文件内容 Hash 判断是否重复
            </p>
          </div>

          {/* 进度 */}
          {organizing && (
            <div className="bg-blue-50 p-4 rounded-lg">
              <p className="text-sm text-blue-600 mb-2">{progress.status}</p>
              <div className="w-full bg-blue-200 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full transition-all"
                  style={{ width: `${(progress.current / progress.total) * 100}%` }}
                />
              </div>
              <p className="text-sm text-blue-600 mt-2">
                {progress.current} / {progress.total}
              </p>
            </div>
          )}

          {/* 按钮组 */}
          <div className="flex gap-4">
            <button
              onClick={saveConfig}
              disabled={organizing}
              className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 disabled:opacity-50"
            >
              保存配置
            </button>
            <button
              onClick={startOrganize}
              disabled={organizing || !sourceDir || !destDir}
              className="px-6 py-3 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {organizing ? '整理中...' : '开始整理'}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
