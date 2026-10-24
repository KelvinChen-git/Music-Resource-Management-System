import { computed, ref, shallowRef, watch } from 'vue'
import { defineStore } from 'pinia'
import { createMusicUrl } from '@/api/music'
import { useUserStore } from '@/stores/user'

export const useSonoraPlayer = defineStore('sonora-player', () => {
  const user = useUserStore()
  const audio = shallowRef(null)
  const current = ref(null)
  const queue = ref([])
  const playing = ref(false)
  const loading = ref(false)
  const error = ref('')
  const position = ref(0)
  const duration = ref(0)
  const volume = ref(70)
  const loop = ref(false)
  const shuffle = ref(false)
  const favorites = ref([])
  const recent = ref([])
  const reviewSession = shallowRef(null)
  let reviewControls = null
  let generation = 0
  let objectUrl = ''
  const key = (kind) => `sonora:${user.userId || 'guest'}:${kind}:v1`
  function read(kind) {
    try {
      const ids = JSON.parse(localStorage.getItem(key(kind)) || '[]')
      return Array.isArray(ids) ? [...new Set(ids.filter(id => /^\d+$/.test(String(id))).map(String))].slice(0, 200) : []
    } catch { return [] }
  }
  function save(kind, value) {
    try { localStorage.setItem(key(kind), JSON.stringify(value)) } catch { /* Playback works without storage. */ }
  }
  function reset() {
    releaseReview()
    generation++
    audio.value?.pause()
    if (audio.value) { audio.value.removeAttribute('src'); audio.value.load() }
    if (objectUrl) URL.revokeObjectURL(objectUrl)
    objectUrl = ''
    current.value = null
    queue.value = []
    playing.value = loading.value = false
    position.value = duration.value = 0
    error.value = ''
  }
  watch(() => user.userId, () => {
    reset()
    favorites.value = read('favorites')
    recent.value = read('recent')
  }, { immediate: true, flush: 'sync' })
  watch(() => user.token, releaseReview, { flush: 'sync' })
  const favoriteSet = computed(() => new Set(favorites.value))
  function toggleFavorite(song) {
    const id = String(song.musicid)
    favorites.value = favoriteSet.value.has(id) ? favorites.value.filter(item => item !== id) : [id, ...favorites.value].slice(0, 200)
    save('favorites', favorites.value)
  }
  function attach(element) { audio.value = element; if (element) element.volume = volume.value / 100 }
  function releaseReview() {
    const previous = reviewControls
    reviewControls = null; reviewSession.value = null
    previous?.stop()
  }
  function registerReview(song, range, controls) {
    releaseReview()
    // Invalidate ordinary fetch/play work before the review can acquire audio.
    const wasLoading = loading.value
    generation++; audio.value?.pause(); playing.value = loading.value = false
    if (wasLoading) {
      // A cancelled song switch must not resume the older bytes under its new title.
      if (audio.value) { audio.value.removeAttribute('src'); audio.value.load() }
      if (objectUrl) URL.revokeObjectURL(objectUrl)
      objectUrl = ''; position.value = duration.value = 0
    }
    const ticket = Symbol('review')
    reviewControls = { ...controls, ticket }
    reviewSession.value = { song, phase: 'loading', positionMs: range[0], rangeStartMs: range[0], rangeEndMs: range[1], verified: false, error: '' }
    controls.setVolume(volume.value)
    return {
      update(snapshot) { if (reviewControls?.ticket === ticket) reviewSession.value = { ...reviewSession.value, ...snapshot } },
      release() { if (reviewControls?.ticket === ticket) releaseReview() }
    }
  }
  function toggleReview() { return reviewControls?.toggle() }
  function seekReview(percent) {
    const session = reviewSession.value
    if (!session?.verified || !Number.isFinite(Number(percent))) return
    return reviewControls?.seek(session.rangeStartMs + Math.max(0, Math.min(100, Number(percent))) / 100 * (session.rangeEndMs - session.rangeStartMs))
  }
  async function play(song, context = []) {
    releaseReview()
    const ticket = ++generation
    audio.value?.pause()
    playing.value = false
    loading.value = true
    error.value = ''
    current.value = song
    position.value = duration.value = 0
    if (context.length) queue.value = [...context]
    else if (!queue.value.some(item => String(item.musicid) === String(song.musicid))) queue.value.push(song)
    try {
      const url = await createMusicUrl(song.musicid, true)
      if (ticket !== generation || !audio.value) { URL.revokeObjectURL(url); return }
      if (objectUrl) URL.revokeObjectURL(objectUrl)
      objectUrl = url
      audio.value.src = url
      audio.value.load()
      await audio.value.play()
      if (ticket !== generation) return
      recent.value = [String(song.musicid), ...recent.value.filter(id => id !== String(song.musicid))].slice(0, 200)
      save('recent', recent.value)
    } catch {
      if (ticket === generation) {
        playing.value = false
        error.value = '播放失败，请检查登录状态、资源权限或网络后重试。'
      }
    } finally { if (ticket === generation) loading.value = false }
  }
  async function toggle() {
    if (loading.value || !current.value || !audio.value) return
    if (playing.value) audio.value.pause()
    else if (error.value || !audio.value.getAttribute('src')) await play(current.value)
    else {
      try { await audio.value.play() } catch { error.value = '浏览器未能开始播放，请重试。' }
    }
  }
  async function advance(direction = 1) {
    if (reviewSession.value) return
    if (!queue.value.length) return
    const at = queue.value.findIndex(item => String(item.musicid) === String(current.value?.musicid))
    const next = shuffle.value && queue.value.length > 1
      ? (at + 1 + Math.floor(Math.random() * (queue.value.length - 1))) % queue.value.length
      : (at + direction + queue.value.length) % queue.value.length
    await play(queue.value[next])
  }
  function seek(value) {
    if (audio.value && Number.isFinite(duration.value) && duration.value > 0) {
      audio.value.currentTime = Math.max(0, Math.min(duration.value, Number(value) / 100 * duration.value))
    }
  }
  function setVolume(value) {
    if (!Number.isFinite(Number(value))) return
    volume.value = Math.max(0, Math.min(100, Number(value)))
    if (audio.value) audio.value.volume = volume.value / 100
    reviewControls?.setVolume(volume.value)
  }
  function sync() {
    if (!audio.value) return
    if (reviewSession.value) { audio.value.pause(); playing.value = false; return }
    position.value = audio.value.currentTime || 0
    duration.value = Number.isFinite(audio.value.duration) ? audio.value.duration : 0
    playing.value = !audio.value.paused && !audio.value.ended
  }
  return { audio, current, queue, playing, loading, error, position, duration, volume, loop, shuffle,
    favorites, recent, favoriteSet, toggleFavorite, attach, play, toggle, advance, seek, setVolume, sync, reset,
    reviewSession, registerReview, releaseReview, toggleReview, seekReview }
})
