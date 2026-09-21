<template>
  <div class="music-list-container">
    <!-- 搜索栏 -->
    <div class="search-bar">
      <div class="search-header">
        <h2>Music Resource List</h2>
        <el-tag v-if="userIsAdmin" type="danger" effect="dark">Admin</el-tag>
      </div>
      <el-form :inline="true" :model="musicStore.searchForm" class="search-form">
        <!-- 新增：Keyword 输入框 -->
        <el-form-item>
          <el-input v-model="musicStore.searchForm.keyword" placeholder="Keyword (searches multiple fields)" clearable
            style="width: 240px" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="musicStore.searchForm.title" placeholder="Title" clearable />
        </el-form-item>
        <el-form-item>
          <el-input v-model="musicStore.searchForm.artist" placeholder="Artist" clearable />
        </el-form-item>
        <el-form-item>
          <el-input v-model="musicStore.searchForm.album" placeholder="Album" clearable />
        </el-form-item>
        <el-form-item>
          <el-select v-model="musicStore.searchForm.categoryId" placeholder="Select Category" clearable
            style="width: 240px">
            <el-option v-for="item in musicStore.categoryOptions" :key="item.categoryId" :label="item.categoryName"
              :value="item.categoryId" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-select v-model="musicStore.searchForm.tagIds" multiple filterable placeholder="Select Tags" clearable
            style="width: 200px" :loading="tagStore.loading">
            <el-option v-for="item in tagStore.userTagOptions" :key="item.value" :label="item.label"
              :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="userIsAdmin">
          <el-input v-model="musicStore.searchForm.username" placeholder="Uploader Username" clearable />
        </el-form-item>
        <el-form-item v-if="userIsAdmin">
          <el-input v-model="musicStore.searchForm.email" placeholder="Uploader Email" clearable />
        </el-form-item>
        <el-form-item v-if="userIsAdmin">
          <el-select v-model="musicStore.searchForm.approvalStatus" placeholder="Approval Status" clearable
            style="width: 240px">
            <el-option label="Pending" value="pending" />
            <el-option label="Approved" value="approved" />
            <el-option label="Rejected" value="rejected" />
          </el-select>
        </el-form-item>
        

        <!-- 新增：开始日期选择器 -->
        <el-form-item>
          <el-date-picker v-model="musicStore.searchForm.startDate" type="date" placeholder="Start Date" clearable
            style="width: 200px" />
        </el-form-item>
        <!-- 新增：结束日期选择器 -->
        <el-form-item>
          <el-date-picker v-model="musicStore.searchForm.endDate" type="date" placeholder="End Date" clearable
            style="width: 195px" />
        </el-form-item>

      </el-form>
      <!-- 将按钮组移到 el-form 外部或新的容器中 -->
      <div class="button-group" style="margin-top: 10px;">
        <el-button type="primary" @click="musicStore.handleSearch">Search</el-button>
        <el-button @click="musicStore.handleReset">Reset</el-button>
        <el-button type="success" @click="showUploadDialog">
          <el-icon>
            <Upload />
          </el-icon>Upload Music
        </el-button>
        <el-button type="info" @click="navigateToRecycleBin">
          <el-icon>
            <Delete />
          </el-icon>Recycle Bin
        </el-button>
        <el-button v-if="userIsAdmin" type="warning" @click="navigateToRecycleBinSettings">
          <el-icon>
            <Setting />
          </el-icon>Recycle Bin Settings
        </el-button>
      </div>
    </div>

    <!-- 音乐列表表格 -->
    <el-table v-loading="musicStore.loading" :data="musicStore.musicList" style="width: 100%"
      @sort-change="handleSortChange"
      :default-sort="{ prop: musicStore.sortParams.orderBy, order: musicStore.sortParams.orderType === 'desc' ? 'descending' : 'ascending' }">
      <el-table-column prop="title" label="Title" min-width="180" sortable="custom">
        <template #default="{ row }">
          <el-tooltip :content="row.title" placement="top" :show-after="1000">
            <span class="file-name">{{ row.title }}</span>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column prop="artist" label="Artist" min-width="120" sortable="custom">
        <template #default="{ row }">
          <span class="cell-content">{{ row.artist }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="album" label="Album" min-width="120" sortable="custom">
        <template #default="{ row }">
          <span class="cell-content">{{ row.album }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="genre" label="Genre" min-width="100" sortable="custom">
        <template #default="{ row }">
          <span class="cell-content">{{ row.genre || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="categoryName" label="Category" min-width="100" sortable="custom">
        <template #default="{ row }">
          <span class="cell-content">{{ row.categoryName || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="Uploader" min-width="120" prop="uploader.name" sortable="custom">
        <template #default="{ row }">
          <span class="cell-content">{{ row.uploader?.name || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="format" label="Format" width="80" sortable="custom" />
      <el-table-column prop="fileSize" label="File Size" width="100" sortable="custom">
        <template #default="{ row }">
          {{ musicStore.formatFileSize(row.fileSize) }}
        </template>
      </el-table-column>
      <el-table-column prop="uploadTime" label="Upload Time" width="180" sortable="custom">
        <template #default="{ row }">
          {{ musicStore.formatDateTime(row.uploadTime) }}
        </template>
      </el-table-column>
      <el-table-column prop="playCount" label="Play Count" width="110" sortable="custom" />
      <el-table-column label="Status" width="100" prop="approvalStatus" sortable="custom">
        <template #default="{ row }">
          <el-tag v-if="row.approvalStatus === 'approved'" type="success">Approved</el-tag>
          <el-tag v-else-if="row.approvalStatus === 'pending'" type="warning">Pending</el-tag>
          <el-tag v-else-if="row.approvalStatus === 'rejected'" type="danger">Rejected</el-tag>
          <el-tag v-else type="info">Unknown</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Actions" width="120" fixed="right">
        <template #default="{ row }">
          <el-dropdown trigger="click">
            <el-button type="primary" link>
              Actions<el-icon class="el-icon--right"><arrow-down /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="() => {
                  if (row.approvalStatus === 'rejected' && !userIsAdmin) {
                    ElMessage.warning('This music has been blocked by the admin and cannot be played.')
                  } else {
                    handlePlay(row)
                  }
                }">
                  <el-icon><video-play /></el-icon>
                  <span
                    :style="{ color: row.approvalStatus === 'rejected' && !userIsAdmin ? '#888' : 'inherit' }">Play</span>
                </el-dropdown-item>

                <el-dropdown-item @click="handleEdit(row)">
                  <el-icon>
                    <edit />
                  </el-icon> Edit
                </el-dropdown-item>
                <el-dropdown-item @click="handleViewDetails(row)">
                  <el-icon><info-filled /></el-icon> Details
                </el-dropdown-item>

                <el-dropdown-item @click="() => {
                  if (row.approvalStatus === 'rejected' && !userIsAdmin) {
                    ElMessage.warning('This music has been blocked by the admin and cannot be downloaded.')
                  } else {
                    handleDownload(row)
                  }
                }">
                  <el-icon>
                    <download />
                  </el-icon>
                  <span
                    :style="{ color: row.approvalStatus === 'rejected' && !userIsAdmin ? '#888' : 'inherit' }">Download</span>
                </el-dropdown-item>
                <el-dropdown-item v-if="userIsAdmin" @click="handleApprove(row)">
                  <el-icon>
                    <check />
                  </el-icon> Approve
                </el-dropdown-item>
                <el-dropdown-item v-if="userIsAdmin" @click="handleReject(row)" class="danger-item">
                  <el-icon><close-bold /></el-icon> Reject
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleDelete(row)" class="danger-item">
                  <el-icon>
                    <delete />
                  </el-icon> Delete
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination">
      <el-pagination v-model:current-page="musicStore.currentPage" v-model:page-size="musicStore.pageSize"
        :page-sizes="[10, 20, 50, 100]" :total="musicStore.total" layout="total, sizes, prev, pager, next"
        @size-change="musicStore.handleSizeChange" @current-change="musicStore.handleCurrentChange" />
    </div>

    <!-- 上传对话框 -->
    <el-dialog v-model="uploadDialog" title="Upload Music" width="600px">
      <music-upload @upload-complete="handleUploadComplete" />
    </el-dialog>

    <!-- 元数据编辑对话框 -->
    <el-dialog v-model="musicStore.metadataDialog.visible"
      :title="musicStore.metadataDialog.isEdit ? 'Edit Music Information' : 'Music Metadata'" width="500px"
      :close-on-click-modal="false" :close-on-press-escape="false">
      <div v-loading="musicStore.metadataDialog.loading" class="metadata-content">
        <el-form v-if="musicStore.metadataDialog.data" :model="musicStore.metadataDialog.data" label-width="80px"
          :rules="metadataRules" ref="metadataFormRef">
          <el-form-item label="Title" prop="title">
            <el-input v-model="musicStore.metadataDialog.data.title" :maxlength="100" show-word-limit
              placeholder="Enter music title" />
          </el-form-item>
          <el-form-item label="Artist" prop="artist">
            <el-input v-model="musicStore.metadataDialog.data.artist" :maxlength="50" show-word-limit
              placeholder="Enter artist" />
          </el-form-item>
          <el-form-item label="Album" prop="album">
            <el-input v-model="musicStore.metadataDialog.data.album" :maxlength="50" show-word-limit
              placeholder="Enter album name" />
          </el-form-item>
          <el-form-item label="Genre" prop="genre">
            <el-input v-model="musicStore.metadataDialog.data.genre" :maxlength="30" show-word-limit
              placeholder="Enter music genre" />
          </el-form-item>
          <el-form-item label="Category" prop="categoryId">
            <el-select v-model="musicStore.metadataDialog.data.categoryId" placeholder="Select category" clearable
              style="width: 100%">
              <el-option v-for="item in musicStore.categoryOptions" :key="item.categoryId" :label="item.categoryName"
                :value="item.categoryId" />
            </el-select>
          </el-form-item>
          <el-form-item label="Tags" prop="tagIds">
            <el-select v-model="musicStore.metadataDialog.data.tagIds" multiple filterable placeholder="Select tags"
              style="width: 100%" clearable :loading="tagStore.loading" multiple-limit="3">
              <el-option v-for="item in tagStore.userTagOptions" :key="item.value" :label="item.label"
                :value="item.value" />
            </el-select>
            <el-text size="small" type="info" style="margin-top: 5px; display: block;">
              {{ tagLimitMessage }}
            </el-text>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleMetadataCancel">Cancel</el-button>
          <el-button type="primary" :loading="musicStore.metadataDialog.saving" @click="handleMetadataSave">
            Save
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 添加详情对话框 -->
    <el-dialog v-model="musicStore.detailsDialog.visible"
      :title="'Music Details - ' + (musicStore.detailsDialog.data?.title || '')" width="600px">
      <div v-if="musicStore.detailsDialog.data" class="details-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Title">{{ musicStore.detailsDialog.data.title }}</el-descriptions-item>
          <el-descriptions-item label="Artist">{{ musicStore.detailsDialog.data.artist || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Album">{{ musicStore.detailsDialog.data.album || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Genre">{{ musicStore.detailsDialog.data.genre || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Category">{{ musicStore.detailsDialog.data.categoryName || '-'
            }}</el-descriptions-item>
          <el-descriptions-item label="Format">{{ musicStore.detailsDialog.data.format }}</el-descriptions-item>
          <el-descriptions-item label="File Size">{{ musicStore.formatFileSize(musicStore.detailsDialog.data.fileSize)
            }}</el-descriptions-item>
          <el-descriptions-item label="Upload Time">{{ musicStore.detailsDialog.data.uploadTime
            }}</el-descriptions-item>
          <el-descriptions-item label="Uploader">{{ musicStore.detailsDialog.data.uploader?.name || '-'
            }}</el-descriptions-item>
        </el-descriptions>

        <div class="metadata-section" v-if="musicStore.detailsDialog.data.additionalMetadata">
          <h3>Detailed Metadata</h3>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="Year">
              {{ musicStore.detailsDialog.data.additionalMetadata.year || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="Track Number">
              {{ musicStore.detailsDialog.data.additionalMetadata.track || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="Composer">
              {{ musicStore.detailsDialog.data.additionalMetadata.composer || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="Publisher">
              {{ musicStore.detailsDialog.data.additionalMetadata.publisher || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="Original Artist">
              {{ musicStore.detailsDialog.data.additionalMetadata.originalArtist || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="Album Artist">
              {{ musicStore.detailsDialog.data.additionalMetadata.albumArtist || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="Copyright">
              {{ musicStore.detailsDialog.data.additionalMetadata.copyright || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="URL">
              {{ musicStore.detailsDialog.data.additionalMetadata.url || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="Encoder">
              {{ musicStore.detailsDialog.data.additionalMetadata.encoder || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="BPM">
              {{ musicStore.detailsDialog.data.additionalMetadata.bpm || '-' }}
            </el-descriptions-item>
          </el-descriptions>

          <h3>Audio Features</h3>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="Bitrate">
              {{ musicStore.detailsDialog.data.additionalMetadata.bitrate || '-' }} kbps
            </el-descriptions-item>
            <el-descriptions-item label="Sample Rate">
              {{ musicStore.detailsDialog.data.additionalMetadata.sampleRate || '-' }} Hz
            </el-descriptions-item>
            <el-descriptions-item label="Channel Mode">
              {{ musicStore.detailsDialog.data.additionalMetadata.channels || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="Duration">
              {{ musicStore.formatDuration(musicStore.detailsDialog.data.additionalMetadata.duration) }}
            </el-descriptions-item>
            <el-descriptions-item label="Variable Bitrate">
              {{ musicStore.detailsDialog.data.additionalMetadata.isVbr ? 'Yes' : 'No' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 新增：显示标签 -->
        <div class="metadata-section" v-if="detailTags.length > 0">
          <h3>Tags</h3>
          <div>
            <el-tag v-for="tagName in detailTags" :key="tagName" type="info" effect="plain"
              style="margin-right: 5px; margin-bottom: 5px;">
              {{ tagName }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, inject, computed } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Upload, VideoPlay, Download, Edit, InfoFilled, Check, Delete, ArrowDown, Setting, CloseBold } from '@element-plus/icons-vue'
import { downloadMusic } from '@/api/music'
import MusicUpload from '@/components/MusicUpload.vue'
import { useMusicStore } from '@/stores/musicStore'
import { useTagStore } from '@/stores/tagStore'
import { useRouter } from 'vue-router'
import { isAdmin } from '@/utils/permissionUtil'

const musicStore = useMusicStore()
const tagStore = useTagStore()
const router = useRouter()
const userIsAdmin = ref(false)
const app = inject('app', null)
const uploadDialog = ref(false)
const metadataFormRef = ref(null)
const tagLimitMessage = ref('A maximum of 3 tags can be added to each music file.')

const detailTags = computed(() => {
  const tagIds = musicStore.detailsDialog.data?.tagIds;
  if (!tagIds || tagIds.length === 0) {
    return []; // 如果没有 tagIds，返回空数组
  }
  // 创建一个 Map 用于快速查找 tagId 对应的 label
  const optionsMap = new Map(tagStore.userTagOptions.map(opt => [opt.value, opt.label]));
  // 映射 ID 到标签名，并过滤掉未找到的 (以防万一)
  return tagIds
    .map(id => optionsMap.get(id))
    .filter(label => !!label);
});

const metadataRules = {
  title: [
    { required: true, message: 'Please enter a music title.', trigger: 'blur' },
    { max: 100, message: 'Title cannot exceed 100 characters.', trigger: 'blur' }
  ],
  artist: [
    { required: true, message: 'Please enter an artist name.', trigger: 'blur' },
    { max: 50, message: 'Artist name cannot exceed 50 characters.', trigger: 'blur' }
  ],
  album: [
    { required: true, message: 'Please enter an album name.', trigger: 'blur' },
    { max: 50, message: 'Album name cannot exceed 50 characters.', trigger: 'blur' }
  ],
  genre: [
    { max: 30, message: 'Genre name cannot exceed 30 characters.', trigger: 'blur' }
  ],
  categoryId: [
    { required: true, message: 'Please select a category.', trigger: 'change' }
  ]
}

const handleSortChange = ({ prop, order }) => {
  if (order === 'ascending') {
    musicStore.sortParams.orderType = 'asc'
  } else if (order === 'descending') {
    musicStore.sortParams.orderType = 'desc'
  } else {
    musicStore.sortParams.orderBy = 'uploadTime'
    musicStore.sortParams.orderType = 'desc'
  }
  musicStore.sortParams.orderBy = prop || 'uploadTime'

  musicStore.fetchMusicList()
}

const showUploadDialog = () => {
  uploadDialog.value = true
}

const handleUploadComplete = ({ fileId, fileName }) => {
  uploadDialog.value = false
  musicStore.showMetadataDialog(fileId, fileName, false)
}

const handleMetadataCancel = () => {
  musicStore.cancelMetadataEdit(metadataFormRef.value)
}

const handleMetadataSave = () => {
  musicStore.saveMetadata(metadataFormRef.value)
}

const handleEdit = (row) => {
  musicStore.showMetadataDialog(row.musicid, row.title, true)
}

const handleViewDetails = (row) => {
  musicStore.showDetails(row)
}

const handlePlay = (row) => {
  if (row.approvalStatus === 'rejected' && !userIsAdmin.value) {
    ElMessage.warning('This music has been blocked by the admin and cannot be played.');
    return;
  }

  if (app) {
    const playUrl = `/api/music-resources/${row.musicid}/file?pay=1`;
    app.addToPlayerPlaylist({ ...row, playUrl });
  } else {
    ElMessage.warning('Player component not found');
  }
};

const handleDownload = (row) => {
  if (row.approvalStatus === 'rejected' && !userIsAdmin.value) {
    ElMessage.warning('This music has been blocked by the admin and cannot be downloaded.');
    return;
  }

  try {
    const fileName = encodeURIComponent(`${row.title}.${row.format}`);
    const downloadUrl = `/api/music-resources/${row.musicid}/file?fileName=${fileName}`;

    const link = document.createElement('a');
    link.href = downloadUrl;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();

    setTimeout(() => {
      document.body.removeChild(link);
    }, 100);

    ElMessage.success('Download started');
  } catch (error) {
    console.error('Download failed:', error);
    ElMessage.error('Download failed');
  }
};

const handleApprove = (row) => {
  ElMessageBox.confirm(
    `Are you sure you want to approve the music "${row.title}"?`,
    'Approval Confirmation',
    {
      confirmButtonText: 'Approve',
      cancelButtonText: 'Cancel',
      type: 'info'
    }
  ).then(async () => {
    musicStore.approveItem(row.musicid)
  })
}

const handleReject = (row) => {
  ElMessageBox.confirm(
    `Are you sure you want to reject the music "${row.title}"?`,
    'Rejection Confirmation',
    {
      confirmButtonText: 'Reject',
      cancelButtonText: 'Cancel',
      type: 'info'
    }
  ).then(async () => {
    musicStore.rejectItem(row.musicid)
  })
}

const handleDelete = (row) => {
  ElMessageBox.confirm(
    `Are you sure you want to delete the music "${row.title}"?`,
    'Confirmation',
    {
      confirmButtonText: 'Delete',
      cancelButtonText: 'Cancel',
      type: 'warning'
    }
  ).then(async () => {
    musicStore.deleteItem(row.musicid)
  })
}

const navigateToRecycleBin = () => {
  router.push('/recyclebin')
}

const navigateToRecycleBinSettings = () => {
  router.push('/recyclebin-settings')
}

onMounted(() => {
  musicStore.fetchMusicList()
  musicStore.fetchCategoryOptions()
  tagStore.fetchUserTagOptions()
  userIsAdmin.value = isAdmin()
})

onUnmounted(() => {
  musicStore.cleanup()
})
</script>

<style scoped>
.music-list-container {
  padding: 20px;
  color: #ffffff;
}

.search-bar {
  margin-bottom: 20px;
}

.search-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.search-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.file-name {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.cell-content {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.metadata-content {
  padding: 20px 0;
}

.details-content {
  padding: 20px 0;
}

.metadata-section {
  margin-top: 20px;
}

.metadata-section h3 {
  margin: 20px 0 10px;
  color: #ff6b81;
  font-size: 16px;
  font-weight: 500;
}

:deep(.el-descriptions__label) {
  width: 100px;
  font-weight: 500;
}

:deep(.el-table) {
  background-color: #1e1e1e;
  color: #ffffff;
  border: none;
}

:deep(.el-table tr) {
  background-color: #1e1e1e;
}

:deep(.el-table th.el-table__cell) {
  background-color: #2d2d2d;
  color: #ffffff;
  border-bottom: 1px solid #333;
}

:deep(.el-table td.el-table__cell) {
  border-bottom: 1px solid #333;
}

:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) {
  background-color: #2d2d2d;
}

:deep(.el-button) {
  border: none;
}

:deep(.el-button--primary) {
  background-color: #ff6b81;
}

:deep(.el-input__wrapper) {
  background-color: #2d2d2d !important;
  border: none !important;
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

:deep(.el-descriptions__header) {
  margin-bottom: 10px;
}

:deep(.el-descriptions__title) {
  color: #ffffff;
}

:deep(.el-descriptions__cell) {
  background-color: #2d2d2d !important;
}

:deep(.el-descriptions__label) {
  color: #aaa;
}

:deep(.el-descriptions__content) {
  color: #fff;
}

:deep(.el-select-dropdown__item) {
  color: #fff;
}

:deep(.el-select-dropdown) {
  background-color: #2d2d2d;
  border: 1px solid #333;
}

:deep(.el-pagination) {
  --el-pagination-bg-color: transparent;
  --el-pagination-text-color: #fff;
  --el-pagination-button-color: #fff;
  --el-pagination-hover-color: #ff6b81;
}

@media (max-width: 768px) {
  .music-list-container {
    padding: 10px;
  }

  .search-form {
    gap: 5px;
  }

  .pagination {
    justify-content: center;
  }

  .metadata-content {
    padding: 10px 0;
  }

  :deep(.el-dialog) {
    width: 95% !important;
  }

  :deep(.el-descriptions) {
    width: 100%;
  }
}

.audio-player {
  display: none;
}

:deep(.el-tag) {
  background-color: transparent;
}

:deep(.el-tag--success) {
  border-color: #67C23A;
  color: #67C23A;
}

:deep(.el-tag--warning) {
  border-color: #E6A23C;
  color: #E6A23C;
}

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

:deep(.el-table .el-table__cell) {
  /* Example: Adjust padding if needed */
  /* padding: 8px 5px; */
}
</style>