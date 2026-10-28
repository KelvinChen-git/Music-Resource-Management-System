<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useUserStore } from '@/stores/user'
import { useSonoraPlayer } from '@/stores/sonoraPlayer'
import { fetchMedia } from '@/utils/media'
import { createReviewAudio } from '@/utils/reviewAudio'
import { DIAGNOSTIC_SCHEMA, loadReviewPack, exportReviewPack, loadReviewDraft, reviewDraftKey, reviewCounts, validAlias, checkRange } from '@/utils/reviewPack'

const user = useUserStore(), player = useSonoraPlayer()
const pack = ref(null), queryIndex = ref(0), candidateIndex = ref(0), alias = ref('')
const message = ref(''), draft = ref(null), audioElement = ref(null), input = ref(null)
const playback = ref({ phase: 'idle', positionMs: 0, trackId: '', verified: false, error: '' })
const rangeStart = ref(''), rangeEnd = ref(''), importing = ref(false)
const seekPreview = ref(null)
const counts = computed(() => pack.value ? reviewCounts(pack.value) : { total: 0, judged: 0, unjudged: 0 })
const diagnostic = computed(() => pack.value?.schema === DIAGNOSTIC_SCHEMA)
const query = computed(() => pack.value?.queries[queryIndex.value])
const row = computed(() => query.value?.candidates[candidateIndex.value])
const canJudge = computed(() => validAlias(alias.value))
const aliasHint = computed(() => !alias.value
  ? '先填写匿名标注代号，即可选择下方相关度。无需使用真实姓名。'
  : !canJudge.value
    ? '代号需为 1–64 位，以英文字母或数字开头，其余可用英文字母、数字、点、横线或下划线。'
    : '代号已填写，请根据试听选择相关度；填写代号不会自动评分。')
const busy = computed(() => playback.value.phase === 'loading')
const canCapture = computed(() => playback.value.verified && playback.value.trackId === row.value?.track_id)
const rates = ['0 · 不相关', '1 · 弱相关', '2 · 相关', '3 · 高度相关']
let controller, binding = null, epoch = 0, editVersion = 0
const downloads = new Map()
function session() {
  const stored = localStorage.getItem('token') || sessionStorage.getItem('token')
  if (!user.userId || !user.token || stored !== user.token) throw new Error('登录状态已变化，请重新登录后导入。')
  return { owner: String(user.userId), token: user.token }
}
function stamp() { return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z') }
function seconds(ms) { return (ms / 1000).toFixed(3) }
function time(ms) { const total = Math.floor(ms / 1000); return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}` }
function resetSelection() {
  releasePlayback(); rangeStart.value = ''; rangeEnd.value = ''
}
function releasePlayback() { const previous = binding; binding = null; previous?.release(); controller?.stop(); seekPreview.value = null }
function clearSession() {
  epoch++; editVersion++; releasePlayback(); pack.value = null; draft.value = null
  alias.value = ''; queryIndex.value = candidateIndex.value = 0
  rangeStart.value = rangeEnd.value = ''; importing.value = false
  message.value = '请在当前账号下重新导入标注包。'
  for (const [url, timer] of downloads) { clearTimeout(timer); URL.revokeObjectURL(url) }
  downloads.clear()
}
function storageChanged(event) { if (['token', 'userInfo'].includes(event.key) || event.key === null) clearSession() }
watch(() => [user.userId, user.token], clearSession, { flush: 'sync' })
watch([queryIndex, candidateIndex], resetSelection, { flush: 'sync' })
onMounted(() => {
  controller = createReviewAudio({ audio: audioElement.value, fetchMedia, onState: value => { playback.value = value; binding?.update(value) } })
  window.addEventListener('storage', storageChanged)
})
onBeforeUnmount(() => { clearSession(); window.removeEventListener('storage', storageChanged) })
async function importFile(event) {
  const file = event.target.files?.[0]; event.target.value = ''
  if (!file) return
  const ticket = ++epoch; editVersion++; releasePlayback(); importing.value = true; message.value = ''; draft.value = null
  try {
    const { owner, token } = session()
    if (file.size > 2 * 1024 * 1024) throw new Error('文件超过 2 MiB。')
    const imported = await loadReviewPack(await file.text(), owner)
    if (ticket !== epoch || token !== user.token) return
    pack.value = imported; queryIndex.value = candidateIndex.value = 0
    rangeStart.value = rangeEnd.value = ''; alias.value = ''
    message.value = '标注包已导入。当前文件未被本机草稿替换。'
    try {
      const raw = localStorage.getItem(reviewDraftKey(owner, imported.dataset_sha256))
      if (raw) {
        const saved = await loadReviewDraft(raw, imported, owner)
        if (ticket === epoch && token === user.token) draft.value = { raw, judged: reviewCounts(saved).judged }
      }
    } catch { if (ticket === epoch) message.value = '本机草稿不可用；当前导入文件已保留，可继续并导出。' }
  } catch (error) { if (ticket === epoch) message.value = error.message || '无法导入该标注包。' }
  finally { if (ticket === epoch) importing.value = false }
}
async function persist() {
  const ticket = ++editVersion, accountEpoch = epoch
  try {
    const { owner, token } = session(), snapshot = JSON.stringify(pack.value)
    const saved = await loadReviewPack(snapshot, owner)
    if (ticket !== editVersion || accountEpoch !== epoch || token !== user.token) return
    localStorage.setItem(reviewDraftKey(owner, saved.dataset_sha256), JSON.stringify(saved))
    draft.value = null; message.value = '已保存到当前账号的本机草稿。'
  } catch { if (accountEpoch === epoch && ticket === editVersion) message.value = '本机草稿未保存，请导出 JSON 保留本次判断。' }
}
async function restore() {
  if (!draft.value) return
  const ticket = epoch
  try {
    const { owner } = session(), saved = await loadReviewDraft(draft.value.raw, pack.value, owner)
    if (ticket !== epoch) return
    releasePlayback(); pack.value = saved; draft.value = null; editVersion++
    rangeStart.value = rangeEnd.value = ''; message.value = '已恢复同一候选包的本机草稿。'
  } catch (error) { message.value = error.message }
}
function judge(value) {
  if (!row.value || !canJudge.value) return
  try { session() } catch (error) { message.value = error.message; return }
  row.value.relevance = value; row.value.annotator = alias.value; row.value.judged_at = stamp()
  if (value === 0) row.value.human_intervals_ms = null
  persist()
}
function clearJudgment() {
  if (!row.value) return
  row.value.relevance = row.value.human_intervals_ms = row.value.annotator = row.value.judged_at = null
  rangeStart.value = rangeEnd.value = ''; persist()
}
function setRange() {
  try {
    session()
    if (!canJudge.value || !(row.value.relevance > 0)) throw new Error('请先填写代号并给出正相关判断。')
    if (![rangeStart.value, rangeEnd.value].every(value => /^(0|[1-9]\d*)(\.\d{1,3})?$/.test(String(value)))) throw new Error('起止秒数需为非负数，最多三位小数。')
    const range = [rangeStart.value, rangeEnd.value].map(value => Math.round(Number(value) * 1000))
    checkRange(range, row.value.duration_ms)
    row.value.human_intervals_ms = [range]; row.value.annotator = alias.value; row.value.judged_at = stamp(); persist()
  } catch (error) { message.value = error.message }
}
function clearRange() {
  if (!row.value || !canJudge.value || row.value.relevance === null) return
  row.value.human_intervals_ms = null; row.value.annotator = alias.value; row.value.judged_at = stamp(); persist()
}
function capture(which) {
  if (!canCapture.value) return
  const value = seconds(playback.value.positionMs)
  if (which === 'start') rangeStart.value = value
  else rangeEnd.value = value
}
async function play(range) {
  try {
    session(); releasePlayback()
    const candidate = row.value, bounds = range || [0, candidate.duration_ms]
    binding = player.registerReview({ musicid: candidate.track_id, title: candidate.title, artist: candidate.artist }, bounds, controller)
    await controller.start(candidate, bounds)
  }
  catch (error) { message.value = error.message }
}
function seek(value) { seekPreview.value = null; return controller.seek(Number(value)) }
async function download() {
  const accountEpoch = epoch, version = editVersion
  try {
    const { owner, token } = session(), content = await exportReviewPack(pack.value, owner)
    if (accountEpoch !== epoch || version !== editVersion || token !== user.token) return
    const url = URL.createObjectURL(new Blob([content], { type: 'application/json' }))
    const link = document.createElement('a'); link.href = url; link.download = `sonora-judgments-${pack.value.dataset_sha256.slice(0, 12)}.json`
    document.body.appendChild(link); link.click(); link.remove()
    downloads.set(url, setTimeout(() => { URL.revokeObjectURL(url); downloads.delete(url) }, 1000))
    message.value = '已导出部分判断；未判断条目仍为空。交接前请用固定运行的 CLI 校验。'
  } catch (error) { message.value = error.message || '无法导出当前判断。' }
}
</script>

<template>
  <section class="review-workspace">
    <header class="review-heading"><div><p class="eyebrow">EXPLORATORY LISTENING</p><h1>试听审阅</h1><p>{{ diagnostic ? '听一听，再判断文字描述与音乐是否相关。本轮核查未入选曲目，不提供模型建议，仅作探索。' : '听一听，再判断文字描述与音乐是否相关。模型建议可见，本轮仅作探索。' }}</p></div><div class="actions"><button type="button" :disabled="importing" @click="input.click()">{{ importing ? '正在校验…' : '导入标注包' }}</button><button v-if="pack" type="button" @click="download">导出 JSON</button><input ref="input" class="file-input" type="file" accept=".json,application/json" aria-label="选择标注包" @change="importFile"></div></header>
    <p v-if="message" class="notice" role="status">{{ message }}</p>
    <div v-if="!pack" class="review-empty"><h2>从本机标注包开始</h2><p>导入准备好的探索 JSON，候选和原始评分会保留。音频通过当前账号的曲库权限读取。</p><p>不会自动填写人工判断，也不会把未判断条目记为不相关。</p></div>
    <template v-else>
      <p v-if="diagnostic" class="notice">补充核查：这些曲目未进入上一轮候选；已完成判断保留，本包独立保存。</p>
      <div class="review-summary"><span>已判断 <strong>{{ counts.judged }}</strong> / {{ counts.total }}</span><span>未判断 {{ counts.unjudged }}</span></div>
      <button v-if="draft" class="restore" type="button" @click="restore">恢复本机草稿（{{ draft.judged }} 条已判断）</button>
      <label class="query-select">选择查询<select :value="queryIndex" @change="queryIndex = Number($event.target.value); candidateIndex = 0"><option v-for="(item, index) in pack.queries" :key="item.query_id" :value="index">{{ item.query_id }} · {{ item.text }}</option></select></label>
      <h2 class="query-title">{{ query.text }}</h2>
      <div class="review-columns"><nav class="candidate-list" aria-label="候选曲目"><button v-for="(item, index) in query.candidates" :key="item.track_id" type="button" :class="{ selected: candidateIndex === index }" :aria-pressed="candidateIndex === index" @click="candidateIndex = index"><strong>{{ item.title }}</strong><span>{{ item.artist }}</span><small>{{ item.relevance === null ? '尚未判断' : rates[item.relevance] }}</small></button></nav>
        <article v-if="row" class="candidate-detail"><p class="eyebrow">CANDIDATE {{ candidateIndex + 1 }} / {{ query.candidates.length }}</p><h2>{{ row.title }}</h2><p>{{ row.artist }} · {{ time(row.duration_ms) }}</p><div class="source-links"><a :href="row.source_url" target="_blank" rel="noopener noreferrer">来源</a><a :href="row.license_url" target="_blank" rel="noopener noreferrer">CC BY 许可</a></div>
          <div class="actions"><button type="button" @click="play()">{{ busy ? '重新获取并试听整曲' : '试听整曲' }}</button><button type="button" :disabled="!['playing','loading'].includes(playback.phase)" @click="controller.stop(false)">停止试听</button></div>
          <div class="review-progress"><span>{{ time(playback.positionMs) }}</span><input type="range" :min="playback.rangeStartMs || 0" :max="playback.rangeEndMs || 1" step="100" :value="seekPreview ?? playback.positionMs" :disabled="!playback.verified || busy" aria-label="试听进度" @input="seekPreview=Number($event.target.value)" @change="seek($event.target.value)" @pointercancel="seekPreview=null"><span>{{ time(playback.rangeEndMs || 0) }}</span></div>
          <div class="actions"><button type="button" :disabled="!playback.verified || busy" @click="controller.toggle()">{{ playback.phase === 'playing' ? '暂停试听' : '继续试听' }}</button><small class="hint" v-if="playback.rangeEndMs">可拖动范围：{{ seconds(playback.rangeStartMs) }}–{{ seconds(playback.rangeEndMs) }} 秒</small></div>
          <p class="playback" role="status">{{ busy ? '正在获取并校验音频…' : playback.phase === 'playing' ? '试听中' : playback.phase === 'paused' ? '已暂停' : '已停止' }} · {{ time(playback.positionMs) }}</p><p v-if="playback.error" class="error" role="alert">{{ playback.error }}</p>
          <div class="suggestions"><h3>{{ diagnostic ? '试听与手动定位' : '模型建议片段' }}</h3><p v-if="diagnostic" class="hint">本轮请试听整曲并手动定位，不提供模型建议。</p><template v-else><div class="actions"><button v-for="(range, index) in row.model_suggested_intervals_ms" :key="index" type="button" @click="play(range)">试听 {{ seconds(range[0]) }}–{{ seconds(range[1]) }} 秒</button></div><p v-if="!row.model_suggested_intervals_ms.length" class="hint">本候选没有建议片段，可试听整曲。</p></template></div>
          <fieldset class="ratings" aria-describedby="rating-alias-hint">
            <legend>与当前描述的相关性</legend>
            <label class="rating-alias">匿名标注代号（必填）<input v-model="alias" maxlength="64" placeholder="如 listener-a" autocomplete="off" spellcheck="false" required aria-label="匿名标注代号" aria-describedby="rating-alias-hint" :aria-invalid="!!alias && !canJudge"></label>
            <p id="rating-alias-hint" class="alias-hint" :class="{ error: !!alias && !canJudge }" role="status">{{ aliasHint }}</p>
            <div class="rating-options" :class="{ unavailable: !canJudge }"><label v-for="(label, value) in rates" :key="value"><input type="radio" name="relevance" :value="value" :disabled="!canJudge" :checked="row.relevance === value" @change="judge(value)">{{ label }}</label></div>
          </fieldset>
          <div class="judgment"><span>{{ row.relevance === null ? '尚未判断' : `当前判断：${rates[row.relevance]} · ${row.annotator}` }}</span><button type="button" :disabled="row.relevance === null" @click="clearJudgment">清除本条判断</button></div>
          <div class="human-range"><h3>人工相关区间（可选）</h3><p class="hint">只记录你实际确认的区间。保存会替换本条现有人工区间。</p><p v-if="row.human_intervals_ms" class="saved-ranges">已记录：{{ row.human_intervals_ms.map(range => `${seconds(range[0])}–${seconds(range[1])} 秒`).join('、') }}</p><div class="range-fields"><label>起点（秒）<input v-model="rangeStart" inputmode="decimal" aria-label="人工起点（秒）" placeholder="0.000"></label><button type="button" :disabled="!canCapture" @click="capture('start')">取当前起点</button><label>终点（秒）<input v-model="rangeEnd" inputmode="decimal" aria-label="人工终点（秒）" placeholder="0.000"></label><button type="button" :disabled="!canCapture" @click="capture('end')">取当前终点</button></div><div class="actions"><button type="button" :disabled="!canJudge || !(row.relevance > 0)" @click="setRange">保存人工区间</button><button type="button" :disabled="!canJudge || !row.human_intervals_ms" @click="clearRange">清除人工区间</button></div></div>
        </article>
      </div><p class="hint footnote">草稿只保存在本浏览器并按账号与候选包隔离。导出前可保留未完成条目；最终交接需用固定运行校验，不作为正式测试集或质量结论。</p>
    </template><audio ref="audioElement" preload="none" aria-hidden="true"></audio>
  </section>
</template>

<style scoped>
.review-workspace{max-width:1180px;margin:auto;color:var(--text,#eee);overflow-wrap:anywhere}.review-heading,.review-summary,.actions,.judgment,.source-links{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.review-heading{justify-content:space-between}.review-heading h1{font-size:30px;margin:8px 0}.eyebrow{font-size:11px;letter-spacing:2px;color:var(--accent,#b5e853)}p{line-height:1.6}.hint,.review-heading>div>p:last-child,.candidate-detail>p,.candidate-list span{color:var(--muted,#9a9aa0);font-size:13px}.file-input{display:none}button,input,select{font:inherit}button{background:#282b27;border:1px solid #42473b;color:#eee;padding:10px 14px;border-radius:8px;cursor:pointer;white-space:normal}button:hover:not(:disabled),button.selected{border-color:#b5e853;background:#303b22}button:disabled{opacity:.45;cursor:default}input,select{background:#151713;border:1px solid #45493f;border-radius:6px;padding:9px;color:#eee;max-width:100%;min-width:0}input:focus,select:focus,button:focus-visible{outline:2px solid #b5e853;outline-offset:2px}.notice,.review-empty,.review-summary{background:#22251f;border:1px solid #3c4234;border-radius:10px;padding:16px;margin:20px 0}.review-empty{padding:40px 24px}.review-summary{justify-content:space-between}.query-select{display:grid;gap:8px;margin-top:24px}.query-select select{width:100%;text-overflow:ellipsis}.query-title{font-size:20px;line-height:1.5}.review-columns{display:grid;grid-template-columns:minmax(180px,260px) minmax(0,1fr);gap:20px;align-items:start}.candidate-list{display:grid;gap:8px;min-width:0}.candidate-list button{text-align:left;display:grid;gap:6px;min-width:0}.candidate-list strong,.candidate-detail h2{overflow-wrap:anywhere}.candidate-list small{color:#b6d48c}.candidate-detail{min-width:0;border:1px solid #383b32;border-radius:12px;padding:24px;background:#1b1d19}.candidate-detail h2{font-size:26px;margin:10px 0}.source-links{margin-bottom:20px}.source-links a{color:#b5e853}.playback{font-variant-numeric:tabular-nums}.review-progress{display:flex;align-items:center;gap:12px;margin:18px 0;font-size:12px;font-variant-numeric:tabular-nums}.review-progress input{flex:1;width:100%;padding:0;accent-color:#b5e853}.suggestions,.human-range{border-top:1px solid #3b3e34;margin-top:22px;padding-top:10px}h3{font-size:15px}.ratings{min-width:0;border:1px solid #434b37;border-radius:8px;padding:14px;margin:24px 0 14px}.ratings label{display:flex;align-items:center;gap:6px;font-size:13px}.ratings .rating-alias{flex-wrap:wrap;gap:10px}.rating-alias input{flex:1;min-width:120px;max-width:280px}.alias-hint{font-size:13px;color:var(--muted,#9a9aa0);margin:10px 0 16px}.rating-options{display:flex;flex-wrap:wrap;gap:14px 18px}.rating-options label{min-height:32px;cursor:pointer}.rating-options.unavailable label{opacity:.55;cursor:default}.ratings input{accent-color:#b5e853}.judgment{justify-content:space-between;font-size:13px}.range-fields{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;margin:16px 0}.range-fields label{display:grid;gap:7px;font-size:13px}.range-fields button{align-self:end}.error{color:#f6a39c}.saved-ranges{font-size:13px;color:#c5dea6}.footnote{margin-top:24px}.restore{margin-bottom:10px}
@media(max-width:720px){.review-columns{grid-template-columns:minmax(0,1fr)}.candidate-list{grid-template-columns:repeat(2,minmax(0,1fr))}.candidate-list button{padding:10px}.candidate-detail{padding:16px}.review-heading h1{font-size:26px}.review-summary{align-items:flex-start}.range-fields{gap:9px}.ratings .rating-alias{align-items:flex-start}.rating-alias input{flex-basis:100%;max-width:100%}.actions button{padding:10px}.judgment button{margin-left:auto}}
</style>
