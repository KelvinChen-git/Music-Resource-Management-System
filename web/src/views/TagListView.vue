<template>
  <div class="tag-list-container">
    <!-- 顶部操作栏 -->
    <div class="operation-bar">
      <el-button type="primary" @click="tagStore.showCreateDialog">
        <el-icon><plus /></el-icon>Add Tag
      </el-button>
    </div>

    <!-- 标签列表 -->
    <el-table
      v-loading="tagStore.loading"
      :data="tagStore.tagList"
      style="width: 100%"
      border
    >
      <el-table-column prop="tagId" label="ID" width="100" />
      <el-table-column prop="tagName" label="Tag Name" min-width="200" />
      <el-table-column label="Actions" width="150" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="tagStore.showEditDialog(row)">Edit</el-button>
          <el-button link type="danger" @click="tagStore.handleDelete(row)">Delete</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="tagStore.currentPage"
        v-model:page-size="tagStore.pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="tagStore.total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="tagStore.handleSizeChange"
        @current-change="tagStore.handleCurrentChange"
      />
    </div>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="tagStore.dialog.visible"
      :title="tagStore.dialog.isEdit ? 'Edit Tag' : 'Add Tag'"
      width="400px"
      @close="tagStore.resetDialog(formRef)" 
    >
      <el-form
        ref="formRef"
        :model="tagStore.dialog.form"
        :rules="formRules"
        label-width="100px"
        @submit.prevent="tagStore.handleSave(formRef)" 
      >
        <el-form-item label="Tag Name" prop="tagName">
          <el-input
            v-model="tagStore.dialog.form.tagName"
            placeholder="Enter tag name"
            maxlength="50"
            show-word-limit
            clearable
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="tagStore.resetDialog(formRef)">Cancel</el-button>
          <el-button type="primary" @click="tagStore.handleSave(formRef)" :loading="tagStore.dialog.saving">
            Save
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { useTagStore } from '@/stores/tagStore'

const tagStore = useTagStore()
const formRef = ref(null)

const formRules = {
  tagName: [
    { required: true, message: 'Please enter tag name', trigger: 'blur' },
    { max: 50, message: 'Tag name cannot exceed 50 characters', trigger: 'blur' }
  ]
}

onMounted(() => {
  tagStore.fetchTagList()
})
</script>

<style scoped>
.tag-list-container {
  padding: 20px;
  color: #ffffff;
}

.operation-bar {
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

@media screen and (max-width: 768px) {
  .tag-list-container {
    padding: 10px;
  }

  .pagination-container {
    justify-content: center;
  }

  :deep(.el-dialog) {
    width: 95% !important;
  }
}

/* 深色主题样式 - 参考 CategoryListView */
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

:deep(.el-pagination) {
  --el-pagination-bg-color: transparent !important;
  --el-pagination-text-color: #fff !important;
  --el-pagination-button-color: #fff !important;
  --el-pagination-hover-color: #ff6b81 !important;
  --el-pagination-button-bg-color: #2d2d2d !important;
  --el-pagination-button-disabled-bg-color: #1e1e1e !important;
}
</style> 