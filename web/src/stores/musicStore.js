import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { 
  getMusicList, 
  getMusicDetail, 
  updateMusic, 
  deleteMusic, 
  approveMusic, 
  createMusicUrl,
  rejectMusic
} from '@/api/music'
import { parseAndSaveMetadata } from '@/api/file'
import { getCategoryList } from '@/api/category'
import { useTagStore } from '@/stores/tagStore'
import { ElMessage } from 'element-plus'

export const useMusicStore = defineStore('music', () => {
  // 路由实例
  const route = useRoute()
  const router = useRouter()

  // 状态
  const musicList = ref([])
  const loading = ref(false)
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(10)
  const categoryOptions = ref([])
  
  // 搜索表单
  const searchForm = ref({
    title: '',
    artist: '',
    album: '',
    categoryId: null,
    username: '',
    email: '',
    approvalStatus: null,
    tagIds: [],
    startDate: null,
    endDate: null,
    keyword: ''
  })

  // --- NEW: Sort state in store ---
  const sortParams = ref({
    orderBy: 'uploadTime', // Default sort
    orderType: 'desc'
  })

  // 元数据对话框状态
  const metadataDialog = ref({
    visible: false,
    loading: false,
    saving: false,
    isEdit: false,
    musicid: null,
    fileId: null,
    fileName: '',
    data: {
      title: '',
      artist: '',
      album: '',
      genre: '',
      categoryId: null,
      tagIds: []
    }
  })

  // 详情对话框状态
  const detailsDialog = ref({
    visible: false,
    data: null
  })

  // 播放相关状态
  const currentPlayingId = ref(null)
  const currentPlayingUrl = ref('')
  
  // 计算属性
  const isEmpty = computed(() => musicList.value.length === 0)
  const hasSearchParams = computed(() => {
    return !!(
      searchForm.value.title || 
      searchForm.value.artist || 
      searchForm.value.album || 
      searchForm.value.categoryId ||
      searchForm.value.username ||
      searchForm.value.email ||
      searchForm.value.approvalStatus
    )
  })

  // 监听路由参数变化，更新搜索条件并触发搜索
  watch(
    () => route.query,
    (query) => {
      // Ensure query parameters are strings for comparison or default to empty string
      const queryTitle = query.title?.toString() ?? '';
      const queryArtist = query.artist?.toString() ?? '';
      const queryAlbum = query.album?.toString() ?? '';
      const queryCategoryId = query.categoryId ? parseInt(query.categoryId, 10) : null;
      const queryUsername = query.username?.toString() ?? '';
      const queryEmail = query.email?.toString() ?? '';
      const queryApprovalStatus = query.approvalStatus?.toString() ?? null;
      const queryTagIdsStr = query.tagIds?.toString() ?? '';
      const queryKeyword = query.keyword?.toString() ?? '';
      const currentTagIdsStr = (searchForm.value.tagIds || []).join(',');

      let needsSearch = false;

      if (queryTitle !== searchForm.value.title) {
        searchForm.value.title = queryTitle;
        needsSearch = true;
      }
      if (queryArtist !== searchForm.value.artist) {
        searchForm.value.artist = queryArtist;
        needsSearch = true;
      }
      if (queryAlbum !== searchForm.value.album) {
        searchForm.value.album = queryAlbum;
        needsSearch = true;
      }
      if (queryCategoryId !== searchForm.value.categoryId) {
        searchForm.value.categoryId = queryCategoryId;
        needsSearch = true;
      }
      if (queryUsername !== searchForm.value.username) {
        searchForm.value.username = queryUsername;
        needsSearch = true;
      }
      if (queryEmail !== searchForm.value.email) {
        searchForm.value.email = queryEmail;
        needsSearch = true;
      }
      if (queryApprovalStatus !== searchForm.value.approvalStatus) {
        searchForm.value.approvalStatus = queryApprovalStatus;
        needsSearch = true;
      }
      if (queryTagIdsStr !== currentTagIdsStr) {
         if (queryTagIdsStr) {
             searchForm.value.tagIds = queryTagIdsStr.split(',').map(id => parseInt(id, 10)).filter(Number.isFinite);
         } else {
             searchForm.value.tagIds = [];
         }
         needsSearch = true;
      }
      if (queryKeyword !== searchForm.value.keyword) {
        searchForm.value.keyword = queryKeyword;
        needsSearch = true;
      }

      if (needsSearch) {
        handleSearch();
      }
    },
    { immediate: true, deep: true } // Use deep watch
  )

  // 获取音乐列表数据
  const fetchMusicList = async () => {
    try {
      loading.value = true

      let formattedStartDate = null;
      if (searchForm.value.startDate) {
        try {
          const date = new Date(searchForm.value.startDate);
          formattedStartDate = date.toISOString().split('T')[0];
        } catch (e) {
          console.error("Error formatting start date:", e);
        }
      }

      let formattedEndDate = null;
      if (searchForm.value.endDate) {
        try {
          const date = new Date(searchForm.value.endDate);
          formattedEndDate = date.toISOString().split('T')[0];
        } catch (e) {
          console.error("Error formatting end date:", e);
        }
      }

      const params = {
        current: currentPage.value,
        pageSize: pageSize.value,
        title: searchForm.value.title,
        artist: searchForm.value.artist,
        album: searchForm.value.album,
        categoryId: searchForm.value.categoryId,
        username: searchForm.value.username,
        email: searchForm.value.email,
        approvalStatus: searchForm.value.approvalStatus,
        tagIds: searchForm.value.tagIds,
        startDate: formattedStartDate,
        endDate: formattedEndDate,
        orderBy: sortParams.value.orderBy,
        orderType: sortParams.value.orderType,
        keyword: searchForm.value.keyword
      }
      
      Object.keys(params).forEach(key => {
        if (params[key] === null || params[key] === undefined || params[key] === '' || (Array.isArray(params[key]) && params[key].length === 0)) {
          delete params[key];
        }
      });

      const res = await getMusicList(params)
      if (res.code === 200) {
        musicList.value = res.data.records || []
        total.value = res.data.total || 0
        currentPage.value = res.data.current || 1
        pageSize.value = res.data.size || 10
        
        // 当使用用户名或邮箱搜索但没有结果时显示提示
        if (musicList.value.length === 0 && (searchForm.value.username || searchForm.value.email)) {
          ElMessage.info('No music resources found with the specified user filters')
        }
      }
    } catch (error) {
      ElMessage.error('获取音乐列表失败')
      console.error('获取音乐列表失败:', error)
      // 出错时重置列表
      musicList.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  // 搜索操作
  const handleSearch = () => {
    currentPage.value = 1
    fetchMusicList()
    
    updateRouteQuery()
  }

  // 更新路由查询参数
  const updateRouteQuery = () => {
    const query = { ...route.query }
    
    // Helper to add/remove query param
    const updateQueryParam = (key, value) => {
      if (value !== null && value !== undefined && value !== '' && (!Array.isArray(value) || value.length > 0)) {
          // Convert array to comma-separated string for URL
          query[key] = Array.isArray(value) ? value.join(',') : value;
      } else {
          delete query[key];
      }
    };

    updateQueryParam('title', searchForm.value.title);
    updateQueryParam('artist', searchForm.value.artist);
    updateQueryParam('album', searchForm.value.album);
    updateQueryParam('categoryId', searchForm.value.categoryId);
    updateQueryParam('username', searchForm.value.username);
    updateQueryParam('email', searchForm.value.email);
    updateQueryParam('approvalStatus', searchForm.value.approvalStatus);
    updateQueryParam('tagIds', searchForm.value.tagIds);
    updateQueryParam('startDate', searchForm.value.startDate instanceof Date ? searchForm.value.startDate.toISOString().split('T')[0] : searchForm.value.startDate);
    updateQueryParam('endDate', searchForm.value.endDate instanceof Date ? searchForm.value.endDate.toISOString().split('T')[0] : searchForm.value.endDate);
    updateQueryParam('keyword', searchForm.value.keyword);

    // 只有当查询参数发生变化时才更新路由
    if (JSON.stringify(query) !== JSON.stringify(route.query)) {
      router.replace({ query })
    }
  }

  // 重置搜索表单和排序
  const handleReset = () => {
    searchForm.value = {
      title: '',
      artist: '',
      album: '',
      categoryId: null,
      username: '',
      email: '',
      approvalStatus: null,
      tagIds: [],
      startDate: null,
      endDate: null,
      keyword: ''
    }
    // Reset sort state to default
    sortParams.value.orderBy = 'uploadTime'
    sortParams.value.orderType = 'desc'
    
    // Fetch list with reset filters and sort
    handleSearch()
  }

  // 分页大小改变
  const handleSizeChange = (val) => {
    pageSize.value = val
    currentPage.value = 1 // Reset page when size changes
    fetchMusicList()
  }

  // 页码改变
  const handleCurrentChange = (val) => {
    currentPage.value = val
    fetchMusicList()
  }

  // 获取分类选项
  const fetchCategoryOptions = async () => {
    try {
      const res = await getCategoryList({ size: 100 })
      if (res.code === 200) {
        categoryOptions.value = res.data.records
      }
    } catch (error) {
      console.error('获取分类列表失败:', error)
    }
  }

  // 显示元数据对话框
  const showMetadataDialog = async (id, fileName, isEdit = true) => {
    // Ensure tag options are loaded
    await tagStore.fetchUserTagOptions()
    // Ensure category options are loaded
    if (categoryOptions.value.length === 0) {
      await fetchCategoryOptions()
    }

    metadataDialog.value = {
      visible: true,
      loading: true,
      saving: false,
      isEdit,
      musicid: isEdit ? id : null,
      fileId: !isEdit ? id : null,
      fileName,
      data: {
        title: '',
        artist: '',
        album: '',
        genre: '',
        categoryId: null,
        tagIds: []
      }
    }

    try {
      if (isEdit) {
        const res = await getMusicDetail(id)
        if (res.code === 200) {
          const musicData = res.data; // 获取完整的响应数据
          metadataDialog.value.data = {
            title: musicData.title,
            artist: musicData.artist || '',
            album: musicData.album || '',
            genre: musicData.genre || '',
            categoryId: musicData.categoryid,
            tagIds: musicData.tagIds || [] // 从响应中获取 tagIds
          }
        } else {
          throw new Error(res.message || 'Failed to load music details')
        }
      } else {
        // New mode: parse metadata
        const res = await parseAndSaveMetadata(id)
        if (res.code === 200) {
          const defaultTitle = fileName.substring(0, fileName.lastIndexOf('.') > 0 ? fileName.lastIndexOf('.') : fileName.length)
          metadataDialog.value.data = {
            title: res.data.title || defaultTitle,
            artist: res.data.artist || '',
            album: res.data.album || '',
            genre: res.data.genre || '',
            categoryId: null,
            tagIds: []
          }
          if (res.data.title) {
            ElMessage.success('Metadata parsed successfully')
          } else {
            ElMessage.info('No metadata found, using filename as default title')
          }
        } else {
          throw new Error(res.message || 'Failed to parse metadata')
        }
      }
    } catch (error) {
      console.error('Failed to load music information:', error)
      const defaultTitle = fileName.substring(0, fileName.lastIndexOf('.') > 0 ? fileName.lastIndexOf('.') : fileName.length)
      ElMessage.warning('Failed to load music information, please fill in manually')
      metadataDialog.value.data = {
        title: defaultTitle,
        artist: '',
        album: '',
        genre: '',
        categoryId: null,
        tagIds: []
      }
    } finally {
      metadataDialog.value.loading = false
    }
  }

  // 保存元数据
  const saveMetadata = async (formRef) => {
    if (!formRef) return
    
    try {
      await formRef.validate()
      
      metadataDialog.value.saving = true
      const { musicid, fileId, data, isEdit } = metadataDialog.value

      // Prepare data payload, ensuring tagIds is an array
      const payload = {
        title: data.title,
        artist: data.artist || '',
        album: data.album || '',
        genre: data.genre || '',
        categoryId: data.categoryId,
        tagIds: data.tagIds || []
      }

      if (isEdit) {
        // Edit mode: Update existing music resource
        const res = await updateMusic(musicid, payload)
        if (res.code === 200) {
          ElMessage.success('Music information updated successfully')
          metadataDialog.value.visible = false
          fetchMusicList()
        } else {
          throw new Error(res.message || 'Update failed')
        }
      } else {
        // New mode: Save metadata after upload (associates with fileId)
        const res = await parseAndSaveMetadata(fileId, payload)
        if (res.code === 200) {
          ElMessage.success('Metadata saved successfully')
          metadataDialog.value.visible = false
          fetchMusicList()
        } else {
          throw new Error(res.message || 'Save failed')
        }
      }
    } catch (error) {
      console.error('Save failed:', error)
      if (error.message?.includes('已上传过相同的音乐')) {
        ElMessage.error('You have already uploaded the same music')
      } else {
        ElMessage.error(error.message || 'Save failed')
      }
    } finally {
      metadataDialog.value.saving = false
    }
  }

  // 取消元数据编辑
  const cancelMetadataEdit = (formRef) => {
    metadataDialog.value.visible = false
    metadataDialog.value.data = {
      title: '',
      artist: '',
      album: '',
      genre: '',
      categoryId: null,
      tagIds: []
    }
    if (formRef) {
      formRef.resetFields()
    }
  }

  // 显示音乐详情
  const showDetails = (row) => {
    detailsDialog.value = {
      visible: true,
      data: row
    }
  }

  // 获取音乐URL
  const getMusicUrl = async (musicId) => {
    try {
      // 调用createMusicUrl时，第二个参数为true表示需要计数
      const url = await createMusicUrl(musicId, true);
      currentPlayingId.value = musicId;
      currentPlayingUrl.value = url;
      
      // 手动更新前端列表中的播放次数
      const index = musicList.value.findIndex(item => item.musicid === musicId);
      if (index !== -1) {
        // 确保 playCount 存在且是数字
        if (typeof musicList.value[index].playCount === 'number') {
           musicList.value[index].playCount++;
        } else {
           // 如果 playCount 不存在或不是数字，则设为 1
           musicList.value[index].playCount = 1;
        }
      }
      
      return url;
    } catch (error) {
      ElMessage.error('获取音乐URL失败: ' + error.message);
      return null;
    }
  }

  // 删除音乐
  const deleteItem = async (id) => {
    try {
      const res = await deleteMusic(id)
      if (res.code === 200) {
        ElMessage.success('Music deleted successfully')
        fetchMusicList()
        return true
      }
      return false
    } catch (error) {
      ElMessage.error('Failed to delete music')
      console.error('Deletion failed:', error)
      return false
    }
  }

  // 审核音乐
  const approveItem = async (id) => {
    try {
      const res = await approveMusic(id)
      if (res.code === 200) {
        ElMessage.success('审核通过')
        fetchMusicList()
        return true
      }
      return false
    } catch (error) {
      ElMessage.error('审核失败')
      console.error('审核失败:', error)
      return false
    }
  }

  // 拒绝音乐
  const rejectItem = async (id) => {
    loading.value = true
    try {
      const res = await rejectMusic(id)
      if (res.code === 200) {
        ElMessage.success('音乐拒绝成功')
        fetchMusicList()
      }
    } catch (error) {
      ElMessage.error('拒绝失败: ' + error.message)
    } finally {
      loading.value = false
    }
  }

  // 格式化文件大小
  const formatFileSize = (size) => {
    if (size < 1024) return size + ' B'
    const kb = size / 1024
    if (kb < 1024) return kb.toFixed(2) + ' KB'
    const mb = kb / 1024
    if (mb < 1024) return mb.toFixed(2) + ' MB'
    const gb = mb / 1024
    return gb.toFixed(2) + ' GB'
  }

  // 格式化时长
  const formatDuration = (seconds) => {
    if (!seconds) return '-'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const remainingSeconds = seconds % 60
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`
    } else {
      return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
    }
  }

  // 格式化日期时间
  const formatDateTime = (isoString) => {
    if (!isoString) return '-';
    try {
      const date = new Date(isoString);
      if (isNaN(date.getTime())) { // Check if date is valid
        return isoString; // Return original if invalid
      }
      const year = date.getFullYear();
      const month = (date.getMonth() + 1).toString().padStart(2, '0');
      const day = date.getDate().toString().padStart(2, '0');
      const hours = date.getHours().toString().padStart(2, '0');
      const minutes = date.getMinutes().toString().padStart(2, '0');
      const seconds = date.getSeconds().toString().padStart(2, '0');
      return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
    } catch (error) {
      console.error('Error formatting date:', isoString, error);
      return isoString; // Return original string in case of error
    }
  }

  // 初始化
  const initialize = () => {
    fetchMusicList()
    fetchCategoryOptions()
  }

  // 清理资源
  const cleanup = () => {
    // 清理逻辑 - 在 PlayerBar 中处理
  }

  const tagStore = useTagStore()

  return {
    // 状态
    musicList,
    loading,
    total,
    currentPage,
    pageSize,
    searchForm,
    sortParams,
    categoryOptions,
    metadataDialog,
    detailsDialog,
    currentPlayingId,
    currentPlayingUrl,
    
    // 计算属性
    isEmpty,
    hasSearchParams,
    
    // 方法
    fetchMusicList,
    handleSearch,
    handleReset,
    handleSizeChange,
    handleCurrentChange,
    fetchCategoryOptions,
    showMetadataDialog,
    saveMetadata,
    cancelMetadataEdit,
    showDetails,
    getMusicUrl,
    deleteItem,
    approveItem,
    rejectItem,
    formatFileSize,
    formatDuration,
    formatDateTime,
    initialize,
    cleanup
  }
})