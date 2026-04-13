import { useState } from 'react'
import { logger } from '../utils/logger'

export default function Settings() {
  const [settings, setSettings] = useState({
    organizeMode: 'copy',
    organizeBase: '',
    organizeIncludeUnknown: true,
    logLevel: 'INFO'
  })

  const handleSave = () => {
    logger.info('Saving settings', settings)
    // TODO: 保存设置
    alert('设置已保存')
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
                value={settings.organizeMode}
                onChange={(e) => setSettings({ ...settings, organizeMode: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="copy">复制</option>
                <option value="move">移动</option>
                <option value="link">链接</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">整理输出目录</label>
              <input
                type="text"
                value={settings.organizeBase}
                onChange={(e) => setSettings({ ...settings, organizeBase: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="留空使用默认目录"
              />
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="includeUnknown"
                checked={settings.organizeIncludeUnknown}
                onChange={(e) => setSettings({ ...settings, organizeIncludeUnknown: e.target.checked })}
                className="w-4 h-4"
              />
              <label htmlFor="includeUnknown" className="text-sm">
                整理无法识别时间的照片
              </label>
            </div>
          </div>
        </div>

        {/* 日志设置 */}
        <div className="bg-white p-4 rounded-lg shadow">
          <h2 className="text-lg font-medium mb-4">日志设置</h2>
          
          <div>
            <label className="block text-sm font-medium mb-1">日志级别</label>
            <select
              value={settings.logLevel}
              onChange={async (e) => {
                setSettings({ ...settings, logLevel: e.target.value })
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
          className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          保存设置
        </button>
      </div>
    </div>
  )
}
