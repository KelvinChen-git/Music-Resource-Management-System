import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTagList, createTag, updateTag, deleteTag } from '@/api/tag'

export const useTagStore = defineStore('tag', () => {
  // State
  const tagList = ref([])
  const loading = ref(false)
  const currentPage = ref(1)
  const pageSize = ref(10)
  const total = ref(0)
  const dialog = ref({
    visible: false,
    isEdit: false,
    saving: false,
    form: {
      tagId: null,
      tagName: ''
    }
  })
  const userTagOptions = ref([])

  // Actions
  const fetchTagList = async () => {
    try {
      loading.value = true
      const params = {
        current: currentPage.value,
        size: pageSize.value
      }
      const res = await getTagList(params)
      if (res.code === 200) {
        tagList.value = res.data.records || []
        total.value = res.data.total || 0
        currentPage.value = res.data.current || 1
        pageSize.value = res.data.size || 10
      }
    } catch (error) {
      ElMessage.error(error.message || 'Failed to get tag list')
      tagList.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  const fetchUserTagOptions = async () => {
    loading.value = true;
    try {
      const res = await getTagList({ current: 1, size: 1000 }); 
      if (res.code === 200 && res.data.records) {
        userTagOptions.value = res.data.records.map(tag => ({
          value: tag.tagId,
          label: tag.tagName
        }));
      } else {
        userTagOptions.value = [];
      }
    } catch (error) {
      console.error('Failed to fetch user tag options:', error);
      ElMessage.error('Failed to load tag options');
      userTagOptions.value = [];
    } finally {
      loading.value = false;
    }
  }

  const showCreateDialog = () => {
    dialog.value = {
      visible: true,
      isEdit: false,
      saving: false,
      form: {
        tagId: null,
        tagName: ''
      }
    }
  }

  const showEditDialog = (tag) => {
    dialog.value = {
      visible: true,
      isEdit: true,
      saving: false,
      form: {
        tagId: tag.tagId,
        tagName: tag.tagName || ''
      }
    }
  }

  const handleSave = async (formRef) => {
    if (!formRef) return

    try {
      await formRef.validate()

      dialog.value.saving = true
      const formData = { tagName: dialog.value.form.tagName }

      if (dialog.value.isEdit) {
        await updateTag(dialog.value.form.tagId, formData)
        ElMessage.success('Tag updated successfully')
      } else {
        await createTag(formData)
        ElMessage.success('Tag created successfully')
      }

      dialog.value.visible = false
      fetchTagList() // Refresh list after save

    } catch (error) {
      // Handle potential validation errors from API (e.g., name exists)
      ElMessage.error(error.message || 'Save failed')
    } finally {
      dialog.value.saving = false
    }
  }

  const handleDelete = (tag) => {
    ElMessageBox.confirm(
      `Are you sure you want to delete the tag "${tag.tagName}"?`,
      'Confirmation',
      {
        confirmButtonText: 'Delete',
        cancelButtonText: 'Cancel',
        type: 'warning'
      }
    ).then(async () => {
      try {
        await deleteTag(tag.tagId)
        ElMessage.success('Tag deleted successfully')
        // If the deleted item was the last one on the current page,
        // go back one page if it's not the first page.
        if (tagList.value.length === 1 && currentPage.value > 1) {
          currentPage.value--
        }
        fetchTagList() // Refresh list after delete
      } catch (error) {
        ElMessage.error(error.message || 'Delete failed')
      }
    }).catch(() => {
      // Catch cancel action
    })
  }

  const handleSizeChange = (newSize) => {
    pageSize.value = newSize
    currentPage.value = 1 // Reset to first page
    fetchTagList()
  }

  const handleCurrentChange = (newPage) => {
    currentPage.value = newPage
    fetchTagList()
  }

  const resetDialog = (formRef) => {
    dialog.value.visible = false
    if (formRef) {
      formRef.resetFields()
    }
    dialog.value.form = { tagId: null, tagName: '' }
  }

  return {
    // State
    tagList,
    loading,
    currentPage,
    pageSize,
    total,
    dialog,
    userTagOptions,

    // Actions
    fetchTagList,
    fetchUserTagOptions,
    showCreateDialog,
    showEditDialog,
    handleSave,
    handleDelete,
    handleSizeChange,
    handleCurrentChange,
    resetDialog
  }
}) 