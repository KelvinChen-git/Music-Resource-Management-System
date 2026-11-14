<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useUserStore } from '@/stores/user'
import { useSonoraPlayer } from '@/stores/sonoraPlayer'
import { searchDiscovery } from '@/api/discovery'
import { getCategoryList } from '@/api/category'
import { getTagList } from '@/api/tag'
import { discoveryResults, discoveryMediaUrl } from '@/utils/discovery'
import { createReviewAudio } from '@/utils/reviewAudio'
import { fetchMedia } from '@/utils/media'
import { formatTime } from '@/utils/sonoraArt'
import Icon from './SonoraIcon.vue'

const user = useUserStore(), player = useSonoraPlayer()
const query = ref(''), mode = ref('segment'), category = ref(''), tags = ref([]), tagMatch = ref('all')
const categories = ref([]), tagOptions = ref([]), loading = ref(false), error = ref(''), result = ref(null)
const fixture = ref(false), playback = ref({ phase: 'idle' }), audioElement = ref(null)
let generation = 0, pending = null, controller = null, binding = null
function release() { const previous = binding; binding = null; previous?.release(); controller?.stop() }
function clear() {
  generation++; pending?.abort(); pending = null; loading.value = false
  release(); result.value = null; error.value = ''; fixture.value = false
}
function identityChanged() { clear(); query.value = ''; category.value = ''; tags.value = []; categories.value = []; tagOptions.value = []; loadOptions() }
watch(() => [user.userId, user.token], identityChanged, { flush: 'sync' })
function currentSession() { return user.userId && user.token && (localStorage.getItem('token') || sessionStorage.getItem('token')) === user.token }
function storageChanged(event) { if (['token', 'userInfo', null].includes(event.key)) { clear(); query.value=''; category.value=''; tags.value=[]; categories.value=[]; tagOptions.value=[] } }
async function loadOptions() {
  const identity = user.token
  if (!identity || !currentSession()) return
  const values = await Promise.allSettled([getCategoryList({ current: 1, size: 100 }), getTagList({ current: 1, size: 100 })])
  if (identity !== user.token) return
  categories.value = values[0].status === 'fulfilled' ? values[0].value.data.records || [] : []
  tagOptions.value = values[1].status === 'fulfilled' ? values[1].value.data.records || [] : []
}
async function search() {
  if (!currentSession()) { clear(); error.value='登录状态已变化，请重新登录。'; return }
  const text = query.value.trim()
  if (!text || [...text].length > 1000) { error.value = '请输入1–1000字的音乐描述。'; return }
  clear(); const ticket = generation, identity = user.token
  loading.value = true; pending = new AbortController()
  try {
    const response = await searchDiscovery({ query: { kind: 'text', text }, retrieval_mode: mode.value, top_k: 10,
      filters: { category_id: category.value || null, tag_ids: tags.value.map(String), tag_match: tagMatch.value } }, pending.signal)
    if (ticket !== generation || identity !== user.token || !currentSession()) return
    result.value = discoveryResults(response.data)
    fixture.value = result.value.engine_kind === 'synthetic_fixture'
  } catch (failure) {
    if (ticket !== generation || identity !== user.token) return
    error.value = failure.response?.data?.message || failure.message || '检索暂不可用，请稍后重试。'
    fixture.value = failure.response?.data?.data?.error_type === 'fixture_query_unavailable'
  } finally { if (ticket === generation) { loading.value = false; pending = null } }
}
async function play(row, segment) {
  if (!controller) return
  if (!currentSession()) { clear(); error.value='登录状态已变化，请重新登录。'; return }
  release()
  const range = [segment.start_ms, segment.end_ms]
  binding = player.registerReview({ musicid: row.track_id, title: row.title, artist: row.artist, discovery: true }, range, controller)
  await controller.start(row, range)
}
function example(text) { query.value = text; search() }
onMounted(() => {
  controller = createReviewAudio({ audio: audioElement.value, fetchMedia, mediaUrl: discoveryMediaUrl,
    onState: state => { playback.value = state; binding?.update(state) } })
  loadOptions(); window.addEventListener('storage', storageChanged)
})
onBeforeUnmount(() => { clear(); window.removeEventListener('storage', storageChanged) })
</script>

<template>
  <section class="discovery-panel" aria-labelledby="discovery-title">
    <div class="section-heading"><div><div class="eyebrow">FIND YOUR SOUND</div><h2 id="discovery-title">用描述，找到一段音乐。</h2></div></div>
    <p class="hint">描述想听的声音或使用场景，查找已审核音乐中的相关片段。首版建议使用英文。</p>
    <form @submit.prevent="search">
      <div class="discovery-query"><input v-model="query" aria-label="音乐描述" maxlength="1000" placeholder="例如 calm acoustic guitar for a quiet evening"><button class="primary" :disabled="loading || !query.trim()" type="submit"><Icon name="search" />{{ loading ? '正在检索…' : '查找片段' }}</button></div>
      <div class="discovery-filters">
        <label>检索方式<select v-model="mode" aria-label="检索方式"><option value="segment">片段匹配</option><option value="whole_track">整曲匹配</option></select></label>
        <label>分类<select v-model="category" aria-label="检索分类"><option value="">全部分类</option><option v-for="item in categories" :key="item.categoryId" :value="String(item.categoryId)">{{ item.categoryName }}</option></select></label>
        <el-select v-model="tags" multiple collapse-tags clearable placeholder="标签（可选）" aria-label="检索标签" class="discovery-tags"><el-option v-for="item in tagOptions" :key="item.tagId" :value="String(item.tagId)" :label="item.tagName" /></el-select>
        <label v-if="tags.length">标签关系<select v-model="tagMatch" aria-label="标签关系"><option value="all">全部满足</option><option value="any">满足任一</option></select></label>
      </div>
    </form>
    <div v-if="fixture" class="fixture-notice" role="note"><strong>合成联调模式 · 未运行语义模型</strong><span>仅用于验证权限、排序和试听链路。</span><button v-for="tone in [440,660,880]" :key="tone" class="link" @click="example(`synthetic tone ${tone}`)">synthetic tone {{ tone }}</button></div>
    <p v-if="loading" role="status" class="hint">正在查找相关片段…</p>
    <p v-if="error" role="alert" class="inline-error">{{ error }}</p>
    <template v-if="result">
      <p class="hint" role="status">找到 {{ result.results.length }} 首音乐 · 每首最多3段</p>
      <p v-if="!result.results.length" class="discovery-empty">当前已审核曲库和筛选条件下没有匹配项，试试其他描述或筛选。</p>
      <article v-for="row in result.results" :key="row.track_id" class="discovery-result">
        <div class="discovery-track"><strong>{{ row.title }}</strong><span>{{ row.artist || '未知歌手' }}</span><small>排序分数 {{ row.score.toFixed(3) }}</small></div>
        <div class="discovery-clips"><button v-for="segment in row.segments" :key="segment.segment_id" class="secondary" :disabled="playback.phase==='loading'" @click="play(row,segment)" :aria-label="`试听 ${row.title} ${formatTime(segment.start_ms/1000)}至${formatTime(segment.end_ms/1000)}`"><Icon name="play" />{{ formatTime(segment.start_ms/1000) }} – {{ formatTime(segment.end_ms/1000) }}</button></div>
      </article>
    </template>
    <p v-if="playback.phase==='error'" role="alert" class="inline-error">{{ playback.error }}</p>
    <audio ref="audioElement"></audio>
  </section>
</template>

<style scoped>
.discovery-panel{border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.025);border-radius:18px;padding:24px;margin:0 0 32px}.discovery-panel h2{font-size:22px;margin:6px 0}.discovery-query{display:flex;gap:12px;margin:18px 0 14px}.discovery-query input{flex:1;min-width:0;border:1px solid #394147;background:#151c20;border-radius:10px;padding:13px 15px;color:inherit;font:inherit}.discovery-query input:focus{outline:2px solid #b4db82;outline-offset:2px}.discovery-filters{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.discovery-filters label{display:flex;align-items:center;gap:8px;font-size:12px;color:#b6bfc6}.discovery-filters select{color:#e3e9e4;background:#192125;border:1px solid #394147;border-radius:7px;padding:7px}.discovery-tags{width:200px}.discovery-result{padding:18px 0;border-top:1px solid rgba(255,255,255,.08);display:flex;justify-content:space-between;align-items:center;gap:20px}.discovery-track{display:flex;flex-direction:column;gap:5px;min-width:0;overflow-wrap:anywhere}.discovery-track span,.discovery-track small{color:#a9b5bd;font-size:12px}.discovery-clips{display:flex;gap:8px;flex-wrap:wrap;flex-shrink:0}.discovery-clips button{font-size:12px;padding:9px 12px}.fixture-notice{margin:18px 0;padding:12px;border:1px solid #867546;border-radius:8px;color:#e8ce8f;display:flex;flex-wrap:wrap;gap:10px;font-size:12px}.discovery-empty{color:#b6bfc6;font-size:14px;padding:16px 0}@media(max-width:600px){.discovery-panel{padding:18px 14px}.discovery-query{flex-direction:column}.discovery-query button{justify-content:center}.discovery-result{align-items:flex-start;flex-direction:column;gap:12px}.discovery-clips{width:100%}.discovery-clips button{flex:1;white-space:nowrap}.discovery-filters{gap:10px}}
</style>
