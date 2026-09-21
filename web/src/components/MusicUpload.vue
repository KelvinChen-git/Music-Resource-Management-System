<template>
  <div class="music-upload">
    <el-upload
      class="upload-area"
      drag
      :auto-upload="false"
      :show-file-list="false"
      :on-change="handleFileChange"
      :before-upload="beforeUpload"
    >
      <div class="upload-inner">
        <div class="upload-icon-container">
          <el-icon class="upload-icon"><upload-filled /></el-icon>
        </div>
        <div class="upload-text">
          click to upload
        </div>
        <div class="upload-tip">
          Supports MP3 files
        </div>
      </div>
    </el-upload>

    <!-- 当前文件上传进度 -->
    <div v-if="currentFile" class="file-info-card" :class="{ 'success-card': uploadStatus === 'success' }">
      <div class="file-header">
        <el-icon class="file-icon"><document /></el-icon>
        <div class="file-details">
          <div class="file-name">{{ currentFile.name }}</div>
          <div class="file-size">{{ formatFileSize(currentFile.size) }}</div>
        </div>
      </div>
      <div class="progress-container">
        <el-progress 
          :percentage="Math.floor(uploadProgress)" 
          :status="uploadStatus"
          :stroke-width="12"
          :format="percentageFormat"
          class="upload-progress"
        />
        <div class="progress-status-text" :class="uploadStatus">
          <span class="status-icon" v-if="uploadStatus">
            <el-icon v-if="uploadStatus === 'success'"><circle-check /></el-icon>
            <el-icon v-else-if="uploadStatus === 'exception'"><circle-close /></el-icon>
            <el-icon v-else-if="uploadStatus === 'warning'" class="loading-icon"><loading /></el-icon>
          </span>
          {{ progressStatusText }}
        </div>
        <div class="control-buttons">
          <el-button 
            v-if="uploadStatus === 'exception'"
            type="primary" 
            size="large"
            class="action-button"
            @click="resetUpload"
          >
            <el-icon><Back /></el-icon>
            Choose Another File
          </el-button>
          <el-button 
            v-if="uploadStatus !== 'success' && uploadStatus !== 'exception'"
            :type="isPaused ? 'primary' : 'warning'"
            size="large"
            class="action-button"
            @click="togglePause"
          >
            <el-icon>
              <video-play v-if="isPaused" />
              <video-pause v-else />
            </el-icon>
            {{ isPaused ? 'Resume Upload' : 'Pause Upload' }}
          </el-button>
          <el-button 
            v-if="uploadStatus === 'exception'"
            type="primary" 
            size="large"
            class="action-button"
            @click="retryUpload"
          >
            <el-icon><refresh /></el-icon>
            Retry Upload
          </el-button>
          <el-button 
            v-if="uploadStatus !== 'success'"
            type="danger" 
            size="large"
            class="action-button"
            @click="cancelUpload"
          >
            <el-icon><close /></el-icon>
            Cancel Upload
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { checkFile, uploadChunk, mergeChunks, createFile, getMissingChunks } from '@/api/file'
import { UploadFilled, Document, CircleCheck, CircleClose, Loading, VideoPause, VideoPlay, Refresh, Close, Back } from '@element-plus/icons-vue'
import SparkMD5 from 'spark-md5'

// 定义常量
const CHUNK_SIZE = 1 * 1024 * 1024 // 1MB 分片大小

const emit = defineEmits(['upload-complete'])

const currentFile = ref(null)
const uploadProgress = ref(0)
const uploadStatus = ref('')
const isPaused = ref(false)
const uploadData = ref({
  fileId: null,
  chunkIndex: 0,
  chunkMd5: ''
})

// 计算文件MD5
const calculateFileMD5 = async (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.readAsArrayBuffer(file)
    reader.onload = (e) => {
      const spark = new SparkMD5.ArrayBuffer()
      spark.append(e.target.result)
      resolve(spark.end())
    }
    reader.onerror = reject
  })
}

// 上传前处理
const beforeUpload = () => {
  return false // 阻止自动上传
}

// 文件选择处理
const handleFileChange = async (file) => {
  if (!file) return
  
  // 获取实际的文件对象
  const actualFile = file.raw || file
  
  // 检查文件大小（100MB）
  if (actualFile.size > 100 * 1024 * 1024) {
    ElMessage.error('File size cannot exceed 100MB, please select a smaller file')
    return
  }

  // 检查文件类型
  if (!actualFile.type.includes('audio/mp3') && !actualFile.name.toLowerCase().endsWith('.mp3')) {
    ElMessage.error('Only MP3 files are supported')
    return
  }

  // 开始上传流程
  currentFile.value = actualFile
  uploadProgress.value = 0
  uploadStatus.value = ''
  await startUpload()
}

// 开始上传
const startUpload = async () => {
  try {
    // 计算文件MD5
    const fileMd5 = await calculateFileMD5(currentFile.value)
    currentFile.value.md5 = fileMd5

    // 检查文件是否已存在
    const res = await checkFile(fileMd5)
    if (res.code === 200) {
      if (res.data.exists) {
        ElMessage.success('File instant upload successful!')
        handleUploadSuccess(res.data.fileId)
      } else if (res.data.fileId) {
        // 继续未完成的上传
        uploadData.value.fileId = res.data.fileId
        currentFile.value.totalChunks = Math.ceil(currentFile.value.size / CHUNK_SIZE)
        ElMessage.info('Unfinished upload record found, continuing upload')
        await startUploadChunks(true)
      } else {
        // 创建新的文件记录
        const createRes = await createFile({
          fileName: currentFile.value.name,
          fileSize: currentFile.value.size,
          fileMd5: fileMd5,
          chunkCount: Math.ceil(currentFile.value.size / CHUNK_SIZE)
        })
        
        if (createRes.code === 200) {
          uploadData.value.fileId = createRes.data.id
          currentFile.value.totalChunks = Math.ceil(currentFile.value.size / CHUNK_SIZE)
          uploadData.value.chunkIndex = 0
          await startUploadChunks(false)
        } else {
          ElMessage.error(createRes.message || 'Failed to create file record')
          uploadStatus.value = 'exception'
        }
      }
    }
  } catch (error) {
    console.error('Upload processing failed:', error)
    ElMessage.error('Upload processing failed')
    uploadStatus.value = 'exception'
  }
}

// 上传分片
const startUploadChunks = async (isResume = false) => {
  const file = currentFile.value
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE)
  
  try {
    // 获取缺失的分片
    let missingChunks = []
    if (isResume) {
      const res = await getMissingChunks(uploadData.value.fileId)
      if (res.code === 200) {
        missingChunks = res.data
        if (missingChunks.length === 0) {
          await mergeFile()
          return
        }
      } else {
        throw new Error(res.message || 'Failed to get missing chunks information')
      }
    }
    
    const chunksToUpload = isResume ? missingChunks : Array.from(Array(totalChunks).keys())
    let completedChunks = totalChunks - chunksToUpload.length
    
    for (const i of chunksToUpload) {
      if (isPaused.value) return
      
      const start = i * CHUNK_SIZE
      const end = Math.min(start + CHUNK_SIZE, file.size)
      const chunk = file.slice(start, end)
      
      const formData = new FormData()
      formData.append('fileId', uploadData.value.fileId)
      formData.append('chunkIndex', i)
      formData.append('chunk', chunk)
      formData.append('chunkMd5', await calculateFileMD5(chunk))
      
      try {
        const res = await uploadChunk(formData)
        if (res.code === 200) {
          completedChunks++
          uploadProgress.value = (completedChunks / totalChunks) * 100
        } else {
          throw new Error(res.message || 'Chunk upload failed')
        }
      } catch (error) {
        console.error(`Chunk ${i} upload failed:`, error)
        if (error.message?.includes('network') || !navigator.onLine) {
          ElMessage.error('Upload interrupted due to network issues')
          isPaused.value = true
        } else {
          ElMessage.error('Upload failed, please retry')
        }
        uploadStatus.value = 'exception'
        return
      }
    }
    
    if (!isPaused.value) {
      await mergeFile()
    }
  } catch (error) {
    console.error('Upload process error:', error)
    if (!navigator.onLine) {
      ElMessage.error('Network connection lost, upload paused')
      isPaused.value = true
    } else {
      ElMessage.error('Upload process error, please retry')
    }
    uploadStatus.value = 'exception'
  }
}

// 合并文件
const mergeFile = async () => {
  try {
    uploadStatus.value = 'warning'
    const res = await mergeChunks(uploadData.value.fileId)
    if (res.code === 200) {
      ElMessage.success('File upload successful')
      uploadStatus.value = 'success'
      // 触发上传完成事件，传递文件ID和文件名
      emit('upload-complete', {
        fileId: uploadData.value.fileId,
        fileName: currentFile.value.name
      })
      // 延迟重置上传状态
      setTimeout(() => {
        resetUpload()
      }, 2000)
    } else {
      throw new Error(res.message || 'File merge failed')
    }
  } catch (error) {
    console.error('Merge error:', error)
    ElMessage.error('File merge failed: ' + error.message)
    uploadStatus.value = 'exception'
  }
}

// 上传成功处理
const handleUploadSuccess = (fileId) => {
  uploadStatus.value = 'success'
  uploadProgress.value = 100
  // 触发上传完成事件
  emit('upload-complete', {
    fileId: fileId,
    fileName: currentFile.value.name
  })
  // 延迟重置上传状态
  setTimeout(() => {
    resetUpload()
  }, 2000)
}

// 重置上传状态
const resetUpload = () => {
  currentFile.value = null
  uploadProgress.value = 0
  uploadStatus.value = ''
  uploadData.value = {
    fileId: null,
    chunkIndex: 0,
    chunkMd5: ''
  }
  isPaused.value = false
}

// 暂停/继续上传
const togglePause = async () => {
  isPaused.value = !isPaused.value
  if (!isPaused.value) {
    try {
      // 获取缺失的分片
      const res = await getMissingChunks(uploadData.value.fileId)
      if (res.code === 200) {
        const missingChunks = res.data
        if (missingChunks.length === 0) {
          // 如果没有缺失的分片，直接执行合并
          await mergeFile()
        } else {
          // 继续上传缺失的分片
          await startUploadChunks(true)
        }
      } else {
        throw new Error(res.message || 'Failed to get missing chunks information')
      }
    } catch (error) {
      console.error('Resume upload failed:', error)
      ElMessage.error('Resume upload failed, please retry')
      uploadStatus.value = 'exception'
    }
  }
}

// 重试上传
const retryUpload = async () => {
  try {
    uploadStatus.value = ''
    isPaused.value = false
    // 获取缺失的分片
    const res = await getMissingChunks(uploadData.value.fileId)
    if (res.code === 200) {
      const missingChunks = res.data
      if (missingChunks.length === 0) {
        // 如果没有缺失的分片，直接执行合并
        await mergeFile()
      } else {
        // 继续上传缺失的分片
        await startUploadChunks(true)
      }
    } else {
      throw new Error(res.message || 'Failed to get missing chunks information')
    }
  } catch (error) {
    console.error('Retry upload failed:', error)
    ElMessage.error('Retry upload failed, please try again')
    uploadStatus.value = 'exception'
  }
}

// 取消上传
const cancelUpload = async () => {
  try {
    await ElMessageBox.confirm('Are you sure you want to cancel the upload? The uploaded parts will be discarded.', 'Warning', {
      confirmButtonText: 'Confirm',
      cancelButtonText: 'Cancel',
      type: 'warning'
    })
    resetUpload()
    ElMessage.info('Upload canceled')
  } catch (error) {
    // 用户取消操作，不做处理
  }
}

// 格式化文件大小
const formatFileSize = (size) => {
  if (size < 1024) {
    return size + ' B'
  } else if (size < 1024 * 1024) {
    return (size / 1024).toFixed(2) + ' KB'
  } else if (size < 1024 * 1024 * 1024) {
    return (size / (1024 * 1024)).toFixed(2) + ' MB'
  } else {
    return (size / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
  }
}

// 格式化进度
const percentageFormat = (percentage) => {
  if (!percentage) return '0%'
  return `${Math.floor(percentage)}%`
}

// 修改进度状态文本的计算属性
const progressStatusText = computed(() => {
  if (!currentFile.value) return ''
  
  if (uploadStatus.value === 'success') {
    return 'Upload completed!'
  } else if (uploadStatus.value === 'exception') {
    if (!navigator.onLine) {
      return 'Network connection lost, please check your network and retry'
    }
    return 'Upload failed, please retry'
  } else if (uploadStatus.value === 'warning') {
    return 'Merging file, please wait...'
  } else if (isPaused.value) {
    return 'Upload paused'
  } else if (uploadProgress.value === 0) {
    return 'Preparing to upload file...'
  } else if (uploadProgress.value < 100) {
    return `Uploading chunks, ${Math.floor(uploadProgress.value)}% completed`
  } else {
    return 'Upload complete, merging file...'
  }
})
</script>

<style scoped>
.music-upload {
  width: 100%;
}

.upload-area {
  width: 100%;
  border: 1px dashed #ff6b81;
  border-radius: 8px;
  transition: all 0.3s;
  background-color: transparent;
}

.upload-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: #ffffff;
}

.upload-icon-container {
  background-color: #ff6b81;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.upload-icon {
  font-size: 32px;
  color: white;
  transition: transform 0.3s;
}

.upload-area:hover .upload-icon {
  transform: scale(1.1);
}

.upload-text {
  font-size: 16px;
  color: #ff6b81;
  margin-bottom: 8px;
}

.upload-tip {
  font-size: 14px;
  color: #909399;
}

.file-info-card {
  background-color: #1e1e1e;
  border-radius: 8px;
  padding: 20px;
  margin-top: 20px;
  border-left: 4px solid #ff6b81;
  transition: all 0.3s;
}

.success-card {
  border-left: 4px solid #67C23A;
  background-color: #1e1e1e;
}

.file-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.file-icon {
  font-size: 32px;
  margin-right: 16px;
  color: #ff6b81;
  background-color: rgba(255, 107, 129, 0.1);
  padding: 8px;
  border-radius: 8px;
}

.file-details {
  flex: 1;
}

.file-name {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 4px;
  word-break: break-all;
}

.file-size {
  font-size: 14px;
  color: #909399;
}

.progress-container {
  display: flex;
  flex-direction: column;
}

.progress-status-text {
  display: flex;
  align-items: center;
  margin-top: 12px;
  font-size: 14px;
  color: #909399;
}

.progress-status-text.success {
  color: #67C23A;
}

.progress-status-text.warning {
  color: #E6A23C;
}

.progress-status-text.exception {
  color: #F56C6C;
}

.status-icon {
  margin-right: 8px;
  display: inline-flex;
  align-items: center;
}

.loading-icon {
  animation: spin 1.2s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.control-buttons {
  margin-top: 20px;
  display: flex;
  gap: 12px;
  justify-content: center;
}

.action-button {
  min-width: 120px;
  background-color: #2d2d2d;
  border: none;
  color: #ffffff;
}

.action-button:hover {
  background-color: #ff6b81;
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

@media (max-width: 768px) {
  .control-buttons {
    flex-direction: column;
  }
  
  .action-button {
    width: 100%;
  }
}

:deep(.el-upload-dragger) {
  background-color: transparent;
  border: none;
  padding: 0;
}

:deep(.el-upload) {
  width: 100%;
}
</style> 