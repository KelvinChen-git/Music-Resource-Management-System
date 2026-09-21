<template>
  <div class="file-list">
    <div class="search-bar">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="File Name" class="search-item">
          <el-input v-model="searchForm.fileName" placeholder="Enter file name" clearable />
        </el-form-item>
        <el-form-item label="File Type" class="search-item">
          <el-input v-model="searchForm.fileType" placeholder="Enter file type" clearable />
        </el-form-item>
        <el-form-item label="Status" class="search-item">
          <el-select v-model="searchForm.status" placeholder="Select status" clearable>
            <el-option label="Uploading" :value="0" />
            <el-option label="Completed" :value="1" />
          </el-select>
        </el-form-item>
        <el-form-item class="search-buttons">
          <el-button type="primary" @click="searchFiles">Search</el-button>
          <el-button @click="resetSearch">Reset</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 移动端文件列表 -->
    <div class="mobile-file-list" v-if="isMobile">
      <div v-for="row in fileList" :key="row.id" class="mobile-file-item">
        <div class="mobile-file-header">
          <el-tooltip :content="row.fileName" placement="top" :show-after="1000">
            <div class="mobile-file-name">{{ row.fileName }}</div>
          </el-tooltip>
          <el-tag :type="row.status === 1 ? 'success' : 'warning'" size="small" class="status-tag">
            {{ row.status === 1 ? 'Completed...' : 'Uploading...' }}
          </el-tag>
        </div>
        <div class="mobile-file-info">
          <span>{{ row.fileType }}</span>
          <span>{{ formatFileSize(row.fileSize) }}</span>
        </div>
        <div class="mobile-file-time">
          <div>Upload: {{ formatTime(row.createTime) }}</div>
          <div v-if="row.completeTime">Complete: {{ formatTime(row.completeTime) }}</div>
        </div>
        <div class="mobile-file-actions">
          <el-dropdown trigger="click">
            <el-button type="primary">
              Actions<el-icon class="el-icon--right"><arrow-down /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-if="row.status === 1" @click="downloadFile(row)">
                  <el-icon><download /></el-icon> Download
                </el-dropdown-item>
                <el-dropdown-item v-if="row.status === 1 && row.fileType.toLowerCase() === 'mp3'" @click="handleParseMetadata(row)">
                  <el-icon><document /></el-icon> Parse Metadata
                </el-dropdown-item>
                <el-dropdown-item @click="showUploadStatus(row)">
                  <el-icon><upload /></el-icon> Upload Status
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleDelete(row)" class="danger-item">
                  <el-icon><delete /></el-icon> Delete
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </div>

    <!-- PC端表格视图 -->
    <el-table 
      v-else
      :data="fileList" 
      style="width: 100%" 
      v-loading="loading"
      @sort-change="handleSortChange"
      :default-sort="{ prop: 'createTime', order: 'descending' }"
    >
      <el-table-column prop="fileName" label="File Name" min-width="200" sortable="custom">
        <template #default="{ row }">
          <el-tooltip :content="row.fileName" placement="top" :show-after="1000">
            <span class="file-name">{{ row.fileName }}</span>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column prop="fileType" label="Type" width="100" sortable="custom" />
      <el-table-column prop="fileSize" label="Size" width="120" sortable="custom">
        <template #default="{ row }">
          {{ formatFileSize(row.fileSize) }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="Status" width="120">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'warning'" class="status-tag">
            {{ row.status === 1 ? 'Completed...' : 'Uploading...' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="createTime" label="Upload Time" width="180" sortable="custom" />
      <el-table-column prop="completeTime" label="Complete Time" width="180" sortable="custom" />
      <el-table-column label="Actions" width="120" fixed="right">
        <template #default="{ row }">
          <el-dropdown trigger="click">
            <el-button type="primary" link>
              Actions<el-icon class="el-icon--right"><arrow-down /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-if="row.status === 1" @click="downloadFile(row)">
                  <el-icon><download /></el-icon> Download
                </el-dropdown-item>
                <el-dropdown-item v-if="row.status === 1 && row.fileType.toLowerCase() === 'mp3'" @click="handleParseMetadata(row)">
                  <el-icon><document /></el-icon> Parse Metadata
                </el-dropdown-item>
                <el-dropdown-item @click="showUploadStatus(row)">
                  <el-icon><upload /></el-icon> Upload Status
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleDelete(row)" class="danger-item">
                  <el-icon><delete /></el-icon> Delete
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加分页组件 -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="pagination.current"
        v-model:page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 上传状态对话框 -->
    <el-dialog
      v-model="statusDialog.visible"
      :title="'File Upload Status - ' + (statusDialog.data?.fileName || '')"
      :width="isMobile ? '95%' : '600px'"
      :fullscreen="isMobile"
    >
      <div v-if="statusDialog.data" class="upload-status">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="File Size">
            {{ formatFileSize(statusDialog.data.fileSize) }}
          </el-descriptions-item>
          <el-descriptions-item label="File Type">
            {{ statusDialog.data.fileType }}
          </el-descriptions-item>
          <el-descriptions-item label="Total Chunks">
            {{ statusDialog.data.chunkCount }}
          </el-descriptions-item>
          <el-descriptions-item label="Uploaded Chunks">
            {{ statusDialog.data.uploadedChunks }}
          </el-descriptions-item>
          <el-descriptions-item label="Start Time">
            {{ statusDialog.data.createTime }}
          </el-descriptions-item>
          <el-descriptions-item label="Last Update">
            {{ statusDialog.data.updateTime }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="progress-section">
          <div class="progress-header">
            <span>Upload Progress: {{ Math.floor(statusDialog.data.progress) }}%</span>
          </div>
          <el-progress 
            :percentage="statusDialog.data.progress" 
            :status="statusDialog.data.status === 1 ? 'success' : ''"
          />
        </div>

        <div class="chunks-section">
          <div class="chunks-grid">
            <div
              v-for="i in statusDialog.data.chunkCount"
              :key="i-1"
              class="chunk-item"
              :class="{
                'uploaded': statusDialog.data.uploadedChunkIndexes.includes(i-1),
                'missing': statusDialog.data.missingChunkIndexes.includes(i-1)
              }"
              :title="'Chunk ' + (i-1)"
            >
              {{ i-1 }}
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button type="primary" @click="statusDialog.visible = false">
            Close
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 下载进度对话框 -->
    <el-dialog
      v-model="downloadStatus.visible"
      :title="'Download File - ' + downloadStatus.fileName"
      :width="isMobile ? '95%' : '400px'"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <div class="download-progress">
        <div class="progress-info">
          <el-icon class="download-icon"><Download /></el-icon>
          <div class="file-info">
            <div class="download-filename">{{ downloadStatus.fileName }}</div>
            <div class="download-status" :class="downloadStatus.status">
              {{ getDownloadStatusText(downloadStatus.status) }}
            </div>
          </div>
        </div>
        <el-progress 
          :percentage="downloadStatus.progress"
          :stroke-width="12"
          :status="getProgressStatus(downloadStatus.status)"
          :format="(val) => val + '%'"
          class="progress-bar"
        />
        <div class="download-actions" v-if="downloadStatus.status === 'downloading'">
          <el-button 
            type="danger" 
            @click="cancelDownload"
            :disabled="downloadStatus.status === 'canceling'"
          >
            Cancel Download
          </el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 添加元数据对话框 -->
    <el-dialog
      v-model="metadataDialog.visible"
      :title="'Music Metadata - ' + (metadataDialog.fileName || '')"
      :width="isMobile ? '95%' : '500px'"
      :fullscreen="isMobile"
    >
      <div v-if="metadataDialog.data" class="metadata-content">
        <el-form :model="metadataDialog.data" label-width="80px">
          <el-form-item label="Title">
            <el-input v-model="metadataDialog.data.title" />
          </el-form-item>
          <el-form-item label="Artist">
            <el-input v-model="metadataDialog.data.artist" />
          </el-form-item>
          <el-form-item label="Album">
            <el-input v-model="metadataDialog.data.album" />
          </el-form-item>
          <el-form-item label="Genre">
            <el-input v-model="metadataDialog.data.genre" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="metadataDialog.visible = false">Cancel</el-button>
          <el-button type="primary" @click="saveMetadata">
            Save
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getFileList, deleteFile, getUploadStatus, parseAndSaveMetadata } from '@/api/file'
import { Download, Document, Upload, Delete, ArrowDown } from '@element-plus/icons-vue'

const loading = ref(false)
const fileList = ref([])
const searchForm = ref({
  fileName: '',
  fileType: '',
  status: null
})

// 上传状态对话框
const statusDialog = ref({
  visible: false,
  data: null
})

// 下载状态管理
const downloadStatus = ref({
  visible: false,
  progress: 0,
  fileName: '',
  fileId: null,
  status: ''
})

// 添加移动端检测
const isMobile = ref(window.innerWidth <= 768)
const handleResize = () => {
  isMobile.value = window.innerWidth <= 768
}

// 在 script setup 部分添加 AbortController
const downloadAbortController = ref(null)

// 修改分页相关的响应式变量
const pagination = ref({
  current: 1,
  pageSize: 10,
  total: 0,
  pages: 0
})

// 添加元数据对话框状态
const metadataDialog = ref({
  visible: false,
  fileName: '',
  fileId: null,
  data: null
})

// 添加排序参数
const sortParams = reactive({
  orderBy: 'createTime', // 默认按上传时间排序
  orderType: 'desc' // 默认降序
})

// 获取文件列表
const fetchFileList = async () => {
  try {
    loading.value = true
    const params = {
      ...searchForm.value,
      current: pagination.value.current,
      pageSize: pagination.value.pageSize,
      orderBy: sortParams.orderBy,
      orderType: sortParams.orderType
    }
    const res = await getFileList(params)
    if (res.code === 200) {
      fileList.value = res.data.records || []
      pagination.value = {
        current: res.data.current,
        pageSize: res.data.size,
        total: res.data.total,
        pages: res.data.pages
      }
    } else {
      ElMessage.error(res.message || 'Failed to get file list')
    }
  } catch (error) {
    console.error('Failed to get file list:', error)
    ElMessage.error('Failed to get file list')
  } finally {
    loading.value = false
  }
}

// 搜索文件
const searchFiles = () => {
  pagination.value.current = 1 // Reset to first page when searching
  fetchFileList()
}

// 重置搜索
const resetSearch = () => {
  searchForm.value = {
    fileName: '',
    fileType: '',
    status: null
  }
  pagination.value.current = 1 // Reset to first page
  pagination.value.pageSize = 10 // Reset page size
  fetchFileList()
}

// 删除文件
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `Are you sure you want to delete file "${row.fileName}"?`,
      'Confirmation',
      {
        confirmButtonText: 'Confirm',
        cancelButtonText: 'Cancel',
        type: 'warning'
      }
    )
    
    const res = await deleteFile(row.id)
    if (res.code === 200) {
      ElMessage.success('File deleted successfully')
      fetchFileList()
    } else {
      ElMessage.error(res.message || 'Failed to delete file')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Delete file error:', error)
      ElMessage.error('Failed to delete file')
    }
  }
}

// 显示上传状态
const showUploadStatus = async (row) => {
  try {
    const res = await getUploadStatus(row.id)
    if (res.code === 200) {
      statusDialog.value = {
        visible: true,
        data: {
          ...res.data,
          fileName: row.fileName,
          fileType: row.fileType,
          fileSize: row.fileSize,
          progress: (res.data.uploadedChunks / res.data.chunkCount) * 100 || 0
        }
      }
    } else {
      ElMessage.error(res.message || 'Failed to get upload status')
    }
  } catch (error) {
    console.error('Get upload status error:', error)
    ElMessage.error('Failed to get upload status')
  }
}

// 下载文件
const downloadFile = async (row) => {
  try {
    // 重置下载状态
    downloadStatus.value = {
      visible: true,
      progress: 0,
      fileName: row.fileName,
      fileId: row.id,
      status: 'downloading'
    }
    
    // 创建 AbortController 用于取消下载
    downloadAbortController.value = new AbortController()
    const signal = downloadAbortController.value.signal
    
    // 创建请求
    const res = await fetch(`/api/file/download/${row.id}`, {
      method: 'GET',
      signal
    })
    
    if (!res.ok) {
      const errorData = await res.json()
      throw new Error(errorData.message || 'Download failed')
    }
    
    // 获取文件大小以便计算进度
    const contentLength = Number(res.headers.get('content-length'))
    let receivedLength = 0
    
    // 创建 ReadableStream 读取器
    const reader = res.body.getReader()
    const chunks = []
    
    // 读取数据块并更新进度
    while (true) {
      const { done, value } = await reader.read()
      
      if (done) {
        downloadStatus.value.status = 'success'
        downloadStatus.value.progress = 100
        
        // 延迟关闭下载对话框
        setTimeout(() => {
          downloadStatus.value.visible = false
        }, 1500)
        
        break
      }
      
      chunks.push(value)
      receivedLength += value.length
      
      // 更新下载进度
      if (contentLength) {
        downloadStatus.value.progress = Math.round((receivedLength / contentLength) * 100)
      }
    }
    
    // 合并所有块并创建 Blob
    const blob = new Blob(chunks)
    
    // 创建下载链接并点击
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = row.fileName
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    
  } catch (error) {
    if (error.name === 'AbortError') {
      downloadStatus.value.status = 'canceled'
      ElMessage.warning('Download canceled')
    } else {
      console.error('Download error:', error)
      downloadStatus.value.status = 'error'
      ElMessage.error(error.message || 'Download failed')
    }
    
    // 延迟关闭下载对话框
    setTimeout(() => {
      downloadStatus.value.visible = false
    }, 1500)
  } finally {
    downloadAbortController.value = null
  }
}

// 取消下载
const cancelDownload = () => {
  if (downloadAbortController.value) {
    downloadStatus.value.status = 'canceling'
    downloadAbortController.value.abort()
  }
}

// 获取下载状态文本
const getDownloadStatusText = (status) => {
  const statusMap = {
    'downloading': 'Downloading...',
    'canceling': 'Canceling...',
    'canceled': 'Download Canceled',
    'success': 'Download Complete',
    'error': 'Download Failed'
  }
  return statusMap[status] || 'Unknown Status'
}

// 获取进度条状态
const getProgressStatus = (status) => {
  const statusMap = {
    'success': 'success',
    'error': 'exception',
    'canceled': 'warning'
  }
  return statusMap[status] || ''
}

// 格式化文件大小
const formatFileSize = (size) => {
  if (!size) return '0 B'
  
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let index = 0
  let formattedSize = size
  
  while (formattedSize >= 1024 && index < units.length - 1) {
    formattedSize /= 1024
    index++
  }
  
  return `${formattedSize.toFixed(2)} ${units[index]}`
}

// 格式化时间
const formatTime = (timeStr) => {
  if (!timeStr) return ''
  
  // 简单的时间格式化，可以根据需要进行扩展
  return timeStr
}

// 分页大小改变
const handleSizeChange = (val) => {
  pagination.value.pageSize = val
  pagination.value.current = 1
  fetchFileList()
}

// 当前页改变
const handleCurrentChange = (val) => {
  pagination.value.current = val
  fetchFileList()
}

// 解析元数据
const handleParseMetadata = async (row) => {
  try {
    const res = await fetch(`/api/music/metadata/${row.id}`)
    
    if (!res.ok) {
      const errorData = await res.json()
      throw new Error(errorData.message || 'Failed to get metadata')
    }
    
    const data = await res.json()
    
    if (data.code === 200) {
      metadataDialog.value = {
        visible: true,
        fileName: row.fileName,
        fileId: row.id,
        data: {
          ...data.data,
          // 如果后端返回的数据字段不同，这里需要适配
          title: data.data.title || '',
          artist: data.data.artist || '',
          album: data.data.album || '',
          genre: data.data.genre || ''
        }
      }
    } else {
      throw new Error(data.message || 'Failed to get metadata')
    }
  } catch (error) {
    console.error('Parse metadata error:', error)
    ElMessage.error(error.message || 'Failed to get metadata')
  }
}

// 保存元数据
const saveMetadata = async () => {
  try {
    if (!metadataDialog.value.fileId || !metadataDialog.value.data) return
    
    const res = await parseAndSaveMetadata(metadataDialog.value.fileId, metadataDialog.value.data)
    
    if (res.code === 200) {
      ElMessage.success('Metadata saved successfully')
      metadataDialog.value.visible = false
    } else {
      ElMessage.error(res.message || 'Failed to save metadata')
    }
  } catch (error) {
    console.error('Save metadata error:', error)
    ElMessage.error('Failed to save metadata')
  }
}

// 处理排序变化
const handleSortChange = ({ prop, order }) => {
  if (order === 'ascending') {
    sortParams.orderType = 'asc'
  } else if (order === 'descending') {
    sortParams.orderType = 'desc'
  } else {
    // 如果取消排序，恢复默认排序
    sortParams.orderBy = 'createTime'
    sortParams.orderType = 'desc'
    fetchFileList()
    return
  }
  sortParams.orderBy = prop
  fetchFileList()
}

// 在组件挂载时获取文件列表
onMounted(() => {
  fetchFileList()
  
  // 添加窗口大小变化的监听器
  window.addEventListener('resize', handleResize)
})

// 组件卸载时，移除事件监听器
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.file-list {
  padding: 20px;
  color: #ffffff;
}

.search-bar {
  padding: 20px;
  margin-bottom: 20px;
  border-radius: 8px;
  background-color: #1e1e1e;
}

.search-form {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  align-items: flex-end;
}

.search-item {
  min-width: 200px;
  margin-bottom: 0;
}

.search-buttons {
  display: flex;
  gap: 10px;
  margin-left: auto;
  margin-bottom: 0;
}

/* Mobile file list styles */
.mobile-file-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.mobile-file-item {
  background-color: #1e1e1e;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.mobile-file-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.mobile-file-name {
  font-weight: 600;
  font-size: 16px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 70%;
  color: #ffffff;
}

.mobile-file-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 14px;
  color: #aaaaaa;
}

.mobile-file-time {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 15px;
  font-size: 14px;
  color: #aaaaaa;
}

.mobile-file-actions {
  display: flex;
  justify-content: center;
}

/* File name styling for table view */
.file-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 300px;
  display: inline-block;
  color: #ffffff;
}

/* Upload status dialog styles */
.upload-status {
  padding: 20px 0;
}

.progress-section {
  margin-top: 20px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  font-weight: 500;
  color: #ffffff;
}

.chunks-section {
  margin-top: 20px;
}

.chunks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(35px, 1fr));
  gap: 4px;
  margin-top: 10px;
}

.chunk-item {
  height: 35px;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #2d2d2d;
  border: 1px solid #444444;
  border-radius: 4px;
  cursor: default;
  color: #ffffff;
}

.chunk-item.uploaded {
  background-color: #67C23A;
  color: white;
  border-color: #67C23A;
}

.chunk-item.missing {
  background-color: #F56C6C;
  color: white;
  border-color: #F56C6C;
}

/* Responsive styles */
@media screen and (max-width: 768px) {
  .file-list {
    padding: 10px;
  }

  .search-bar {
    padding: 15px;
    margin-bottom: 15px;
  }

  .search-form {
    gap: 10px;
  }

  .search-item {
    min-width: 100%;
  }

  .search-buttons {
    width: 100%;
    justify-content: space-between;
  }

  .search-buttons .el-button {
    flex: 1;
  }

  :deep(.el-dialog__body) {
    padding: 15px !important;
  }

  :deep(.el-descriptions) {
    padding: 10px !important;
  }

  :deep(.el-descriptions__cell) {
    padding: 8px !important;
  }
}

/* Download progress styles */
.download-progress {
  padding: 20px 10px;
}

.progress-info {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  gap: 15px;
}

.download-icon {
  font-size: 32px;
  color: #ff6b81;
  background-color: rgba(255, 107, 129, 0.1);
  padding: 10px;
  border-radius: 8px;
}

.file-info {
  flex: 1;
}

.download-filename {
  font-size: 16px;
  font-weight: 500;
  color: #ffffff;
  margin-bottom: 5px;
  word-break: break-all;
}

.download-status {
  font-size: 14px;
  color: #aaaaaa;
}

.download-status.downloading {
  color: #ff6b81;
}

.download-status.success {
  color: #67C23A;
}

.download-status.error,
.download-status.canceled {
  color: #F56C6C;
}

.progress-bar {
  margin-top: 10px;
}

.download-actions {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

@media screen and (max-width: 768px) {
  .download-progress {
    padding: 15px 5px;
  }

  .download-icon {
    font-size: 28px;
    padding: 8px;
  }

  .download-filename {
    font-size: 14px;
  }

  .download-status {
    font-size: 12px;
  }

  .download-actions {
    margin-top: 15px;
  }
  
  .download-actions .el-button {
    width: 100%;
  }
}

/* Pagination styles */
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
  padding: 10px 20px;
  background-color: #1e1e1e;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

/* Mobile pagination styles */
@media screen and (max-width: 768px) {
  .pagination-container {
    justify-content: center;
    padding: 10px;
  }
  
  :deep(.el-pagination) {
    justify-content: center;
    flex-wrap: wrap;
    gap: 8px;
  }
}

/* Metadata dialog styles */
.metadata-content {
  padding: 20px 0;
}

@media screen and (max-width: 768px) {
  .metadata-content {
    padding: 10px 0;
  }
}

/* Deep selectors for Element Plus components in dark theme */
:deep(.el-button) {
  border: none;
}

:deep(.el-button--primary) {
  background-color: #ff6b81;
}

:deep(.el-dialog) {
  background-color: #1e1e1e;
  border-radius: 8px;
}

:deep(.el-dialog__title) {
  color: #ffffff;
}

:deep(.el-dialog__body) {
  color: #ffffff;
}

:deep(.el-form-item__label) {
  color: #ffffff;
}

:deep(.el-input__wrapper) {
  background-color: #2d2d2d !important;
  box-shadow: 0 0 0 1px #444444 inset !important;
}

:deep(.el-input__inner) {
  color: #ffffff !important;
}

:deep(.el-textarea__inner) {
  background-color: #2d2d2d !important;
  border-color: #444444 !important;
  color: #ffffff !important;
}

:deep(.el-table) {
  background-color: #1e1e1e !important;
  color: #ffffff !important;
}

:deep(.el-table th.el-table__cell) {
  background-color: #2d2d2d !important;
  color: #ffffff !important;
  border-bottom: 1px solid #333 !important;
}

:deep(.el-table tr) {
  background-color: #1e1e1e !important;
}

:deep(.el-table td.el-table__cell) {
  border-bottom: 1px solid #333 !important;
}

:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) {
  background-color: #2d2d2d !important;
}

/* 修复触摸时表格行变白的问题 */
:deep(.el-table__row:active),
:deep(.el-table__row.is-active),
:deep(.el-table__row.active),
:deep(.el-table__row.current-row) {
  background-color: #3a3a3a !important;
}

:deep(.el-table__cell:active) {
  background-color: transparent !important;
}

/* 禁用默认的触摸高亮 */
:deep(.el-table__row),
:deep(.el-table__cell) {
  -webkit-tap-highlight-color: transparent !important;
  transition: background-color 0.2s;
}

/* 确保表格在移动设备上的点击状态也保持深色 */
:deep(.el-table__body tr.current-row > td.el-table__cell) {
  background-color: #3a3a3a !important;
}

/* 确保当前选中行保持深色 */
:deep(.el-table__body tr.hover-row > td.el-table__cell),
:deep(.el-table__body tr.hover-row.current-row > td.el-table__cell),
:deep(.el-table__body tr.hover-row.el-table__row--striped > td.el-table__cell),
:deep(.el-table__body tr.hover-row.el-table__row--striped.current-row > td.el-table__cell) {
  background-color: #2d2d2d !important;
}

:deep(.el-pagination) {
  --el-pagination-bg-color: transparent !important;
  --el-pagination-text-color: #fff !important;
  --el-pagination-button-color: #fff !important;
  --el-pagination-hover-color: #ff6b81 !important;
  --el-pagination-button-bg-color: #2d2d2d !important;
  --el-pagination-button-disabled-bg-color: #1e1e1e !important;
}

/* 确保分页组件的触摸状态也是深色的 */
:deep(.el-pager li:active) {
  color: #ffffff !important;
  background-color: #3a3a3a !important;
}

:deep(.el-descriptions__cell) {
  background-color: #2d2d2d !important;
}

:deep(.el-descriptions__label) {
  color: #aaa !important;
}

:deep(.el-descriptions__content) {
  color: #fff !important;
}

:deep(.el-select-dropdown) {
  background-color: #2d2d2d !important;
  border: 1px solid #333 !important;
}

:deep(.el-select-dropdown__item) {
  color: #fff !important;
}

:deep(.el-select-dropdown__item.hover), 
:deep(.el-select-dropdown__item:hover) {
  background-color: #3d3d3d !important;
}

/* 确保下拉选项在触摸时也保持深色 */
:deep(.el-select-dropdown__item:active) {
  background-color: #3a3a3a !important;
}

:deep(.el-tag) {
  background-color: transparent !important;
}

:deep(.el-tag--success) {
  border-color: #67C23A !important;
  color: #67C23A !important;
}

:deep(.el-tag--warning) {
  border-color: #E6A23C !important;
  color: #E6A23C !important;
}

:deep(.el-progress-bar__outer) {
  background-color: #2d2d2d !important;
}

:deep(.el-progress-bar__inner) {
  background-color: #ff6b81 !important;
}

:deep(.el-progress.is-success .el-progress-bar__inner) {
  background-color: #67C23A !important;
}

:deep(.el-progress.is-warning .el-progress-bar__inner) {
  background-color: #E6A23C !important;
}

:deep(.el-progress.is-exception .el-progress-bar__inner) {
  background-color: #F56C6C !important;
}

/* 添加下拉菜单的深色主题样式 */
:deep(.el-dropdown-menu) {
  background-color: #2d2d2d !important;
  border: 1px solid #444 !important;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.4) !important;
}

:deep(.el-dropdown-menu__item) {
  color: #ffffff !important;
}

:deep(.el-dropdown-menu__item:hover) {
  background-color: #3d3d3d !important;
}

:deep(.el-dropdown-menu__item.danger-item) {
  color: #F56C6C !important;
}

:deep(.el-dropdown-menu__item.danger-item:hover) {
  background-color: rgba(245, 108, 108, 0.1) !important;
}

:deep(.el-dropdown-menu__item i) {
  margin-right: 5px;
}

:deep(.el-dropdown .el-dropdown-selfdefine) {
  display: flex;
  align-items: center;
}

.mobile-file-actions {
  display: flex;
  justify-content: center;
}

/* 修改移动端布局 */
@media screen and (max-width: 768px) {
  .mobile-file-actions .el-button {
    width: 100%;
  }
}

/* 状态标签样式 */
.status-tag {
  padding: 0 8px;
  height: 24px;
  line-height: 22px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

@media screen and (max-width: 768px) {
  .status-tag {
    font-size: 11px;
    padding: 0 6px;
    height: 22px;
    line-height: 20px;
  }
}
</style> 