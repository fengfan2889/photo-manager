import { useState, useEffect } from 'react'
import { History, CheckCircle, XCircle, Clock, ChevronRight, FileText, Filter } from 'lucide-react'
import type { ImportRecord, ImportItem } from '../../preload/index'

export default function ImportHistory() {
  const [records, setRecords] = useState<ImportRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedRecord, setSelectedRecord] = useState<ImportRecord | null>(null)
  const [items, setItems] = useState<ImportItem[]>([])
  const [filter, setFilter] = useState<string>('all')

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = async () => {
    setLoading(true)
    try {
      const status = filter === 'all' ? undefined : filter
      const history = await window.electronAPI.getImportHistory(50, 0, status)
      setRecords(history)
    } catch (error) {
      console.error('Failed to load import history:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadItems = async (importId: number) => {
    try {
      const result = await window.electronAPI.getImportItems(importId)
      setItems(result)
    } catch (error) {
      console.error('Failed to load import items:', error)
    }
  }

  const handleRecordClick = (record: ImportRecord) => {
    setSelectedRecord(record)
    loadItems(record.id)
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN')
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />
      case 'running':
        return <Clock className="w-5 h-5 text-blue-500 animate-pulse" />
      default:
        return <Clock className="w-5 h-5 text-gray-400" />
    }
  }

  const getActionColor = (action: string) => {
    switch (action) {
      case 'added':
        return 'bg-green-100 text-green-700'
      case 'skipped':
        return 'bg-yellow-100 text-yellow-700'
      case 'updated':
        return 'bg-blue-100 text-blue-700'
      case 'failed':
        return 'bg-red-100 text-red-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  return (
    <div className="h-full flex">
      {/* 左侧列表 */}
      <div className="w-1/2 border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-xl font-semibold flex items-center gap-2">
              <History className="w-6 h-6" />
              导入历史
            </h1>
            <button
              onClick={loadHistory}
              className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
            >
              刷新
            </button>
          </div>

          {/* 筛选 */}
          <div className="flex gap-2">
            {['all', 'completed', 'failed', 'running'].map((f) => (
              <button
                key={f}
                onClick={() => {
                  setFilter(f)
                  setSelectedRecord(null)
                }}
                className={`px-3 py-1 text-sm rounded ${
                  filter === f
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 hover:bg-gray-200'
                }`}
              >
                {f === 'all' ? '全部' : f === 'completed' ? '成功' : f === 'failed' ? '失败' : '进行中'}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-4 text-center text-gray-500">加载中...</div>
          ) : records.length === 0 ? (
            <div className="p-4 text-center text-gray-500">暂无导入记录</div>
          ) : (
            <div className="divide-y divide-gray-100">
              {records.map((record) => (
                <div
                  key={record.id}
                  onClick={() => handleRecordClick(record)}
                  className={`p-4 cursor-pointer hover:bg-gray-50 ${
                    selectedRecord?.id === record.id ? 'bg-blue-50' : ''
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        {getStatusIcon(record.status)}
                        <span className="font-medium">
                          {record.success_count + record.skip_count + record.fail_count} 个文件
                        </span>
                      </div>
                      <div className="text-sm text-gray-500 space-y-1">
                        <div className="truncate" title={record.source_path}>
                          源: {record.source_path}
                        </div>
                        <div className="truncate" title={record.dest_path}>
                          目标: {record.dest_path}
                        </div>
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        {formatDate(record.created_at)}
                      </div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 右侧详情 */}
      <div className="flex-1 flex flex-col">
        {!selectedRecord ? (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>选择一条记录查看详情</p>
            </div>
          </div>
        ) : (
          <>
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold mb-2">导入详情</h2>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">源目录:</span>
                  <div className="font-mono text-xs truncate" title={selectedRecord.source_path}>
                    {selectedRecord.source_path}
                  </div>
                </div>
                <div>
                  <span className="text-gray-500">目标目录:</span>
                  <div className="font-mono text-xs truncate" title={selectedRecord.dest_path}>
                    {selectedRecord.dest_path}
                  </div>
                </div>
                <div>
                  <span className="text-gray-500">整理模式:</span>
                  <span className="ml-2">{selectedRecord.mode}</span>
                </div>
                <div>
                  <span className="text-gray-500">去重模式:</span>
                  <span className="ml-2">{selectedRecord.duplicate_mode}</span>
                </div>
                <div>
                  <span className="text-gray-500">成功:</span>
                  <span className="ml-2 text-green-600">{selectedRecord.success_count}</span>
                </div>
                <div>
                  <span className="text-gray-500">跳过:</span>
                  <span className="ml-2 text-yellow-600">{selectedRecord.skip_count}</span>
                </div>
                <div>
                  <span className="text-gray-500">失败:</span>
                  <span className="ml-2 text-red-600">{selectedRecord.fail_count}</span>
                </div>
                <div>
                  <span className="text-gray-500">时间:</span>
                  <span className="ml-2">{formatDate(selectedRecord.created_at)}</span>
                </div>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              <h3 className="font-medium mb-3">文件明细</h3>
              {items.length === 0 ? (
                <div className="text-center text-gray-500 py-8">暂无数据</div>
              ) : (
                <div className="space-y-2">
                  {items.map((item) => (
                    <div
                      key={item.id}
                      className="p-3 bg-gray-50 rounded text-sm"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="font-mono text-xs truncate" title={item.file_path}>
                            {item.file_path}
                          </div>
                          {item.reason && (
                            <div className="text-gray-500 text-xs mt-1">{item.reason}</div>
                          )}
                          {item.error_msg && (
                            <div className="text-red-500 text-xs mt-1">{item.error_msg}</div>
                          )}
                        </div>
                        <span className={`px-2 py-1 rounded text-xs ${getActionColor(item.action)}`}>
                          {item.action === 'added' ? '新增' : 
                           item.action === 'skipped' ? '跳过' : 
                           item.action === 'updated' ? '更新' : '失败'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
