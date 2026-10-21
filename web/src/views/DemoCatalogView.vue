<script setup>
import { computed, onMounted, ref } from 'vue'
import { useUserStore } from '@/stores/user'
import { safeCatalogLink as safeLink } from '@/utils/catalogLinks'

const user = useUserStore()
const catalog = ref({ audioTracks: [] })
const references = ref([])
const query = ref('')
const error = ref('')
const loading = ref(true)
const matches = (track) => `${track.title} ${track.artist} ${track.album}`.toLowerCase().includes(query.value.toLowerCase())
const audio = computed(() => catalog.value.audioTracks.filter(matches))
const artistTracks = computed(() => references.value.filter(matches))
const isOwner = computed(() => String(user.userInfo?.userid) === String(catalog.value.ownerId))
onMounted(async () => {
  try {
    const responses = await Promise.all([fetch('/demo-catalog.json'), fetch('/artist-references.json')])
    if (responses.some((response) => !response.ok)) throw new Error('目录尚未准备完成，请稍后刷新。')
    const [local, external] = await Promise.all(responses.map((response) => response.json()))
    catalog.value = local
    references.value = external.tracks
  } catch (failure) { error.value = failure.message }
  finally { loading.value = false }
})
</script>

<template>
  <section class="catalog" v-loading="loading">
    <header>
      <div><p class="eyebrow">MUSIC COLLECTION</p><h1>演示曲库与歌手资料</h1></div>
      <el-input v-model="query" clearable placeholder="搜索歌名、歌手或专辑" aria-label="搜索演示曲库" class="search" />
    </header>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <template v-else>
      <el-card shadow="never" class="collection">
        <h2>完整歌曲 <span>{{ catalog.audioTracks.length }} 首</span></h2>
        <p>来自 Jamendo 的 CC BY 授权音乐，保留原始音频；每首歌曲均列出作者、来源和许可。</p>
        <el-alert v-if="!isOwner" title="这批上传属于普通演示账号。请使用演示账号登录后，到 Music 页面播放；其他账号仍遵循原有资源权限。" type="info" :closable="false" show-icon />
        <el-table :data="audio" stripe empty-text="没有匹配的歌曲">
          <el-table-column prop="title" label="歌曲" min-width="200" />
          <el-table-column prop="artist" label="作者 / 歌手" min-width="160" />
          <el-table-column prop="album" label="专辑" min-width="160" />
          <el-table-column label="来源与许可" min-width="170">
            <template #default="{ row }">
              <a :href="safeLink(row.sourceUrl)" target="_blank" rel="noopener noreferrer">Jamendo 原页</a>
              <a :href="safeLink(row.licenseUrl)" target="_blank" rel="noopener noreferrer">{{ row.license }}</a>
              <small>原音频未修改</small>
            </template>
          </el-table-column>
          <el-table-column label="曲库" width="125">
            <template #default="{ row }"><router-link v-if="isOwner" :to="{ path: '/music', query: { keyword: row.title } }">查找 / 播放</router-link><span v-else>需演示账号</span></template>
          </el-table-column>
        </el-table>
      </el-card>
      <el-card shadow="never" class="collection">
        <h2>Post Malone 与 Drake <span>{{ references.length }} 条资料</span></h2>
        <p>以下仅展示歌曲资料与 Apple 官方页面链接，未导入音频或试听文件。</p>
        <el-table :data="artistTracks" stripe empty-text="没有匹配的歌曲">
          <el-table-column prop="title" label="歌曲" min-width="220" />
          <el-table-column prop="artist" label="歌手" min-width="150" />
          <el-table-column prop="album" label="专辑" min-width="200" />
          <el-table-column label="官方页面" width="130"><template #default="{ row }"><a :href="safeLink(row.sourceUrl)" target="_blank" rel="noopener noreferrer">在 Apple 查看</a></template></el-table-column>
        </el-table>
      </el-card>
    </template>
  </section>
</template>

<style scoped>
.catalog { padding: 24px; max-width: 1400px; margin: auto; }
header { display: flex; align-items: center; justify-content: space-between; gap: 24px; margin-bottom: 24px; }
.eyebrow { font-size: 12px; letter-spacing: .16em; color: var(--el-color-primary); margin: 0 0 6px; }
h1 { font-size: 26px; margin: 0; }
h2 { margin: 0 0 10px; font-size: 20px; }
h2 span { font-size: 14px; font-weight: normal; color: var(--el-text-color-secondary); margin-left: 12px; }
p { color: var(--el-text-color-regular); line-height: 1.7; }
.search { max-width: 340px; }
.collection { margin-bottom: 24px; }
a { color: var(--el-color-primary); display: inline-block; margin-right: 12px; }
small { display: block; color: var(--el-text-color-secondary); }
@media (max-width: 700px) { header { align-items: stretch; flex-direction: column; }.search { max-width: none; }.catalog { padding: 110px 12px 12px; } }
</style>
