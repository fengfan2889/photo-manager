import { useState, useEffect } from 'react'
import { logger } from '../utils/logger'

export default function Settings() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [settings, setSettings] = useState({
    mode: 'copy',
    source: '',
    base: '',
    include_unknown: true,
    duplicate_mode: 'skip',
    time_priority: 'exif>mtime>ctime'
  })

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const data = await window.electronAPI.getSettings('organize')
      setSettings({
        mode: data.mode || 'copy',
        source: data.source || '',
        base: data.base || '',
        include_unknown: data.include_unknown ?? true,
        duplicate_mode: data.duplicate_mode || 'skip',
        time_priority: data.time_priority || 'exif>mtime>ctime'
      })
    } catch (error) {
      logger.error('Failed to load settings:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await window.electronAPI.saveSettings({
        mode: settings.mode,
        source: settings.source,
        base: settings.base,
        include_unknown: settings.include_unknown,
        duplicate_mode: settings.duplicate_mode,
        time_priority: settings.time_priority
      })
      alert('设置已保存')
    } catch (error) {
      logger.error('Failed to save settings:', error)
      alert('保存失败')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="p-6">加载中...</div>
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">设置</h1>

      <div className="max-w-xl space-y-6">
        {/* 整理设置 */}
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-lg font-medium mb-4">整理设置</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">默认整理模式</label>
              <select
                value={settings.mode}
                onChange={(e) => setSettings({ ...settings, mode: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="copy">复制 (Copy)</option>
                <option value="move">移动 (Move)</option>
                <option value="link">链接 (Link)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">整理输出目录</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={settings.base}
                  onChange={(e) => setSettings({ ...settings, base: e.target.value })}
                  className="flex-1 px-3 py-2 border rounded-lg"
                  placeholder="留空使用默认目录"
                />
                <button
                  onClick={async () => {
                    const dir = await window.electronAPI.selectDirectory()
                    if (dir) {
                      setSettings({ ...settings, base: dir })
                    }
                  }}
                  className="px-3 py-2 bg-gray-100 border rounded-lg hover:bg-gray-200"
                >
                  选择
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">重复文件处理</label>
              <select
                value={settings.duplicate_mode}
                onChange={(e) => setSettings({ ...settings, duplicate_mode: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="skip">跳过 (Skip) - 不处理重复文件</option>
                <option value="update">覆盖 (Update) - 替换已存在的文件</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                按文件内容 Hash 判断是否重复
              </p>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="includeUnknown"
                checked={settings.include_unknown}
                onChange={(e) => setSettings({ ...settings, include_unknown: e.target.checked })}
                className="w-4 h-4"
              />
              <label htmlFor="includeUnknown" className="text-sm">
                整理无法识别时间的照片
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">时间优先级</label>
              <select
                value={settings.time_priority}
                onChange={(e) => setSettings({ ...settings, time_priority: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="exif>mtime>ctime">EXIF &gt; 修改时间 &gt; 创建时间</option>
                <option value="mtime>ctime>exif">修改时间 &gt; 创建时间 &gt; EXIF</option>
                <option value="ctime>mtime>exif">创建时间 &gt; 修改时间 &gt; EXIF</option>
              </select>
            </div>
          </div>
        </div>

        {/* 日志设置 */}
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-lg font-medium mb-4">日志设置</h2>
          
          <div>
            <label className="block text-sm font-medium mb-1">日志级别</label>
            <select
              onChange={async (e) => {
                await window.electronAPI.setLogLevel(e.target.value)
              }}
              className="w-full px-3 py-2 border rounded-lg"
            >
              <option value="TRACE">TRACE - 最详细</option>
              <option value="DEBUG">DEBUG - 调试</option>
              <option value="INFO">INFO - 信息</option>
              <option value="WARNING">WARNING - 警告</option>
              <option value="ERROR">ERROR - 错误</option>
            </select>
          </div>
        </div>

        {/* 保存按钮 */}
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
        >
          {saving ? '保存中...' : '保存设置'}
        </button>
      </div>
    </div>
  )
}
