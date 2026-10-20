<script setup>
import { computed, provide, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useSonoraPlayer } from '@/stores/sonoraPlayer'
import { getAvatarUrl } from '@/utils/url'
import Icon from '@/components/SonoraIcon.vue'
import Symbols from '@/components/SonoraSymbols.vue'
import SonoraPlayer from '@/components/SonoraPlayer.vue'
import '@/styles/sonora.css'
const router = useRouter(), route = useRoute(), user = useUserStore(), player = useSonoraPlayer()
const sidebarOpen = ref(false), query = ref(''), search = ref(null)
const auth = computed(() => ['/login','/register','/forgot-password'].includes(route.path))
const admin = computed(() => user.userRole === 'ADMIN')
const links = [{path:'/music',title:'音乐曲库',icon:'grid'},{path:'/artists',title:'歌手与专辑',icon:'artist'},{path:'/favorites',title:'我的收藏',icon:'heart'},{path:'/recent',title:'最近播放',icon:'clock'}]
const tools = computed(() => [{path:'/manage/music',title:'资源管理',icon:'list'},{path:'/upload',title:'上传音乐',icon:'upload'},{path:'/demo-catalog',title:'来源与许可',icon:'check'},{path:'/categories',title:'分类管理',icon:'grid'},{path:'/tags',title:'标签管理',icon:'list'},{path:'/recyclebin',title:'回收站',icon:'clock'},...(admin.value?[{path:'/files',title:'文件管理',icon:'list'},{path:'/admin/users',title:'用户管理',icon:'artist'},{path:'/recyclebin-settings',title:'回收站设置',icon:'list'}]:[])])
const title = computed(() => [...links,...tools.value,{path:'/profile',title:'个人资料'}].find(item => item.path===route.path)?.title || '音乐空间')
watch(() => route.fullPath, () => { sidebarOpen.value=false; query.value=String(route.query.keyword || '') }, {immediate:true})
function handleSearch(){router.push({path:'/music',query:query.value.trim()?{keyword:query.value.trim()}: {}})}
function shortcut(event){if ((event.metaKey||event.ctrlKey)&&event.key.toLowerCase()==='k'){event.preventDefault();search.value?.focus()}if(event.key==='Escape')sidebarOpen.value=false}
onMounted(()=>document.addEventListener('keydown',shortcut))
onBeforeUnmount(()=>document.removeEventListener('keydown',shortcut))
provide('app',{addToPlayerPlaylist:(song)=>player.play(song)})
</script>
<template>
  <Symbols />
  <div v-if="auth" class="sonora-auth"><router-link class="auth-brand" to="/music"><span class="brandmark"></span> SONORA</router-link><router-view /></div>
  <template v-else>
    <div class="mobile-dim" :class="{open:sidebarOpen}" @click="sidebarOpen=false"></div>
    <aside class="sidebar" :class="{open:sidebarOpen}" aria-label="主导航">
      <router-link class="brand" to="/music"><span class="brandmark"></span><span class="wordmark">SONORA<small>YOUR SOUND ARCHIVE</small></span></router-link>
      <div class="navlabel">你的音乐空间</div><nav class="nav"><router-link v-for="link in links" :key="link.path" class="navbtn" :class="{active:route.path===link.path}" :to="link.path"><Icon :name="link.icon" />{{ link.title }}<span v-if="link.path==='/favorites' && player.favorites.length" class="num">{{ player.favorites.length }}</span></router-link></nav>
      <div class="nav-rule"></div><div class="navlabel">音乐管理</div><nav class="nav management-nav"><router-link v-for="link in tools" :key="link.path" class="navbtn" :class="{active:route.path===link.path}" :to="link.path"><Icon :name="link.icon" />{{ link.title }}</router-link></nav>
      <div class="side-bottom"><div class="storage-note">好的音乐，值得被认真收藏。</div><router-link to="/upload"><Icon name="upload" />添加新的声音</router-link></div>
    </aside>
    <div class="workspace"><header class="topbar"><button class="mobile-menu" aria-label="展开导航" :aria-expanded="sidebarOpen" @click="sidebarOpen=!sidebarOpen"><Icon name="menu" /></button><div class="breadcrumbs"><span>我的空间</span><span>/</span><strong>{{ title }}</strong></div><form class="search" @submit.prevent="handleSearch"><Icon name="search" /><input ref="search" v-model="query" type="search" placeholder="搜索歌曲、歌手或专辑" aria-label="搜索歌曲、歌手或专辑"><kbd>⌘ K</kbd></form><span class="preview-pill">音乐空间</span><el-dropdown trigger="click"><button class="avatar" aria-label="账户菜单"><img v-if="user.userAvatar" :src="getAvatarUrl(user.userAvatar)" alt="账户头像"><span v-else>{{ user.userName?.charAt(0)?.toUpperCase() || 'U' }}</span></button><template #dropdown><el-dropdown-menu><el-dropdown-item @click="router.push('/profile')">个人资料</el-dropdown-item><el-dropdown-item divided @click="user.logoutAction()">退出登录</el-dropdown-item></el-dropdown-menu></template></el-dropdown></header>
      <main class="main" :class="{'management-page':!['/music','/artists','/favorites','/recent'].includes(route.path)}"><router-view /></main>
    </div><SonoraPlayer />
  </template>
</template>
