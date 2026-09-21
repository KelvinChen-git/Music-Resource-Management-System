<template>
  <div class="recyclebin-container">
    <div class="recyclebin-header">
      <h1>Recycle Bin</h1>
      <p class="description">View, restore or permanently delete your deleted music files</p>
      <el-alert
        v-if="!isAdmin"
        type="info"
        :closable="false"
        show-icon
      >
        <p>Note: As a regular user, you can only see items that you have deleted</p>
      </el-alert>
    </div>

    <div class="recyclebin-actions">
      <el-row :gutter="20">
        <el-col :span="16">
          <el-input
            v-model="searchQuery"
            placeholder="Search by music title or artist"
            prefix-icon="Search"
            clearable
            @clear="loadRecycleBinData"
            @keyup.enter="loadRecycleBinData"
          />
        </el-col>
        <el-col :span="8" class="action-buttons">
          <el-button 
            type="primary" 
            plain 
            icon="Refresh"
            @click="loadRecycleBinData"
          >
            Refresh
          </el-button>
          <el-button 
            type="danger" 
            plain 
            icon="Delete"
            @click="confirmEmptyRecycleBin"
            :disabled="totalItems === 0 || !isAdmin"
            v-if="isAdmin"
          >
            Empty
          </el-button>
          <el-button 
            type="info" 
            plain 
            @click="goToSettings"
            icon="Setting"
            v-if="isAdmin"
          >
            Settings
          </el-button>
          <el-button 
            type="danger" 
            plain 
            icon="Delete"
            @click="confirmEmptyMyRecycleBin" 
            :disabled="totalItems === 0" 
            v-if="!isAdmin"
          >
            Empty My Items
          </el-button>
          <el-button
            type="danger"
            plain
            icon="Delete"
            @click="confirmDeleteSelected"
            :disabled="isDeleteSelectedDisabled"
          >
            Delete Selected
          </el-button>
        </el-col>
      </el-row>
    </div>

    <el-card class="recyclebin-card" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span class="header-title">
            <el-icon><DeleteFilled /></el-icon> Deleted Music Files
          </span>
          <div class="header-stats">
            <el-tag size="small" type="info">Total: {{ totalItems }} items</el-tag>
            <el-tag size="small" type="warning" v-if="expiringItems > 0">Expiring soon: {{ expiringItems }} items</el-tag>
          </div>
        </div>
      </template>

      <div v-if="recycleBinItems.length === 0" class="empty-state">
        <el-empty description="No items in recycle bin" />
      </div>

      <el-table
        v-else
        :data="recycleBinItems"
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column label="Music Info" min-width="300">
          <template #default="{ row }">
            <div class="music-info">
              <div class="music-title">{{ row.music?.title || 'Unknown Title' }}</div>
              <div class="music-meta">
                <span>{{ row.music?.artist || 'Unknown Artist' }}</span>
                <el-divider direction="vertical" />
                <span>{{ row.music?.album || 'Unknown Album' }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="Deleted At" width="170">
          <template #default="{ row }">
            {{ formatDate(row.deletedAt) }}
          </template>
        </el-table-column>
        <el-table-column label="Deleted By" width="120">
          <template #default="{ row }">
            {{ row.deletedBy?.nickname || row.deletedBy?.username || row.deletedBy?.name || 'Unknown User' }}
          </template>
        </el-table-column>
        <el-table-column label="Expires On" width="170">
          <template #default="{ row }">
            <el-tag 
              :type="isExpiringSoon(row.permanentDeleteTime) ? 'danger' : 'info'" 
              size="small"
            >
              {{ formatDate(row.permanentDeleteTime) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Remaining" width="120">
          <template #default="{ row }">
            <span :class="{ 'low-remaining-days': calculateRemainingDays(row.permanentDeleteTime).isLow }">
              {{ calculateRemainingDays(row.permanentDeleteTime).text }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="200" fixed="right">
          <template #default="{ row }">
            <el-button 
              type="primary" 
              size="small" 
              @click="restoreItem(row)"
            >
              Restore
            </el-button>
            <el-button 
              type="danger" 
              size="small" 
              @click="confirmDeleteItem(row)"
              v-if="isAdmin || row.deletedBy?.userid === userStore.userId"
            >
              Delete
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container" v-if="totalItems > 0">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="totalItems"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { DeleteFilled, Search } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

// 导入API函数
import { 
  getRecycleBinList, 
  restoreFromRecycleBin, 
  deleteFromRecycleBin,
  emptyRecycleBin,
  emptyMyRecycleBin,
  getRecycleBinStats
} from '@/api/recycleBin'

// 路由
const router = useRouter()

// 用户状态
const userStore = useUserStore()
const isAdmin = computed(() => userStore.userInfo?.role === 'ADMIN')

// 状态变量
const loading = ref(false)
const recycleBinItems = ref([])
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const totalItems = ref(0)
const expiringItems = ref(0)
const selectedItems = ref([])

// Computed property to check if the 'Delete Selected' button should be enabled
const isDeleteSelectedDisabled = computed(() => {
  if (selectedItems.value.length === 0) {
    return true; // Always disabled if nothing selected
  }
  if (!isAdmin.value) {
    // For non-admins, check if at least one selected item belongs to them
    const canDeleteAny = selectedItems.value.some(item => item.deletedBy?.userid === userStore.userId);
    return !canDeleteAny; // Disabled if they cannot delete any of the selected items
  }
  return false; // Enabled for admin if items are selected
});

// 获取回收站数据
const loadRecycleBinData = async () => {
  loading.value = true
  try {
    // 获取回收站列表
    const params = {
      title: searchQuery.value,
      artist: searchQuery.value, // 使用相同的查询条件搜索艺术家
      current: currentPage.value,
      pageSize: pageSize.value
    }
    
    const res = await getRecycleBinList(params)
    recycleBinItems.value = res.data.records || []
    totalItems.value = res.data.total || 0
    
    // 获取统计数据 (只有管理员可以看到)
    if (isAdmin.value) {
      try {
        const statsRes = await getRecycleBinStats()
        if (statsRes.code === 200 && statsRes.data) {
          expiringItems.value = statsRes.data.expiringItems || 0
        }
      } catch (error) {
        console.error('Failed to get statistics data', error)
      }
    }
  } catch (error) {
    ElMessage.error('Failed to load recycle bin data: ' + (error.message || 'Unknown error'))
  } finally {
    loading.value = false
  }
}

// 处理分页更改
const handleSizeChange = (size) => {
  pageSize.value = size
  loadRecycleBinData()
}

const handleCurrentChange = (page) => {
  currentPage.value = page
  loadRecycleBinData()
}

// 恢复项目
const restoreItem = async (item) => {
  try {
    loading.value = true
    await restoreFromRecycleBin(item.recycleid)
    ElMessage.success('Item restored successfully')
    loadRecycleBinData()
  } catch (error) {
    ElMessage.error('Restore failed: ' + (error.message || 'Unknown error'))
  } finally {
    loading.value = false
  }
}

// 确认删除项目
const confirmDeleteItem = (item) => {
  ElMessageBox.confirm(
    'Once deleted, this item cannot be recovered. Continue?',
    'Permanent Deletion Confirmation',
    {
      confirmButtonText: 'Delete',
      cancelButtonText: 'Cancel',
      type: 'warning',
    }
  ).then(() => {
    deleteItem(item)
  }).catch(() => {
    // User canceled deletion
  })
}

// 删除项目
const deleteItem = async (item) => {
  try {
    loading.value = true
    await deleteFromRecycleBin(item.recycleid)
    ElMessage.success('Item permanently deleted')
    loadRecycleBinData()
  } catch (error) {
    ElMessage.error('Deletion failed: ' + (error.message || 'Unknown error'))
  } finally {
    loading.value = false
  }
}

// 确认清空回收站
const confirmEmptyRecycleBin = () => {
  // 只允许管理员执行此操作
  if (!isAdmin.value) {
    ElMessage.warning('Only administrators can empty the recycle bin')
    return
  }
  
  ElMessageBox.confirm(
    'Emptying the recycle bin will permanently delete all items. This action cannot be undone. Continue?',
    'Empty Recycle Bin Confirmation',
    {
      confirmButtonText: 'Empty',
      cancelButtonText: 'Cancel',
      type: 'warning',
    }
  ).then(() => {
    emptyAllItems()
  }).catch(() => {
    // User canceled the operation
  })
}

// 清空回收站
const emptyAllItems = async () => {
  // 再次检查权限
  if (!isAdmin.value) {
    ElMessage.warning('Only administrators can empty the recycle bin')
    return
  }
  
  try {
    loading.value = true
    const res = await emptyRecycleBin()
    ElMessage.success(`Recycle bin emptied successfully. ${res.data || 0} items deleted.`)
    loadRecycleBinData()
  } catch (error) {
    ElMessage.error('Failed to empty recycle bin: ' + (error.message || 'Unknown error'))
  } finally {
    loading.value = false
  }
}

// Confirm emptying user's own recycle bin items
const confirmEmptyMyRecycleBin = () => {
  if (totalItems.value === 0) {
      ElMessage.info("Your recycle bin is already empty.");
      return;
  }
  ElMessageBox.confirm(
    'This will permanently delete all items you have put in the recycle bin. This action cannot be undone. Continue?',
    'Empty My Recycle Bin Items Confirmation',
    {
      confirmButtonText: 'Empty My Items',
      cancelButtonText: 'Cancel',
      type: 'warning',
    }
  ).then(() => {
    emptyMyItems()
  }).catch(() => {
    // User canceled the operation
  })
}

// Empty user's own recycle bin items
const emptyMyItems = async () => {
  try {
    loading.value = true
    // Call the new API function
    const res = await emptyMyRecycleBin() 
    // Assuming the backend returns the count of deleted items in res.data
    ElMessage.success(`Your recycle bin items emptied successfully. ${res.data || 0} items deleted.`)
    
    loadRecycleBinData() // Reload data after success
  } catch (error) {
    ElMessage.error("Failed to empty your recycle bin items: " + (error.message || 'Unknown error'))
  } finally {
    loading.value = false
  }
}

// 前往设置页面
const goToSettings = () => {
  // 检查权限
  if (!isAdmin.value) {
    ElMessage.warning('Only administrators can access settings')
    return
  }
  
  router.push('/recyclebin-settings')
}

// 表格多选变更处理
const handleSelectionChange = (items) => {
  selectedItems.value = items
}

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return 'Unknown'
  const date = new Date(dateString)
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 判断是否即将过期（7天内）
const isExpiringSoon = (dateString) => {
  if (!dateString) return false
  const expiryDate = new Date(dateString)
  const now = new Date()
  const diffDays = Math.ceil((expiryDate - now) / (1000 * 60 * 60 * 24))
  return diffDays >= 0 && diffDays <= 7
}

// 计算剩余天数并返回包含低剩余天数标志的对象
const calculateRemainingDays = (expiryDateString) => {
  if (!expiryDateString) return { text: 'N/A', isLow: false };
  const expiryDate = new Date(expiryDateString);
  const now = new Date();
  
  // Set time to 00:00:00 for both dates to compare days accurately
  expiryDate.setHours(0, 0, 0, 0);
  now.setHours(0, 0, 0, 0);

  const diffTime = expiryDate - now;
  if (diffTime < 0) return { text: 'Expired', isLow: false };

  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  const isLow = diffDays < 5;
  
  return {
    text: `${diffDays} day(s)`,
    isLow: isLow
  };
};

// Confirm deleting selected items - Updated logic
const confirmDeleteSelected = () => {
  let itemsToDelete;
  let confirmationMessage;
  const totalSelectedCount = selectedItems.value.length;

  if (isAdmin.value) {
    // Admin deletes all selected items
    itemsToDelete = [...selectedItems.value]; // Clone the array
    if (itemsToDelete.length === 0) {
       ElMessage.warning("Please select items to delete.");
       return;
    }
    confirmationMessage = `You are about to permanently delete ${itemsToDelete.length} selected item(s). This action cannot be undone. Continue?`;
  } else {
    // Non-admin filters items they deleted
    itemsToDelete = selectedItems.value.filter(item => item.deletedBy?.userid === userStore.userId);
    if (itemsToDelete.length === 0) {
      ElMessage.warning("Please select items that you deleted to proceed.");
      return;
    }
    if (itemsToDelete.length < totalSelectedCount) {
        confirmationMessage = `You are about to permanently delete ${itemsToDelete.length} selected item(s) that you put in the recycle bin (other selected items will be ignored). This action cannot be undone. Continue?`;
    } else {
        confirmationMessage = `You are about to permanently delete ${itemsToDelete.length} selected item(s) that you put in the recycle bin. This action cannot be undone. Continue?`;
    }
  }

  ElMessageBox.confirm(
    confirmationMessage,
    `Delete ${itemsToDelete.length} Selected Item(s) Confirmation`,
    {
      confirmButtonText: 'Delete Selected',
      cancelButtonText: 'Cancel',
      type: 'warning',
    }
  ).then(() => {
    deleteSelectedItems(itemsToDelete);
  }).catch(() => {
    // User canceled the operation
  });
};

// Delete selected items (takes the list of items to delete)
// No change needed here, logic is sound for both admin/non-admin
const deleteSelectedItems = async (itemsToDelete) => {
  loading.value = true;
  let successCount = 0;
  let failCount = 0;

  // Use Promise.allSettled to handle multiple API calls concurrently
  // and process results regardless of individual failures.
  const deletePromises = itemsToDelete.map(item => 
    deleteFromRecycleBin(item.recycleid)
      .then(() => { successCount++; })
      .catch(err => {
        failCount++;
        log.error(`Failed to delete item ${item.recycleid}:`, err);
        // Optionally display a specific error per item, but might be too noisy.
      })
  );

  await Promise.allSettled(deletePromises);

  // Show summary message
  if (successCount > 0) {
    ElMessage.success(`${successCount} item(s) permanently deleted.`);
  }
  if (failCount > 0) {
    ElMessage.error(`${failCount} item(s) failed to delete. Check console for details.`);
  }
  if (successCount === 0 && failCount === 0) { // Should not happen with prior checks, but just in case
      ElMessage.info("No items were deleted.");
  }

  loading.value = false;
  selectedItems.value = []; // Clear selection
  loadRecycleBinData(); // Refresh the list
};

// 初始化
onMounted(() => {
  loadRecycleBinData()
})
</script>

<style scoped>
.recyclebin-container {
  padding: 20px;
}

.recyclebin-header {
  margin-bottom: 24px;
}

.recyclebin-header h1 {
  font-size: 24px;
  margin-bottom: 8px;
}

.description {
  color: #606266;
  font-size: 14px;
}

.recyclebin-actions {
  margin-bottom: 20px;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.recyclebin-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: bold;
}

.header-stats {
  display: flex;
  gap: 10px;
}

.empty-state {
  padding: 50px 0;
  text-align: center;
}

.music-info {
  display: flex;
  flex-direction: column;
}

.music-title {
  font-weight: bold;
  margin-bottom: 5px;
}

.music-meta {
  font-size: 12px;
  color: #909399;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .action-buttons {
    margin-top: 10px;
    justify-content: flex-start;
  }
  
  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .header-stats {
    margin-top: 5px;
  }
}

.low-remaining-days {
  color: #E6A23C; /* Warning color */
  font-weight: bold;
}
</style> 