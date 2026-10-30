import { sha256, reviewId, checkRange } from './reviewPack.js'

/** Each start reacquires authorized bytes. No cached URL can resume across starts. */
export function createReviewAudio({ audio, fetchMedia, onState, beforePlay = () => {}, urls = URL }) {
  let generation = 0, request = null, objectUrl = '', timer = null, teardown = () => {}
  let lastPlayback = null, refresh = () => {}
  const state = { phase: 'idle', positionMs: 0, trackId: '', verified: false, error: '', rangeStartMs: 0, rangeEndMs: 0 }
  const emit = (patch) => { Object.assign(state, patch); onState({ ...state }) }
  function stop(reset = true) {
    generation++; request?.abort(); request = null
    clearTimeout(timer); timer = null; teardown(); teardown = () => {}; refresh = () => {}
    audio.pause(); audio.removeAttribute('src'); audio.load()
    if (objectUrl) urls.revokeObjectURL(objectUrl)
    objectUrl = ''
    if (reset) lastPlayback = null
    emit({ phase: 'idle', error: '', ...(reset ? { positionMs: 0, trackId: '', verified: false, rangeStartMs: 0, rangeEndMs: 0 } : {}) })
  }
  async function start(row, range = [0, row.duration_ms], positionMs = range[0], autoplay = true) {
    stop(); const ticket = generation
    request = new AbortController(); const signal = request.signal
    const current = () => ticket === generation && !signal.aborted
    try {
      reviewId(row.track_id); checkRange(range, row.duration_ms); range = [...range]
      if (!Number.isSafeInteger(positionMs) || positionMs < range[0] || positionMs >= range[1]) throw new Error('试听位置超出当前范围。')
      if (!Number.isSafeInteger(row.content_bytes) || row.content_bytes < 1 || row.content_bytes > 30 * 1024 * 1024) throw new Error('音频大小超出允许范围。')
      lastPlayback = { row: { ...row }, range: [...range], requestRange: [...range] }
      beforePlay(); emit({ phase: 'loading', trackId: row.track_id, positionMs, rangeStartMs: range[0], rangeEndMs: range[1] })
      const response = await fetchMedia(`/api/music-resources/${row.track_id}/file`, { signal })
      if (!current()) return
      const declared = response.headers.get('content-length')
      if (declared !== null && Number(declared) !== row.content_bytes) throw new Error('音频字节数与标注包不一致。')
      if (!response.body) throw new Error('未收到音频内容。')
      const reader = response.body.getReader(), blocks = []
      let size = 0
      try {
        while (true) {
          const { done, value } = await reader.read()
          if (!current()) { await reader.cancel(); return }
          if (done) break
          size += value.byteLength
          if (size > row.content_bytes) throw new Error('音频超过标注包记录的大小。')
          blocks.push(value)
        }
      } catch (error) { await reader.cancel().catch(() => {}); throw error }
      finally { reader.releaseLock() }
      if (size !== row.content_bytes) throw new Error('音频不完整或字节数不一致。')
      const bytes = new Uint8Array(size); let offset = 0
      for (const block of blocks) { bytes.set(block, offset); offset += block.byteLength }
      if (await sha256(bytes) !== row.content_sha256) throw new Error('音频内容指纹不匹配，已停止试听。')
      if (!current()) return
      objectUrl = urls.createObjectURL(new Blob([bytes], { type: 'audio/mpeg' }))
      const waitFor = (event, action) => new Promise((resolve, reject) => {
        const timeout = setTimeout(() => finish(new Error('浏览器加载音频超时。')), 15000)
        const finish = (error) => {
          clearTimeout(timeout); audio.removeEventListener(event, ready); audio.removeEventListener('error', failed); signal.removeEventListener('abort', aborted)
          error ? reject(error) : resolve()
        }
        const ready = () => finish(), failed = () => finish(new Error('浏览器无法解码这段音频。'))
        const aborted = () => finish(new DOMException('Aborted', 'AbortError'))
        audio.addEventListener(event, ready, { once: true }); audio.addEventListener('error', failed, { once: true }); signal.addEventListener('abort', aborted, { once: true })
        try { action() } catch (error) { finish(error) }
      })
      await waitFor('loadedmetadata', () => { audio.src = objectUrl; audio.load() })
      if (!current()) return
      if (!Number.isFinite(audio.duration) || audio.duration <= 0) throw new Error('浏览器音频时长与候选区间不符。')
      if (['incompetech', 'loc-citizen-dj-fma', 'loc-citizen-dj-musicbox'].includes(row.source_provider) && range[0] === 0 && range[1] === row.duration_ms) {
        // Verified source MP3 decoders may expose different end padding. Never extend playback or alter the package duration.
        range[1] = Math.min(row.duration_ms, Math.floor(audio.duration * 1000))
        if (range[1] <= 0 || positionMs >= range[1]) throw new Error('浏览器音频时长与候选区间不符。')
        lastPlayback.range = [...range]
        emit({ rangeEndMs: range[1] })
      } else if (range[1] / 1000 > audio.duration + 0.1) throw new Error('浏览器音频时长与候选区间不符。')
      if (positionMs > 0) await waitFor('seeked', () => { audio.currentTime = positionMs / 1000 })
      if (!current()) return
      const finish = () => { const positionMs = Math.min(range[1], Math.round(audio.currentTime * 1000)); stop(false); emit({ positionMs }) }
      const update = () => {
        if (!current()) return
        emit({ positionMs: Math.min(range[1], Math.round(audio.currentTime * 1000)) })
        clearTimeout(timer)
        if (audio.currentTime * 1000 >= range[1]) finish()
        else timer = setTimeout(() => {
          if (!current()) return
          // A stalled decoder must not turn elapsed wall time into played audio.
          if (audio.currentTime * 1000 >= range[1] - 15) finish()
          else update()
        }, Math.max(1, range[1] - audio.currentTime * 1000))
      }
      const failed = () => { if (current()) { stop(); emit({ phase: 'error', error: '音频播放失败，请重新试听。' }) } }
      refresh = update
      audio.addEventListener('timeupdate', update); audio.addEventListener('ended', finish); audio.addEventListener('error', failed)
      teardown = () => { audio.removeEventListener('timeupdate', update); audio.removeEventListener('ended', finish); audio.removeEventListener('error', failed) }
      if (!autoplay) { emit({ verified: true }); pause(); return }
      await audio.play()
      if (!current()) return
      emit({ phase: 'playing', verified: true }); update()
    } catch (error) {
      if (current()) {
        const retry = lastPlayback; stop(); lastPlayback = retry
        emit({ phase: 'error', error: error.message || '试听失败，请检查登录、权限或网络。' })
      }
    }
  }
  function pause() {
    const positionMs = state.verified && objectUrl
      ? Math.max(state.rangeStartMs, Math.min(state.rangeEndMs, Math.round(audio.currentTime * 1000))) : state.positionMs
    stop(false); emit({ phase: 'paused', positionMs })
  }
  async function toggle() {
    if (state.phase === 'playing' || state.phase === 'loading') { pause(); return }
    if (lastPlayback) {
      const { row, range, requestRange } = lastPlayback
      const position = state.positionMs >= range[0] && state.positionMs < range[1] ? state.positionMs : range[0]
      await start(row, requestRange, position)
    }
  }
  async function seek(value) {
    if (!lastPlayback || !Number.isFinite(value)) return
    const { row, range, requestRange } = lastPlayback
    const target = Math.max(range[0], Math.min(range[1], Math.round(value)))
    if (objectUrl && state.verified) {
      try { audio.currentTime = target / 1000; refresh() }
      catch { stop(); emit({ phase: 'error', error: '无法跳转试听位置，请重新试听。' }) }
    } else if (target === range[1]) { stop(false); emit({ positionMs: target }) }
    else await start(row, requestRange, target, state.phase !== 'paused')
  }
  function setVolume(value) {
    if (Number.isFinite(value)) audio.volume = Math.max(0, Math.min(100, value)) / 100
  }
  return { start, stop, pause, toggle, seek, setVolume }
}
