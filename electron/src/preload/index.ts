import { contextBridge, ipcRenderer } from 'electron'

// API 类型定义
export interface ElectronAPI {
  // 文件操作
  selectDirectory: () => Promise<string | null>
  openInExplorer: (path: string) => Promise<void>
  
  // 日志
  setLogLevel: (level: string) => Promise<boolean>
  
  // Python 通信
  pythonExec: (command: string, args?: object) => Promise<PythonResult>
  
  // 照片操作
  organizePhotos: (options: OrganizeOptions) => Promise<OrganizeResult>
  queryPhotos: (filters?: PhotoFilters) => Promise<Photo[]>
  getPhoto: (id: number) => Promise<Photo | null>
  
  // 标注操作
  setRating: (photoId: number, rating: number) => Promise<boolean>
  addTag: (photoId: number, tagId: number) => Promise<boolean>
  removeTag: (photoId: number, tagId: number) => Promise<boolean>
  detectFaces: (photoId: number) => Promise<Face[]>
  nameFace: (faceId: number, name: string, subjectId?: number) => Promise<boolean>
  
  // 标签操作
  getTags: () => Promise<Tag[]>
  createTag: (name: string, color: string) => Promise<number>
  deleteTag: (id: number) => Promise<boolean>
  getPhotoTags: (photoId: number) => Promise<Tag[]>
  
  // 数据操作
  exportJson: (outputPath: string) => Promise<boolean>
  importJson: (inputPath: string) => Promise<boolean>
  
  // 配置操作
  getSettings: (group?: string) => Promise<OrganizeSettings>
  saveSettings: (settings: OrganizeSettings) => Promise<boolean>
  
  // 导入记录
  getImportHistory: (limit?: number, offset?: number, status?: string) => Promise<ImportRecord[]>
  getImportItems: (importId: number, action?: string) => Promise<ImportItem[]>
  
  // 进度回调
  onProgress: (callback: (progress: Progress) => void) => void
  removeProgressListener: () => void
}

export interface OrganizeOptions {
  source: string
  dest: string
  mode: 'copy' | 'move' | 'link'
  duplicate_mode?: 'skip' | 'update'
}

export interface OrganizeResult {
  success: boolean
  total: number
  processed: number
  skipped: number
  failed: number
  errors: string[]
  import_id?: number
}

export interface ImportRecord {
  id: number
  created_at: string
  source_path: string
  dest_path: string
  mode: string
  duplicate_mode: string
  total_count: number
  success_count: number
  skip_count: number
  fail_count: number
  status: 'running' | 'completed' | 'failed' | 'cancelled'
  error_msg: string | null
}

export interface ImportItem {
  id: number
  import_id: number
  file_path: string
  file_hash: string
  file_size: number
  organized_path: string | null
  action: 'added' | 'skipped' | 'updated' | 'failed'
  reason: string | null
  error_msg: string | null
  created_at: string
}

export interface Photo {
  id: number
  file_path: string
  file_hash: string
  file_name: string
  taken_at: string | null
  organized_date: string | null
  rating: number
  is_portrait: number
  thumb_path: string | null
}

export interface PhotoFilters {
  rating?: number
  is_portrait?: boolean
  tag_id?: number
  date_from?: string
  date_to?: string
  search?: string
}

export interface Face {
  id: number
  photo_id: number
  face_x: number
  face_y: number
  face_w: number
  face_h: number
  subject_name: string | null
  confidence: number
}

export interface Tag {
  id: number
  name: string
  color: string
}

export interface Progress {
  current: number
  total: number
  currentFile: string
  status: string
}

export interface OrganizeSettings {
  mode?: 'copy' | 'move' | 'link'
  source?: string
  base?: string
  include_unknown?: boolean
  duplicate_mode?: 'skip' | 'update'
  time_priority?: string
}

export interface PythonResult {
  success: boolean
  data?: unknown
  error?: string
}

// 暴露 API
const api: ElectronAPI = {
  selectDirectory: () => ipcRenderer.invoke('select-directory'),
  openInExplorer: (path) => ipcRenderer.invoke('open-in-explorer', path),
  setLogLevel: (level) => ipcRenderer.invoke('set-log-level', level),
  
  pythonExec: (command, args) => ipcRenderer.invoke('python-exec', command, args || {}),
  
  organizePhotos: (options) => ipcRenderer.invoke('organize-photos', options),
  queryPhotos: (filters) => ipcRenderer.invoke('query-photos', filters || {}),
  getPhoto: (id) => ipcRenderer.invoke('get-photo', id),
  
  setRating: (photoId, rating) => ipcRenderer.invoke('set-rating', photoId, rating),
  addTag: (photoId, tagId) => ipcRenderer.invoke('add-tag', photoId, tagId),
  removeTag: (photoId, tagId) => ipcRenderer.invoke('remove-tag', photoId, tagId),
  detectFaces: (photoId) => ipcRenderer.invoke('detect-faces', photoId),
  nameFace: (faceId, name, subjectId) => 
    ipcRenderer.invoke('name-face', { face_id: faceId, name, subject_id: subjectId }),
  
  getTags: () => ipcRenderer.invoke('get-tags'),
  createTag: (name, color) => ipcRenderer.invoke('create-tag', { name, color }),
  deleteTag: (id) => ipcRenderer.invoke('delete-tag', { id }),
  getPhotoTags: (photoId) => ipcRenderer.invoke('get-photo-tags', { photo_id: photoId }),
  
  exportJson: (outputPath) => ipcRenderer.invoke('export-json', outputPath),
  importJson: (inputPath) => ipcRenderer.invoke('import-json', inputPath),
  
  getSettings: (group = 'organize') => ipcRenderer.invoke('get-settings', { group }),
  saveSettings: (settings) => ipcRenderer.invoke('save-settings', { group: 'organize', ...settings }),
  
  getImportHistory: (limit = 20, offset = 0, status) => 
    ipcRenderer.invoke('get-import-history', { limit, offset, status }),
  getImportItems: (importId, action) => 
    ipcRenderer.invoke('get-import-items', { import_id: importId, action }),
  
  onProgress: (callback) => {
    ipcRenderer.on('organize-progress', (_, progress) => callback(progress))
  },
  removeProgressListener: () => {
    ipcRenderer.removeAllListeners('organize-progress')
  }
}

contextBridge.exposeInMainWorld('electronAPI', api)
