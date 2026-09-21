<template>
    <div class="player-bar" :class="{ 'expanded': showPlaylist }">
      <div class="player-controls">
        <!-- Current song info -->
        <div class="current-song-info">
          <div v-if="currentSong" class="song-details">
            <div class="song-title">{{ currentSong.title }}</div>
            <div class="song-artist">{{ currentSong.artist }}</div>
          </div>
          <div v-else class="no-song">No song selected</div>
        </div>
  
        <!-- Player controls -->
        <div class="control-buttons">
          <el-button circle @click="playPrevious">
            <el-icon><arrow-left /></el-icon>
          </el-button>
          <el-button circle @click="togglePlay">
            <el-icon v-if="isPlaying"><video-pause /></el-icon>
            <el-icon v-else><video-play /></el-icon>
          </el-button>
          <el-button circle @click="playNext">
            <el-icon><arrow-right /></el-icon>
          </el-button>
        </div>
  
        <!-- Progress bar -->
        <div class="progress-container">
          <span class="time">{{ formatTime(currentTime) }}</span>
          <el-slider 
            v-model="progressValue" 
            :max="100" 
            @change="changeProgress" 
            class="progress-slider" 
          />
          <span class="time">{{ formatTime(duration) }}</span>
        </div>
  
        <!-- Volume control -->
        <div class="volume-control">
          <el-button @click="toggleMute" link>
            <el-icon v-if="isMuted"><mute /></el-icon>
            <el-icon v-else><microphone /></el-icon>
          </el-button>
          <el-slider 
            v-model="volume" 
            :max="100" 
            @change="changeVolume" 
            class="volume-slider" 
          />
        </div>
  
        <!-- Playlist toggle -->
        <el-button class="playlist-toggle" @click="showPlaylist = !showPlaylist">
          <el-icon><list /></el-icon>
        </el-button>
      </div>
  
      <!-- Playlist panel -->
      <div v-if="showPlaylist" class="playlist-panel">
        <div class="panel-header">
          <h3>Current Playlist</h3>
          <div class="playlist-actions">
            <el-select v-model="currentPlaylistId" placeholder="Select Playlist" @change="changePlaylist">
              <el-option
                v-for="list in playlists"
                :key="list.id"
                :label="list.name"
                :value="list.id"
              />
            </el-select>
            <el-button @click="clearPlaylist" type="danger" plain size="small">Clear</el-button>
          </div>
        </div>
        <ul class="song-list">
          <li 
            v-for="(song, index) in playlist" 
            :key="song.musicid" 
            :class="{ 'playing': currentSong && currentSong.musicid === song.musicid }"
            @click="playSong(index)"
          >
            <div class="song-index">{{ index + 1 }}</div>
            <div class="song-info">
              <div class="song-title">{{ song.title }}</div>
              <div class="song-artist">{{ song.artist }} - {{ song.album }}</div>
            </div>
            <div class="song-duration">{{ formatTime(song.duration || 0) }}</div>
          </li>
        </ul>
      </div>
  
      <!-- Hidden audio element -->
      <audio 
        ref="audioPlayer" 
        @timeupdate="updateProgress" 
        @loadedmetadata="onLoadedMetadata"
        @ended="handleSongEnd"
      ></audio>
    </div>
  </template>
  
  <script setup>
  import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
  import { ArrowLeft, ArrowRight, VideoPlay, VideoPause, Microphone, Mute, List } from '@element-plus/icons-vue'
  import { ElMessage } from 'element-plus'
  import { useMusicStore } from '@/stores/musicStore'
  
  // 获取音乐状态管理
  const musicStore = useMusicStore()
  
  // State
  const audioPlayer = ref(null)
  const currentSong = ref(null)
  const isPlaying = ref(false)
  const isMuted = ref(false)
  const duration = ref(0)
  const currentTime = ref(0)
  const volume = ref(70)
  const progressValue = ref(0)
  const showPlaylist = ref(false)
  const playlist = ref([])
  const currentSongIndex = ref(-1)
  
  // Playlist management
  const currentPlaylistId = ref('default')
  const playlists = ref([
    { id: 'default', name: 'Default Playlist' },
    { id: 'favorites', name: 'Favorites' },
    { id: 'recent', name: 'Recently Played' }
  ])
  
  // Helper functions
  const formatTime = (seconds) => {
    if (!seconds) return '0:00'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }
  
  // Audio control functions
  const togglePlay = () => {
    if (!currentSong.value) return
    
    if (isPlaying.value) {
      audioPlayer.value.pause()
      isPlaying.value = false
    } else {
      audioPlayer.value.play()
      isPlaying.value = true
    }
  }
  
  const playPrevious = () => {
    if (playlist.value.length === 0) return
    
    // If we're at the beginning, go to the end
    if (currentSongIndex.value <= 0) {
      currentSongIndex.value = playlist.value.length - 1
    } else {
      currentSongIndex.value--
    }
    
    playSong(currentSongIndex.value)
  }
  
  const playNext = () => {
    if (playlist.value.length === 0) return
    
    // If we're at the end, go to the beginning
    if (currentSongIndex.value >= playlist.value.length - 1) {
      currentSongIndex.value = 0
    } else {
      currentSongIndex.value++
    }
    
    playSong(currentSongIndex.value)
  }
  
  const handleSongEnd = () => {
    playNext()
  }
  
  const playSong = async (index) => {
    if (index < 0 || index >= playlist.value.length) return
    
    try {
      currentSongIndex.value = index
      currentSong.value = playlist.value[index]
      
      // Clean up previous audio URL if exists
      if (audioPlayer.value.src) {
        URL.revokeObjectURL(audioPlayer.value.src)
      }
      
      // Load new audio
      const url = await musicStore.getMusicUrl(currentSong.value.musicid)
      if (!url) {
        ElMessage.error('Failed to load audio')
        return
      }
      
      audioPlayer.value.src = url
      audioPlayer.value.load()
      audioPlayer.value.play()
      isPlaying.value = true
    } catch (error) {
      console.error('Failed to play song:', error)
      ElMessage.error('Play failed')
    }
  }
  
  const updateProgress = () => {
    if (!audioPlayer.value) return
    
    currentTime.value = audioPlayer.value.currentTime
    if (duration.value) {
      progressValue.value = (currentTime.value / duration.value) * 100
    }
  }
  
  const onLoadedMetadata = () => {
    duration.value = audioPlayer.value.duration
  }
  
  const changeProgress = (value) => {
    if (!audioPlayer.value || !duration.value) return
    
    const newTime = (value / 100) * duration.value
    audioPlayer.value.currentTime = newTime
    currentTime.value = newTime
  }
  
  const toggleMute = () => {
    if (!audioPlayer.value) return
    
    audioPlayer.value.muted = !audioPlayer.value.muted
    isMuted.value = audioPlayer.value.muted
  }
  
  const changeVolume = (value) => {
    if (!audioPlayer.value) return
    
    audioPlayer.value.volume = value / 100
    if (value > 0 && isMuted.value) {
      audioPlayer.value.muted = false
      isMuted.value = false
    }
  }
  
  // Playlist functions
  const addToPlaylist = (song) => {
    // Check if song is already in playlist
    const exists = playlist.value.some(item => item.musicid === song.musicid)
    if (exists) {
      // 如果歌曲已存在，直接播放该歌曲
      const index = playlist.value.findIndex(item => item.musicid === song.musicid)
      if (index !== -1) {
        playSong(index)
      }
      return
    }
    
    playlist.value.push(song)
    ElMessage.success(`Added "${song.title}" to playlist`)
    
    // 如果当前没有播放中的歌曲，立即播放新添加的歌曲
    if (!currentSong.value) {
      playSong(playlist.value.length - 1)
    }
  }
  
  const removeFromPlaylist = (index) => {
    if (index < 0 || index >= playlist.value.length) return
    
    const song = playlist.value[index]
    playlist.value.splice(index, 1)
    
    // Adjust current song index if necessary
    if (index < currentSongIndex.value) {
      currentSongIndex.value--
    } else if (index === currentSongIndex.value) {
      if (playlist.value.length === 0) {
        // Playlist is now empty
        currentSong.value = null
        currentSongIndex.value = -1
        if (audioPlayer.value) {
          audioPlayer.value.pause()
          audioPlayer.value.src = ''
        }
        isPlaying.value = false
      } else {
        // Play the next song (or the first if we were at the end)
        if (currentSongIndex.value >= playlist.value.length) {
          currentSongIndex.value = 0
        }
        playSong(currentSongIndex.value)
      }
    }
    
    ElMessage.success(`Removed "${song.title}" from playlist`)
  }
  
  const clearPlaylist = () => {
    playlist.value = []
    currentSong.value = null
    currentSongIndex.value = -1
    if (audioPlayer.value) {
      audioPlayer.value.pause()
      audioPlayer.value.src = ''
    }
    isPlaying.value = false
    ElMessage.info('Playlist cleared')
  }
  
  const changePlaylist = (playlistId) => {
    // In a real app, this would load from a database
    // For now, we'll just simulate different playlists
    clearPlaylist()
    ElMessage.info(`Switched to ${playlists.value.find(p => p.id === playlistId).name}`)
  }
  
  // Expose methods to parent components
  defineExpose({
    addToPlaylist,
    playSong,
    playlist
  })
  
  // Initial setup and cleanup
  onMounted(() => {
    if (audioPlayer.value) {
      audioPlayer.value.volume = volume.value / 100
    }
  })
  
  onUnmounted(() => {
    if (audioPlayer.value && audioPlayer.value.src) {
      URL.revokeObjectURL(audioPlayer.value.src)
    }
  })
  </script>
  
  <style scoped>
  .player-bar {
    background-color: #1e1e1e;
    border-bottom: 1px solid #333;
    width: 100%;
    position: relative;
    z-index: 1000;
    transition: height 0.3s ease;
  }
  
  .player-controls {
    display: flex;
    align-items: center;
    padding: 8px 16px;
    height: 60px;
  }
  
  .current-song-info {
    width: 200px;
    overflow: hidden;
    margin-right: 15px;
  }
  
  .song-details {
    overflow: hidden;
  }
  
  .song-title {
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: #fff;
  }
  
  .song-artist {
    font-size: 12px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: #aaa;
  }
  
  .no-song {
    color: #888;
    font-style: italic;
  }
  
  .control-buttons {
    display: flex;
    gap: 10px;
    margin-right: 15px;
  }
  
  .control-buttons .el-button {
    padding: 8px;
    width: 36px;
    height: 36px;
  }
  
  .progress-container {
    flex: 1;
    display: flex;
    align-items: center;
    margin: 0 15px;
  }
  
  .progress-slider {
    flex: 1;
    margin: 0 10px;
  }
  
  .time {
    font-size: 12px;
    color: #aaa;
    width: 40px;
    text-align: center;
  }
  
  .volume-control {
    display: flex;
    align-items: center;
    margin-right: 15px;
    width: 150px;
  }
  
  .volume-slider {
    flex: 1;
    margin-left: 5px;
  }
  
  .playlist-toggle {
    margin-left: 10px;
  }
  
  /* Playlist panel styles */
  .playlist-panel {
    background-color: #222;
    padding: 15px;
    max-height: 300px;
    overflow-y: auto;
    border-bottom: 1px solid #333;
  }
  
  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
  }
  
  .panel-header h3 {
    margin: 0;
    color: #fff;
  }
  
  .playlist-actions {
    display: flex;
    gap: 10px;
    align-items: center;
  }
  
  .song-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  
  .song-list li {
    display: flex;
    align-items: center;
    padding: 8px 10px;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
  }
  
  .song-list li:hover {
    background-color: #2a2a2a;
  }
  
  .song-list li.playing {
    background-color: #333;
  }
  
  .song-index {
    width: 30px;
    font-size: 14px;
    color: #aaa;
    text-align: center;
  }
  
  .song-info {
    flex: 1;
    overflow: hidden;
    margin: 0 10px;
  }
  
  .song-duration {
    color: #aaa;
    font-size: 12px;
    width: 40px;
    text-align: right;
  }
  
  /* Deep selectors for Element Plus components */
  :deep(.el-slider__bar) {
    background-color: #ff6b81;
  }
  
  :deep(.el-slider__button) {
    border-color: #ff6b81;
  }
  
  :deep(.el-select__wrapper) {
    width: 150px;
  }
  
  /* Responsive styles */
  @media (max-width: 768px) {
    .player-controls {
      flex-wrap: wrap;
      height: auto;
      padding: 10px;
    }
    
    .current-song-info {
      width: 100%;
      margin-bottom: 10px;
      margin-right: 0;
      order: 1;
    }
    
    .control-buttons {
      order: 2;
      margin-right: 0;
      margin-bottom: 10px;
    }
    
    .progress-container {
      width: 100%;
      margin: 0 0 10px 0;
      order: 3;
    }
    
    .volume-control {
      order: 4;
      margin-right: 0;
      width: auto;
    }
    
    .playlist-toggle {
      order: 5;
    }
  }
  </style>