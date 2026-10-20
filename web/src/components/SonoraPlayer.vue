<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useSonoraPlayer } from '@/stores/sonoraPlayer'
import { coverFor, formatTime } from '@/utils/sonoraArt'
import Icon from './SonoraIcon.vue'
const player = useSonoraPlayer()
const audio = ref(null)
const queueOpen = ref(false)
onMounted(() => player.attach(audio.value))
onBeforeUnmount(() => { player.reset(); player.attach(null) })
</script>

<template>
  <footer class="player" aria-label="播放器">
    <div class="now">
      <div class="now-art" v-if="player.current" v-html="coverFor(player.current)"></div>
      <div class="now-art empty-art" v-else><Icon name="play" /></div>
      <div class="now-info"><div class="now-title">{{ player.current?.title || '让音乐，从这里开始。' }}</div><div class="now-artist">{{ player.current?.artist || '选择一首歌，开始聆听' }}</div></div>
      <button v-if="player.current" class="icon-btn like-now" :class="{selected:player.favoriteSet.has(String(player.current.musicid))}" :aria-pressed="player.favoriteSet.has(String(player.current.musicid))" aria-label="收藏当前歌曲" @click="player.toggleFavorite(player.current)"><Icon name="heart" /></button>
    </div>
    <div class="player-center">
      <div class="transport">
        <button class="icon-btn" :class="{selected:player.shuffle}" :aria-pressed="player.shuffle" aria-label="随机播放" @click="player.shuffle=!player.shuffle"><Icon name="shuffle" /></button>
        <button class="icon-btn" :disabled="!player.queue.length || player.loading" aria-label="上一首" @click="player.advance(-1)"><Icon name="prev" /></button>
        <button class="big-play" :disabled="!player.current || player.loading" :aria-label="player.loading?'正在加载':player.playing?'暂停':'播放'" @click="player.toggle()"><span v-if="player.loading" class="loading-dot">···</span><Icon v-else :name="player.playing?'pause':'play'" /></button>
        <button class="icon-btn" :disabled="!player.queue.length || player.loading" aria-label="下一首" @click="player.advance()"><Icon name="next" /></button>
        <button class="icon-btn" :class="{selected:player.loop}" :aria-pressed="player.loop" aria-label="单曲循环" @click="player.loop=!player.loop"><Icon name="repeat" /></button>
      </div>
      <div class="progress"><span>{{ formatTime(player.position) }}</span><input type="range" min="0" max="100" step="0.1" :disabled="!player.duration" :value="player.duration?player.position/player.duration*100:0" aria-label="播放进度" @change="player.seek($event.target.value)"><span>{{ formatTime(player.duration) }}</span></div>
    </div>
    <div class="player-right"><span class="preview-note">{{ player.loading?'加载音频':player.playing?'正在播放':'SONORA' }}</span><button class="icon-btn" :aria-label="player.volume?'静音':'取消静音'" @click="player.setVolume(player.volume?0:70)"><Icon name="volume" /></button><input type="range" min="0" max="100" :value="player.volume" aria-label="音量" @input="player.setVolume($event.target.value)"><button class="icon-btn" aria-label="打开播放队列" @click="queueOpen=true"><Icon name="list" /></button></div>
    <audio ref="audio" :loop="player.loop" @timeupdate="player.sync" @loadedmetadata="player.sync" @play="player.sync" @pause="player.sync" @ended="player.advance()" @error="player.error='音频加载失败，请重新选择歌曲。'"></audio>
    <div v-if="player.error" class="player-error" role="alert"><span>{{ player.error }}</span><button aria-label="关闭播放错误提示" @click="player.error=''">×</button></div>
  </footer>
  <el-drawer v-model="queueOpen" title="接下来，继续好听。" size="min(420px, 100%)">
    <p class="hint">本次会话的播放队列</p>
    <p v-if="!player.queue.length" class="hint">还没有歌曲。点击曲库中的播放按钮开始。</p>
    <button v-for="song in player.queue" :key="song.musicid" class="queue-track" @click="player.play(song)"><div class="queue-art" v-html="coverFor(song)"></div><span>{{ song.title }}<small>{{ song.artist }}</small></span><Icon v-if="String(player.current?.musicid)===String(song.musicid)" name="play" /></button>
  </el-drawer>
</template>
