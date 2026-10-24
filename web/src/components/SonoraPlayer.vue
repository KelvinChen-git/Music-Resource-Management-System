<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useSonoraPlayer } from '@/stores/sonoraPlayer'
import { coverFor, formatTime } from '@/utils/sonoraArt'
import Icon from './SonoraIcon.vue'
const player = useSonoraPlayer()
const audio = ref(null)
const queueOpen = ref(false)
const seekPreview = ref(null)
const review = computed(() => player.reviewSession)
const song = computed(() => review.value?.song || player.current)
const playing = computed(() => review.value ? review.value.phase === 'playing' : player.playing)
const loading = computed(() => review.value ? review.value.phase === 'loading' : player.loading)
const position = computed(() => review.value ? review.value.positionMs / 1000 : player.position)
const end = computed(() => review.value ? review.value.rangeEndMs / 1000 : player.duration)
const start = computed(() => review.value ? review.value.rangeStartMs / 1000 : 0)
const error = computed(() => review.value ? review.value.error : player.error)
const progress = computed(() => seekPreview.value ?? (end.value > start.value ? (position.value-start.value)/(end.value-start.value)*100 : 0))
watch(() => `${review.value ? 'review' : 'library'}:${song.value?.musicid}:${start.value}:${end.value}`, () => { seekPreview.value=null })
function toggle() { return review.value ? player.toggleReview() : player.toggle() }
function seek(value) { seekPreview.value = null; return review.value ? player.seekReview(value) : player.seek(value) }
function dismissError() { if (review.value) player.reviewSession = {...review.value,error:''}; else player.error='' }
onMounted(() => player.attach(audio.value))
onBeforeUnmount(() => { player.reset(); player.attach(null) })
</script>

<template>
  <footer class="player" aria-label="播放器">
    <div class="now">
      <div class="now-art" v-if="song" v-html="coverFor(song)"></div>
      <div class="now-art empty-art" v-else><Icon name="play" /></div>
      <div class="now-info"><div class="now-title">{{ song?.title || '让音乐，从这里开始。' }}</div><div class="now-artist">{{ song?.artist || '选择一首歌，开始聆听' }}{{ review ? ' · 试听审阅' : '' }}</div></div>
      <button v-if="song" class="icon-btn like-now" :class="{selected:player.favoriteSet.has(String(song.musicid))}" :aria-pressed="player.favoriteSet.has(String(song.musicid))" aria-label="收藏当前歌曲" @click="player.toggleFavorite(song)"><Icon name="heart" /></button>
    </div>
    <div class="player-center">
      <div class="transport">
        <button class="icon-btn" :disabled="!!review" :class="{selected:player.shuffle}" :aria-pressed="player.shuffle" aria-label="随机播放" @click="player.shuffle=!player.shuffle"><Icon name="shuffle" /></button>
        <button class="icon-btn" :disabled="!!review || !player.queue.length || loading" aria-label="上一首" @click="player.advance(-1)"><Icon name="prev" /></button>
        <button class="big-play" :disabled="!song || loading" :aria-label="loading?'正在加载':playing?'暂停':'播放'" @click="toggle"><span v-if="loading" class="loading-dot">···</span><Icon v-else :name="playing?'pause':'play'" /></button>
        <button class="icon-btn" :disabled="!!review || !player.queue.length || loading" aria-label="下一首" @click="player.advance()"><Icon name="next" /></button>
        <button class="icon-btn" :disabled="!!review" :class="{selected:player.loop}" :aria-pressed="player.loop" aria-label="单曲循环" @click="player.loop=!player.loop"><Icon name="repeat" /></button>
      </div>
      <div class="progress"><span>{{ formatTime(position) }}</span><input type="range" min="0" max="100" step="0.1" :disabled="review ? !review.verified || loading : !player.duration" :value="progress" aria-label="播放进度" @input="seekPreview=Number($event.target.value)" @change="seek($event.target.value)" @pointercancel="seekPreview=null"><span>{{ formatTime(end) }}</span></div>
    </div>
    <div class="player-right"><span class="preview-note">{{ review ? '试听审阅' : loading?'加载音频':playing?'正在播放':'SONORA' }}</span><button class="icon-btn" :aria-label="player.volume?'静音':'取消静音'" @click="player.setVolume(player.volume?0:70)"><Icon name="volume" /></button><input type="range" min="0" max="100" :value="player.volume" aria-label="音量" @input="player.setVolume($event.target.value)"><button class="icon-btn" aria-label="打开播放队列" @click="queueOpen=true"><Icon name="list" /></button></div>
    <audio ref="audio" :loop="player.loop" @timeupdate="player.sync" @loadedmetadata="player.sync" @play="player.sync" @pause="player.sync" @ended="player.advance()" @error="player.error='音频加载失败，请重新选择歌曲。'"></audio>
    <div v-if="error" class="player-error" role="alert"><span>{{ error }}</span><button aria-label="关闭播放错误提示" @click="dismissError">×</button></div>
  </footer>
  <el-drawer v-model="queueOpen" title="接下来，继续好听。" size="min(420px, 100%)">
    <p class="hint">本次会话的播放队列</p>
    <p v-if="!player.queue.length" class="hint">还没有歌曲。点击曲库中的播放按钮开始。</p>
    <button v-for="song in player.queue" :key="song.musicid" class="queue-track" @click="player.play(song)"><div class="queue-art" v-html="coverFor(song)"></div><span>{{ song.title }}<small>{{ song.artist }}</small></span><Icon v-if="String(player.current?.musicid)===String(song.musicid)" name="play" /></button>
  </el-drawer>
</template>
