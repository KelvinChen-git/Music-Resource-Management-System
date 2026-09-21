<template>
  <div class="home">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card class="welcome-card">
          <template #header>
            <div class="card-header">
              <h2>欢迎使用文件上传系统</h2>
            </div>
          </template>
          <div class="card-content">
            <el-row :gutter="20">
              <el-col :span="12">
                <div class="feature-box" @click="$router.push('/upload')">
                  <el-icon size="40"><upload-filled /></el-icon>
                  <h3>文件上传</h3>
                  <p>支持拖拽上传，支持多种文件格式</p>
                </div>
              </el-col>
              <el-col :span="12">
                <div class="feature-box" @click="$router.push('/files')">
                  <el-icon size="40"><folder /></el-icon>
                  <h3>文件管理</h3>
                  <p>轻松管理您的上传文件</p>
                </div>
              </el-col>
            </el-row>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { UploadFilled, Folder } from '@element-plus/icons-vue'
</script>

<style scoped>
.home {
  padding: 20px;
  min-height: 100%;
}

.welcome-card {
  margin: 20px auto;
  max-width: 1200px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  color: #303133;
}

.card-content {
  padding: 20px 0;
}

.feature-box {
  text-align: center;
  padding: 40px 20px;
  background-color: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.feature-box:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.feature-box .el-icon {
  color: #409EFF;
  margin-bottom: 15px;
}

.feature-box h3 {
  margin: 15px 0;
  color: #303133;
}

.feature-box p {
  margin: 0;
  color: #909399;
}
</style> 