<script setup>
import { ref, provide, computed } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessageBox } from 'element-plus'
import PlayerBar from '@/components/PlayerBar.vue'
//导入权限工具
import { isAdmin } from '@/utils/permissionUtil'
import { useMusicStore } from '@/stores/musicStore'
import { getAvatarUrl } from '@/utils/url' // Import the utility function

const musicStore = useMusicStore()
const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const searchKeyword = ref('')
const playerRef = ref(null)
const showSidebar = ref(true) // 控制侧边栏显示

// 控制搜索历史显示
const showSearchHistory = ref(false)
// 从 localStorage 获取搜索历史
const searchHistory = JSON.parse(localStorage.getItem('searchHistory') || '[]')

// Computed property for the user avatar source URL in the top bar
const userAvatarSrc = computed(() => {
  // Check if userInfo exists and has an avatar path
  if (userStore.userInfo?.avatar) {
    return getAvatarUrl(userStore.userInfo.avatar);
  }
  // Return null if no avatar path, so the default slot is used
  return null;
});

// 更新搜索历史
const updateSearchHistory = (keyword) => {
  const maxHistoryLength = 20  // 最大历史记录数
  let history = JSON.parse(localStorage.getItem('searchHistory') || '[]')

  // 如果历史记录中没有此关键词，则添加到数组最前
  if (!history.includes(keyword)) {
    history.unshift(keyword)
  }

  // 如果历史记录超过最大长度，删除最旧的记录
  if (history.length > maxHistoryLength) {
    history.pop()
  }

  // 保存到 localStorage
  localStorage.setItem('searchHistory', JSON.stringify(history))
}

// 点击历史记录进行搜索
const handleHistoryClick = (history) => {
  searchKeyword.value = history  // 将点击的历史记录填入搜索框
  handleSearch()  // 调用搜索方法
}

// 退出登录
const handleLogout = () => {
  ElMessageBox.confirm('Are you sure you want to logout?', 'Prompt', {
    confirmButtonText: 'Confirm',
    cancelButtonText: 'Cancel',
    type: 'warning'
  }).then(async () => {
    await userStore.logoutAction()
    router.push('/login')
  }).catch(() => {
    // Cancel logout
  })
}

// 判断是否是认证页面（登录/注册）
const isAuthPage = computed(() => {
  return ['/login', '/register', '/forgot-password'].includes(route.path)
})

// Handle search
const handleSearch = () => {
  if (searchKeyword.value.trim()) {
    // 存储搜索历史
    updateSearchHistory(searchKeyword.value.trim())
    // Navigate to music list page with search keyword
    router.push({
      path: '/music',
      query: { keyword: searchKeyword.value.trim() }
    })
  }
}

// Handle key down event, trigger search on Enter key
const handleKeyDown = (event) => {
  if (event.key === 'Enter') {
    handleSearch()
  }
}

// Add song to player playlist - can be called from child components
const addToPlayerPlaylist = (song) => {
  if (playerRef.value) {
    playerRef.value.addToPlaylist(song)
  }
}

// Toggle sidebar visibility on mobile
const toggleSidebar = () => {
  showSidebar.value = !showSidebar.value
}

// 提供 app 引用给子组件
provide('app', {
  addToPlayerPlaylist
})

// Expose methods to be used by other components
defineExpose({
  addToPlayerPlaylist
})
</script>

<template>
  <div class="app-layout" :class="{ 'auth-page': isAuthPage }">
    <!-- Player Bar - header area -->
    <div v-if="!isAuthPage" class="app-player">
      <PlayerBar ref="playerRef" />
    </div>

    <!-- Toggle sidebar button (mobile only) -->
    <button v-if="!isAuthPage" class="sidebar-toggle" @click="toggleSidebar">
      <el-icon><i class="el-icon-menu"></i></el-icon>
    </button>

    <!-- Left Sidebar - sidebar area -->
    <div v-if="!isAuthPage" class="app-sidebar" :class="{ 'sidebar-hidden': !showSidebar }">
      <!-- Logo -->
      <div class="logo">
        <span class="music-icon">🎵</span>
        <span class="logo-text">Music Platform</span>
      </div>

      <!-- Search Box -->
      <div class="search-box">
        <el-input
          v-model="searchKeyword"
          placeholder="Enter keywords"
          class="search-input"
          :prefix-icon="Search"
          @keydown="handleKeyDown"
        >
          <template #append>
            <el-button type="primary" @click="handleSearch">Search</el-button>
          </template>
        </el-input>
        <el-button class="advance-search-btn" link @click="router.push('/music')">Cross-Field Fuzzy Search</el-button>
      </div>

      <!-- 搜索历史按钮 -->
<el-button class="search-history-btn" @click="showSearchHistory = !showSearchHistory">Search History</el-button>

<!-- 搜索历史弹窗 -->
<el-dialog v-model="showSearchHistory" title="Search History" width="400px">
  <div class="scrollable-history">
    <ul>
      <li
        v-for="(history, index) in searchHistory"
        :key="index"
        @click="handleHistoryClick(history)"
      >
        {{ history }}
      </li>
    </ul>
  </div>
  <template #footer>
    <el-button @click="showSearchHistory = false">Close</el-button>
  </template>
</el-dialog>


      <!-- Navigation Menu -->
      <el-menu
        class="sidebar-menu"
        :default-active="'/music'"
        :router="true"
        background-color="#1e1e1e"
        text-color="#ffffff"
        active-text-color="#ff6b81"
      >
        <el-menu-item index="/files" v-if="isAdmin()">
          <el-icon><i class="el-icon-document" /></el-icon>
          <span>Files</span>
        </el-menu-item>
        <el-menu-item index="/music">
          <el-icon><i class="el-icon-headset" /></el-icon>
          <span>Music</span>
        </el-menu-item>
        <el-menu-item index="/categories">
          <el-icon><i class="el-icon-menu" /></el-icon>
          <span>Categories</span>
        </el-menu-item>
        <el-menu-item index="/tags">
          <el-icon><i class="el-icon-tag" /></el-icon>
          <span>Tags</span>
        </el-menu-item>
        <!-- 用户管理 -->
        <el-menu-item index="/admin/users" v-if="isAdmin()">
          <el-icon><i class="el-icon-setting" /></el-icon>
          <span>User</span>
        </el-menu-item>
      </el-menu>
    </div>

    <!-- Main Content Area - content area -->
    <div class="app-content" :class="{ 'auth-content': isAuthPage }">
      <!-- Top Bar -->
      <div v-if="!isAuthPage" class="top-bar">
        <div class="page-title">
          <h1>Content Area</h1>
        </div>
        <div class="user-info">
          <el-dropdown trigger="click">
            <el-avatar 
              class="user-avatar" 
              :size="32"
              :src="userAvatarSrc"
            >
              {{ userStore.userName ? userStore.userName.charAt(0).toUpperCase() : 'U' }}
            </el-avatar>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="router.push('/profile')">Profile</el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">Logout</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>

      <!-- Router View -->
      <div class="content-area">
        <router-view></router-view>
      </div>
    </div>
  </div>
</template>

<style>
/* Global styles */
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #121212;
  color: #ffffff;
}

#app {
  height: 100%;
}

/* Element Plus dark theme overrides */
.el-menu {
  border-right: none !important;
}

.el-input__wrapper {
  background-color: #2d2d2d !important;
}

.el-input__inner {
  color: #ffffff !important;
}

/* Scrollbar styles */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #2d2d2d;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb {
  background: #4a4a4a;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #5a5a5a;
}
</style>

<style scoped>
/* 主布局 - Grid 结构 */
.app-layout {
  display: grid;
  grid-template-areas:
    "player player"
    "sidebar content";
  grid-template-columns: 250px 1fr;
  grid-template-rows: auto 1fr;
  min-height: 100vh;
  background-color: #121212;
}

/* 认证页面布局 */
.app-layout.auth-page {
  grid-template-areas: "content";
  grid-template-columns: 1fr;
  grid-template-rows: 1fr;
}

.auth-content {
  grid-area: content;
  height: 100vh !important;
  overflow: hidden !important;
}

/* 播放器区域 */
.app-player {
  grid-area: player;
  width: 100%;
}

/* 侧边栏区域 */
.app-sidebar {
  grid-area: sidebar;
  background-color: #1e1e1e;
  border-right: 1px solid #2d2d2d;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  height: calc(100vh - 60px); /* 减去播放器高度 */
  transition: transform 0.3s ease;
}

/* Logo 部分 */
.logo {
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid #2d2d2d;
}

.music-icon {
  font-size: 24px;
}

.logo-text {
  font-size: 18px;
  font-weight: bold;
  color: #ffffff;
}

/* 搜索框部分 */
.search-box {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.search-input {
  width: 100%;
}

.advance-search-btn {
  color: #ff6b81 !important;
  padding: 0;
}

/* 搜索历史记录 */
.search-history-btn {
  margin-top: 10px;
  width: 100%;
  background-color: #ff6b81;
  color: white;
}

.el-dialog__header {
  background-color: #1e1e1e;
  color: white;
  border-bottom: 1px solid #333;
  font-weight: bold;
}

.el-dialog__body {
  background-color: #1e1e1e;
  color: white;
  max-height: 300px;
  overflow-y: auto;
  padding: 0;
}

.el-dialog__footer {
  background-color: #1e1e1e;
  border-top: 1px solid #333;
  text-align: right;
}

ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

li {
  padding: 10px 15px;
  cursor: pointer;
  border-bottom: 1px solid #444;
  transition: background-color 0.2s;
}

li:hover {
  background-color: #2d2d2d;
}

/* 滚动容器 */
.scrollable-history {
  max-height: 250px;
  overflow-y: auto;
  padding: 10px 0;
}

/* 滚动条样式（可选） */
.scrollable-history::-webkit-scrollbar {
  width: 6px;
}
.scrollable-history::-webkit-scrollbar-thumb {
  background-color: #666;
  border-radius: 4px;
}

/* 列表项样式 */
.scrollable-history li {
  padding: 10px 15px;
  border-bottom: 1px solid #444;
  cursor: pointer;
  color: white;
}
.scrollable-history li:hover {
  background-color: #2d2d2d;
}

/* 侧边栏菜单 */
.sidebar-menu {
  flex: 1;
  margin-top: 10px;
}

/* 主内容区域 */
.app-content {
  grid-area: content;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  overflow-y: auto;
  height: calc(100vh - 60px); /* 减去播放器高度 */
}

/* 顶部栏 */
.top-bar {
  height: 64px;
  background-color: #1e1e1e;
  border-bottom: 1px solid #2d2d2d;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.page-title h1 {
  margin: 0;
  font-size: 20px;
  color: #ffffff;
}

.user-info {
  display: flex;
  align-items: center;
}

.user-avatar {
  cursor: pointer;
  background-color: #ff6b81;
}

/* 内容区域 */
.content-area {
  flex: 1;
  padding: 20px;
}

/* 侧边栏切换按钮 - 默认隐藏 */
.sidebar-toggle {
  display: none;
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #ff6b81;
  color: white;
  border: none;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
  cursor: pointer;
  z-index: 1000;
}

/* 响应式布局 */
@media (max-width: 768px) {
  .app-layout {
    grid-template-areas:
      "player"
      "content";
    grid-template-columns: 1fr;
  }
  
  .app-sidebar {
    position: fixed;
    left: 0;
    top: 60px; /* 播放器高度 */
    width: 250px;
    z-index: 1001;
    height: calc(100vh - 60px);
    box-shadow: 0 0 15px rgba(0, 0, 0, 0.5);
  }
  
  .sidebar-hidden {
    transform: translateX(-100%);
  }
  
  .sidebar-toggle {
    display: block;
  }
  
  /* 适应移动端的播放器 */
  .app-player {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 1002; /* 确保在最上层 */
  }
  
  /* 针对展开播放列表时的调整 */
  .content-area {
    padding: 15px;
  }
}
</style>