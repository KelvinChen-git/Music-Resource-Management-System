<template>
  <div class="category-list-container">
    <!-- 顶部操作栏 -->
    <div class="operation-bar">
      <el-button type="primary" @click="showCreateDialog">
        <el-icon><plus /></el-icon>Add Category
      </el-button>
    </div>

    <!-- 分类列表 -->
    <el-table
      v-loading="loading"
      :data="categoryList"
      style="width: 100%"
      border
    >
      <el-table-column prop="categoryId" label="ID" width="80" />
      <el-table-column prop="categoryName" label="Category Name" min-width="150" />
      <el-table-column prop="description" label="Description" min-width="200" />
      <el-table-column label="Actions" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="handleEdit(row)">Edit</el-button>
          <el-button link type="danger" @click="handleDelete(row)">Delete</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialog.visible"
      :title="dialog.isEdit ? 'Edit Category' : 'Add Category'"
      width="500px"
    >
      <el-form
        ref="formRef"
        :model="dialog.form"
        :rules="formRules"
        label-width="120px"
      >
        <el-form-item label="Category Name" prop="categoryName">
          <el-input
            v-model="dialog.form.categoryName"
            placeholder="Enter category name"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="Description" prop="description">
          <el-input
            v-model="dialog.form.description"
            type="textarea"
            placeholder="Enter category description"
            maxlength="255"
            show-word-limit
            :rows="4"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialog.visible = false">Cancel</el-button>
          <el-button type="primary" @click="handleSave" :loading="dialog.saving">
            Save
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getCategoryList, createCategory, updateCategory, deleteCategory } from '@/api/category'

// 列表数据
const loading = ref(false)
const categoryList = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

// 表单对话框
const formRef = ref(null)
const dialog = ref({
  visible: false,
  isEdit: false,
  saving: false,
  form: {
    categoryId: null,
    categoryName: '',
    description: ''
  }
})

// 表单验证规则
const formRules = {
  categoryName: [
    { required: true, message: 'Please enter category name', trigger: 'blur' },
    { max: 50, message: 'Category name cannot exceed 50 characters', trigger: 'blur' }
  ],
  description: [
    { max: 255, message: 'Description cannot exceed 255 characters', trigger: 'blur' }
  ]
}

// 获取分类列表
const fetchCategoryList = async () => {
  try {
    loading.value = true
    const res = await getCategoryList({
      current: currentPage.value,
      size: pageSize.value
    })
    categoryList.value = res.data.records
    total.value = res.data.total
  } catch (error) {
    ElMessage.error(error.message || 'Failed to get category list')
  } finally {
    loading.value = false
  }
}

// 显示新增对话框
const showCreateDialog = () => {
  dialog.value = {
    visible: true,
    isEdit: false,
    saving: false,
    form: {
      categoryId: null,
      categoryName: '',
      description: ''
    }
  }
}

// 显示编辑对话框
const handleEdit = (row) => {
  dialog.value = {
    visible: true,
    isEdit: true,
    saving: false,
    form: {
      categoryId: row.categoryId,
      categoryName: row.categoryName,
      description: row.description || ''
    }
  }
}

// 保存分类
const handleSave = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    
    dialog.value.saving = true
    if (dialog.value.isEdit) {
      await updateCategory(dialog.value.form.categoryId, dialog.value.form)
      ElMessage.success('Update successful')
    } else {
      await createCategory(dialog.value.form)
      ElMessage.success('Create successful')
    }
    
    dialog.value.visible = false
    fetchCategoryList()
  } catch (error) {
    ElMessage.error(error.message || 'Save failed')
  } finally {
    dialog.value.saving = false
  }
}

// 删除分类
const handleDelete = (row) => {
  ElMessageBox.confirm(
    `Are you sure you want to delete category "${row.categoryName}"?`,
    'Confirmation',
    {
      confirmButtonText: 'Confirm',
      cancelButtonText: 'Cancel',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteCategory(row.categoryId)
      ElMessage.success('Delete successful')
      fetchCategoryList()
    } catch (error) {
      ElMessage.error(error.message || 'Delete failed')
    }
  })
}

// 分页大小改变
const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchCategoryList()
}

// 页码改变
const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchCategoryList()
}

onMounted(() => {
  fetchCategoryList()
})
</script>

<style scoped>
.category-list-container {
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
  .category-list-container {
    padding: 10px;
  }

  .pagination-container {
    justify-content: center;
  }

  :deep(.el-dialog) {
    width: 95% !important;
  }
}

/* 深色主题样式 */
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

:deep(.el-pagination) {
  --el-pagination-bg-color: transparent !important;
  --el-pagination-text-color: #fff !important;
  --el-pagination-button-color: #fff !important;
  --el-pagination-hover-color: #ff6b81 !important;
  --el-pagination-button-bg-color: #2d2d2d !important;
  --el-pagination-button-disabled-bg-color: #1e1e1e !important;
}
</style> 