<template>
  <div class="upload-container">
    <div class="upload-card">
      <h2 class="page-title">文件上传</h2>
      
      <!-- 上传区域 -->
      <el-upload
        class="upload-area"
        drag
        multiple
        :auto-upload="false"
        :data="uploadData"
        :on-preview="handlePreview"
        :on-remove="handleRemove"
        :before-remove="beforeRemove"
        :on-success="handleSuccess"
        :on-error="handleError"
        :on-change="handleFileChange"
        :before-upload="beforeUpload"
      >
        <div class="upload-inner">
          <el-icon class="upload-icon"><upload-filled /></el-icon>
          <div class="upload-text">
            拖拽文件到此处或 <em>点击上传</em>
          </div>
          <div class="upload-tip">
            文件大小不超过10GB
          </div>
        </div>
      </el-upload>
      
      <!-- 上传队列 -->
      <div v-if="uploadQueue.length > 0" class="upload-queue">
        <div class="queue-title">上传队列（{{ uploadQueue.length }}个文件）</div>
        <div class="queue-list">
          <div v-for="(item, index) in uploadQueue" 
               :key="item.file.name + index"
               class="queue-item"
               :class="{ 'current': currentFile && currentFile.name === item.file.name }">
            <div class="queue-item-info">
              <el-icon class="queue-file-icon"><document /></el-icon>
              <div class="queue-file-details">
                <div class="queue-file-name">{{ item.file.name }}</div>
                <div class="queue-file-size">{{ formatFileSize(item.file.size) }}</div>
              </div>
              <div class="queue-status" :class="item.status">
                {{ getStatusText(item.status) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    
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
              {{ isPaused ? '继续上传' : '暂停上传' }}
            </el-button>
            <el-button 
              v-if="uploadStatus === 'exception'"
              type="primary" 
              size="large"
              class="action-button"
              @click="retryUpload"
            >
              <el-icon><refresh /></el-icon>
              重新上传
            </el-button>
            <el-button 
              v-if="uploadStatus !== 'success'"
              type="danger" 
              size="large"
              class="action-button"
              @click="cancelUpload"
            >
              <el-icon><close /></el-icon>
              取消上传
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { UploadFilled, Document, CircleCheck, CircleClose, Loading, VideoPause, VideoPlay, Refresh, Close } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ref, computed } from 'vue'
import { checkFile, uploadChunk, mergeChunks, createFile, getMissingChunks } from '@/api/file'
import SparkMD5 from 'spark-md5'

const currentFile = ref(null)
const uploadProgress = ref(0)
const uploadStatus = ref('')
const isPaused = ref(false)
const uploadQueue = ref([]) // 上传队列
const isUploading = ref(false) // 是否正在上传
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

const handlePreview = (file) => {
  console.log(file)
}

const handleRemove = (file, uploadFiles) => {
  console.log(file, uploadFiles)
}

const beforeRemove = (file, uploadFiles) => {
  return ElMessageBox.confirm(`确定移除 ${file.name}？`)
}

const handleSuccess = (response) => {
  if (response.code === 200) {
    ElMessage.success('分片上传成功')
    // 更新上传进度
    uploadProgress.value = (uploadData.value.chunkIndex + 1) / currentFile.value.totalChunks * 100
    // 更新分片索引
    uploadData.value.chunkIndex++
    // 如果是最后一个分片，请求合并
    if (uploadData.value.chunkIndex === currentFile.value.totalChunks) {
      mergeFile()
    }
  } else {
    ElMessage.error(response.message || '上传失败')
  }
}

const handleError = (error) => {
  console.error('上传错误：', error)
  ElMessage.error('上传失败')
}

// 合并文件
const mergeFile = async () => {
  try {
    uploadStatus.value = 'warning'
    if (uploadQueue.value.length > 0) {
      uploadQueue.value[0].status = 'uploading'
    }
    
    const res = await mergeChunks(uploadData.value.fileId)
    if (res.code === 200) {
      ElMessage.success('文件合并成功')
      uploadStatus.value = 'success'
      // 更新队列中的状态并移除已完成的文件
      if (uploadQueue.value.length > 0) {
        const completedFile = uploadQueue.value.shift()
        completedFile.status = 'success'
      }
      // 重置当前文件状态
      currentFile.value = null
      uploadProgress.value = 0
      uploadStatus.value = ''
      uploadData.value = {
        fileId: null,
        chunkIndex: 0,
        chunkMd5: ''
      }
      isUploading.value = false
      
      // 继续处理队列中的下一个文件
      if (uploadQueue.value.length > 0) {
        processQueue()
      }
    } else {
      const errorMsg = res.message || '文件合并失败'
      ElMessage({
        message: errorMsg,
        type: 'error',
        duration: 5000,
        showClose: true
      })
      uploadStatus.value = 'exception'
      if (uploadQueue.value.length > 0) {
        uploadQueue.value[0].status = 'error'
      }
    }
  } catch (error) {
    console.error('合并错误：', error)
    ElMessage({
      message: '文件合并失败: ' + (error.message || '未知错误'),
      type: 'error',
      duration: 5000,
      showClose: true
    })
    uploadStatus.value = 'exception'
    if (uploadQueue.value.length > 0) {
      uploadQueue.value[0].status = 'error'
    }
  }
}

// 文件选择处理
const handleFileChange = async (file, fileList) => {
  if (!file) return
  
  // 获取实际的文件对象
  const actualFile = file.raw || file
  
  // 检查文件大小（10GB）
  if (actualFile.size > 10 * 1024 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过10GB')
    return
  }

  // 检查文件是否已在队列中
  const isFileInQueue = uploadQueue.value.some(item => 
    item.file.name === actualFile.name && item.file.size === actualFile.size
  )

  if (isFileInQueue) {
    ElMessage.warning('该文件已在上传队列中')
    return
  }

  // 将新文件添加到上传队列
  uploadQueue.value.push({
    file: actualFile,
    status: 'waiting',
    progress: 0,
    md5: '',
    totalChunks: 0
  })

  // 如果当前没有文件在上传，开始上传队列
  if (!isUploading.value) {
    processQueue()
  }
}

// 处理上传队列
const processQueue = async () => {
  if (uploadQueue.value.length === 0 || isUploading.value) return

  isUploading.value = true
  const queueItem = uploadQueue.value[0]
  currentFile.value = queueItem.file
  uploadProgress.value = 0
  uploadStatus.value = ''

  try {
    // 计算文件MD5
    queueItem.md5 = await calculateFileMD5(queueItem.file)
    currentFile.value.md5 = queueItem.md5

    // 检查文件是否已存在
    const res = await checkFile(queueItem.md5)
    if (res.code === 200) {
      if (res.data.exists) {
        ElMessage.success(`文件 ${queueItem.file.name} 秒传成功！`)
        completeCurrentFile('success')
      } else if (res.data.fileId) {
        // 文件存在未完成的上传记录，继续上传
        uploadData.value.fileId = res.data.fileId
        queueItem.totalChunks = Math.ceil(queueItem.file.size / (5 * 1024 * 1024))
        currentFile.value.totalChunks = queueItem.totalChunks
        ElMessage.info('发现未完成的上传记录，继续上传')
        await startUploadChunks(true)
      } else {
        // 创建新的文件记录
        const createRes = await createFile({
          fileName: queueItem.file.name,
          fileSize: queueItem.file.size,
          fileMd5: queueItem.md5,
          chunkCount: Math.ceil(queueItem.file.size / (5 * 1024 * 1024))
        })
        
        if (createRes.code === 200) {
          uploadData.value.fileId = createRes.data.id
          queueItem.totalChunks = Math.ceil(queueItem.file.size / (5 * 1024 * 1024))
          currentFile.value.totalChunks = queueItem.totalChunks
          uploadData.value.chunkIndex = 0
          await startUploadChunks(false)
        } else {
          ElMessage.error(createRes.message || '创建文件记录失败')
          completeCurrentFile('error')
        }
      }
    } else {
      ElMessage.error(res.message || '文件检查失败')
      completeCurrentFile('error')
    }
  } catch (error) {
    console.error('文件处理失败：', error)
    ElMessage.error('文件处理失败')
    completeCurrentFile('error')
  }
}

// 完成当前文件上传
const completeCurrentFile = (status) => {
  if (uploadQueue.value.length > 0) {
    const queueItem = uploadQueue.value.shift()
    queueItem.status = status
  }
  
  currentFile.value = null
  uploadProgress.value = 0
  uploadStatus.value = ''
  uploadData.value = {
    fileId: null,
    chunkIndex: 0,
    chunkMd5: ''
  }
  
  isUploading.value = false
  
  // 继续处理队列中的下一个文件
  if (uploadQueue.value.length > 0) {
    setTimeout(() => {
      processQueue()
    }, 1000) // 添加短暂延迟，确保状态正确更新
  }
}

// 暂停/继续上传
const togglePause = () => {
  isPaused.value = !isPaused.value
  if (!isPaused.value) {
    // 继续上传
    startUploadChunks(true)
  }
}

// 重试上传
const retryUpload = async () => {
  try {
    uploadStatus.value = ''
    isPaused.value = false
    // 获取缺失的分片并重新上传
    await startUploadChunks(true)
  } catch (error) {
    console.error('重试上传失败：', error)
    ElMessage.error('重试上传失败')
    uploadStatus.value = 'exception'
  }
}

// 修改 startUploadChunks 方法
const startUploadChunks = async (isResume = false) => {
  const chunkSize = 5 * 1024 * 1024 // 5MB
  const file = currentFile.value
  const totalChunks = Math.ceil(file.size / chunkSize)
  const concurrentLimit = 10 // 并发上传数量限制
  
  // 更新当前文件状态为上传中
  if (uploadQueue.value.length > 0) {
    uploadQueue.value[0].status = 'uploading'
  }
  
  try {
    // 只有在断点续传时才获取缺失的分片
    let missingChunks = []
    if (isResume) {
      const res = await getMissingChunks(uploadData.value.fileId)
      if (res.code === 200) {
        missingChunks = res.data
        if (missingChunks.length === 0) {
          // 如果没有缺失的分片，直接开始合并
          ElMessage.success('所有分片已上传，开始合并文件...')
          await mergeFile()
          return
        }
        ElMessage.info(`发现${missingChunks.length}个未完成的分片，继续上传`)
      }
    }
  
    // 创建上传任务，如果是断点续传，则只上传缺失的分片
    const uploadTasks = []
    const chunksToUpload = isResume ? missingChunks : Array.from(Array(totalChunks).keys())
    
    for (const i of chunksToUpload) {
      const start = i * chunkSize
      const end = Math.min(start + chunkSize, file.size)
      const chunk = file.slice(start, end)
      
      const formData = new FormData()
      formData.append('fileId', uploadData.value.fileId)
      formData.append('chunkIndex', i)
      formData.append('chunk', chunk)
      formData.append('chunkMd5', await calculateFileMD5(chunk))
      
      uploadTasks.push({
        index: i,
        formData: formData
      })
    }
    
    let allChunksUploaded = true
    let completedChunks = totalChunks - chunksToUpload.length // 已经上传的分片数
    
    // 分批上传分片
    for (let i = 0; i < uploadTasks.length; i += concurrentLimit) {
      // 如果已暂停，退出上传循环
      if (isPaused.value) {
        if (uploadQueue.value.length > 0) {
          uploadQueue.value[0].status = 'waiting'
        }
        return
      }

      const batch = uploadTasks.slice(i, i + concurrentLimit)
      const batchPromises = batch.map(task => 
        uploadChunk(task.formData)
          .then(res => {
            if (res.code === 200) {
              completedChunks++
              uploadProgress.value = (completedChunks / totalChunks) * 100
              // 更新队列中当前文件的进度
              if (uploadQueue.value.length > 0) {
                uploadQueue.value[0].progress = uploadProgress.value
              }
              return res
            } else {
              allChunksUploaded = false
              throw new Error(`分片${task.index}上传失败: ${res.message || '未知错误'}`)
            }
          })
          .catch(error => {
            console.error(`分片${task.index}上传错误:`, error)
            throw error
          })
      )
      
      try {
        await Promise.all(batchPromises)
      } catch (error) {
        console.error('分片上传错误：', error)
        ElMessage({
          message: error.message || '分片上传失败',
          type: 'error',
          duration: 5000,
          showClose: true
        })
        allChunksUploaded = false
        uploadStatus.value = 'exception'
        if (uploadQueue.value.length > 0) {
          uploadQueue.value[0].status = 'error'
        }
        break
      }
    }
    
    // 如果上传被暂停，不执行合并操作
    if (isPaused.value) {
      return
    }
    
    if (allChunksUploaded && completedChunks === totalChunks) {
      ElMessage.success('所有分片上传完成，开始合并文件...')
      await mergeFile()
    } else if (!isPaused.value) { // 只有在非暂停状态下才显示错误
      const errorMessage = '部分分片上传失败，您可以点击重试按钮继续上传'
      ElMessage({
        message: errorMessage,
        type: 'warning',
        duration: 5000,
        showClose: true
      })
      uploadStatus.value = 'exception'
      if (uploadQueue.value.length > 0) {
        uploadQueue.value[0].status = 'error'
      }
    }
  } catch (error) {
    console.error('上传过程出错：', error)
    ElMessage.error('上传过程出错，请重试')
    uploadStatus.value = 'exception'
    if (uploadQueue.value.length > 0) {
      uploadQueue.value[0].status = 'error'
    }
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

// 在 script setup 部分添加格式化函数
const percentageFormat = (percentage) => {
  if (!percentage) return '0%'
  return `${Math.floor(percentage)}%`
}

// 修改 progressStatusText 计算属性
const progressStatusText = computed(() => {
  if (!currentFile.value) return ''
  
  if (uploadStatus.value === 'success') {
    return '文件上传完成！'
  } else if (uploadStatus.value === 'exception') {
    return '上传失败，请重试'
  } else if (uploadStatus.value === 'warning') {
    return '文件合并中，请耐心等待...'
  } else if (isPaused.value) {
    return '上传已暂停'
  } else if (uploadProgress.value === 0) {
    return '准备上传文件...'
  } else if (uploadProgress.value < 100) {
    return `正在上传分片，完成${Math.floor(uploadProgress.value)}%`
  } else {
    return '上传完成，准备合并文件...'
  }
})

// 取消上传
const cancelUpload = async () => {
  try {
    await ElMessageBox.confirm('确定要取消上传吗？已上传的部分将被丢弃。', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    // 重置所有状态
    uploadQueue.value = [] // 清空上传队列
    completeCurrentFile('error')
    
    ElMessage.info('已取消上传')
  } catch (error) {
    // 用户取消操作，不做处理
  }
}

// 获取状态文本
const getStatusText = (status) => {
  switch (status) {
    case 'waiting':
      return '等待上传'
    case 'uploading':
      return '上传中'
    case 'success':
      return '上传成功'
    case 'error':
      return '上传失败'
    default:
      return '未知状态'
  }
}
</script>

<style scoped>
.upload-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 70vh;
  padding: 20px;
  background-color: #f5f7fa;
}

.upload-card {
  width: 100%;
  max-width: 900px;
  background-color: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  padding: 30px;
  transition: all 0.3s ease;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 30px;
  text-align: center;
  position: relative;
}

.page-title::after {
  content: "";
  position: absolute;
  bottom: -10px;
  left: 50%;
  transform: translateX(-50%);
  width: 80px;
  height: 3px;
  background: linear-gradient(90deg, #409EFF, #67C23A);
  border-radius: 3px;
}

.upload-area {
  margin-bottom: 30px;
}

.upload-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px 0;
}

.upload-icon {
  font-size: 64px;
  color: #409EFF;
  margin-bottom: 16px;
  transition: transform 0.3s;
}

.upload-area:hover .upload-icon {
  transform: scale(1.1);
}

.upload-text {
  font-size: 16px;
  color: #606266;
  margin-bottom: 8px;
}

.upload-text em {
  font-style: normal;
  color: #409EFF;
  font-weight: 600;
  cursor: pointer;
}

.upload-tip {
  font-size: 14px;
  color: #909399;
  margin-top: 8px;
}

.file-info-card {
  background-color: #f8f9fb;
  border-radius: 10px;
  padding: 24px;
  margin-top: 30px;
  border-left: 4px solid #409EFF;
  transition: all 0.3s;
}

.success-card {
  border-left: 4px solid #67C23A;
  background-color: #f0f9eb;
}

.file-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.file-icon {
  font-size: 32px;
  margin-right: 16px;
  color: #409EFF;
  background-color: rgba(64, 158, 255, 0.1);
  padding: 10px;
  border-radius: 8px;
}

.file-details {
  flex: 1;
}

.file-name {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
  word-break: break-all;
}

.file-size {
  font-size: 14px;
  color: #606266;
  margin-bottom: 4px;
}

.progress-container {
  display: flex;
  flex-direction: column;
  margin-top: 15px;
}

.upload-progress {
  width: 100%;
}

.progress-status-text {
  display: flex;
  align-items: center;
  margin-top: 12px;
  font-size: 15px;
  color: #606266;
  transition: color 0.3s;
  padding: 0 8px;
}

.success {
  color: #67C23A;
  font-weight: 600;
}

.warning {
  color: #E6A23C;
  font-weight: 600;
}

.exception {
  color: #F56C6C;
  font-weight: 600;
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
  margin-top: 24px;
  display: flex;
  gap: 16px;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
}

.action-button {
  min-width: 140px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 8px;
  font-weight: 500;
  letter-spacing: 0.5px;
  transition: all 0.3s ease;
}

.action-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.el-icon {
  font-size: 18px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .upload-card {
    padding: 20px;
  }
  
  .page-title {
    font-size: 24px;
  }
  
  .control-buttons {
    flex-direction: column;
    width: 100%;
  }
  
  .action-button {
    width: 100%;
  }
}

.upload-queue {
  margin-top: 30px;
  background-color: #f8f9fb;
  border-radius: 10px;
  padding: 20px;
}

.queue-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
}

.queue-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.queue-item {
  background-color: #ffffff;
  border-radius: 8px;
  padding: 12px;
  border: 1px solid #ebeef5;
  transition: all 0.3s;
}

.queue-item.current {
  border-color: #409EFF;
  background-color: #ecf5ff;
}

.queue-item-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.queue-file-icon {
  font-size: 24px;
  color: #909399;
}

.queue-file-details {
  flex: 1;
  min-width: 0;
}

.queue-file-name {
  font-size: 14px;
  color: #303133;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.queue-file-size {
  font-size: 12px;
  color: #909399;
}

.queue-status {
  font-size: 13px;
  padding: 4px 8px;
  border-radius: 4px;
  background-color: #f4f4f5;
  color: #909399;
}

.queue-status.waiting {
  background-color: #e9f2ff;
  color: #409EFF;
}

.queue-status.uploading {
  background-color: #fdf6ec;
  color: #e6a23c;
}

.queue-status.success {
  background-color: #f0f9eb;
  color: #67c23a;
}

.queue-status.error {
  background-color: #fef0f0;
  color: #f56c6c;
}
</style>