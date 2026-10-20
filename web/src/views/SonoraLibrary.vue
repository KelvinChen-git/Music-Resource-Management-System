<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getMusicList, getMusicDetail } from '@/api/music'
import { useSonoraPlayer } from '@/stores/sonoraPlayer'
import { coverFor, durationOf, formatTime } from '@/utils/sonoraArt'
import Icon from '@/components/SonoraIcon.vue'
const route=useRoute(), router=useRouter(), player=useSonoraPlayer()
const songs=ref([]), total=ref(0), page=ref(1), limit=ref(8), loading=ref(false), failure=ref('')
const layout=ref('grid'), sort=ref('recent'), genre=ref('全部'), collection=ref(null)
const detail=ref(null), drawer=ref(false), detailLoading=ref(false), detailError=ref('')
const references=ref([]), catalog=ref([]), referenceError=ref(''), selectedArtist=ref(''), artistQuery=ref('')
let requestId=0, detailId=0
const mode=computed(()=>route.path.slice(1))
const artistMode=computed(()=>mode.value==='artists')
const titles=computed(()=>({favorites:['喜欢，就再听一遍。','把心动的旋律，收藏成自己的小小宇宙。','我的收藏'],recent:['让昨天的心情，再响一次。','那些刚刚陪伴过你的声音，都在这里。','最近播放'],artists:['有些声音，一听就认得。','从熟悉的歌手，走进更多音乐故事。','歌手聚焦']}[mode.value]||['把喜欢的声音，留在这里。','从一首歌开始，慢慢建立属于你的音乐世界。','全部音乐']))
const genreOf=s=>{const g=String(s.genre||'').toLowerCase();if(/pop|流行/.test(g))return '流行';if(/electro|house|dance|电子/.test(g))return '电子';if(/folk|acoustic|民谣/.test(g))return '民谣';if(/hip|rap|嘻哈/.test(g))return '嘻哈';return s.genre||'其他'}
const filtered=computed(()=>{
  let items=songs.value.filter(s=>(genre.value==='全部'||genreOf(s)===genre.value)&&(mode.value!=='favorites'||player.favoriteSet.has(String(s.musicid))))
  if (sort.value==='name')items.sort((a,b)=>String(a.title).localeCompare(String(b.title)))
  if (sort.value==='duration')items.sort((a,b)=>durationOf(a)-durationOf(b))
  return items
})
const hasMore=computed(()=>page.value*20<total.value)
const artistRows=computed(()=>references.value.filter(t=>(!selectedArtist.value||t.artist===selectedArtist.value)&&`${t.title} ${t.artist} ${t.album}`.toLowerCase().includes(artistQuery.value.toLowerCase())))
const attribution=computed(()=>catalog.value.find(t=>t.title===detail.value?.title&&t.artist===detail.value?.artist))
function safeLink(value){try{const u=new URL(value);return u.protocol==='https:'&&['www.jamendo.com','creativecommons.org','music.apple.com','itunes.apple.com'].includes(u.hostname)?u.href:''}catch{return ''}}
async function load(append=false){
  const ticket=++requestId
  loading.value=true;failure.value=''
  if(!append){songs.value=[];total.value=0;page.value=1;limit.value=8}
  try{
    if(artistMode.value)return
    const next=append?page.value+1:1
    let records,count
    if(mode.value==='favorites'||mode.value==='recent'){
      const ids=mode.value==='favorites'?player.favorites:player.recent
      const results=await Promise.allSettled(ids.slice((next-1)*20,next*20).map(id=>getMusicDetail(id)))
      records=results.filter(r=>r.status==='fulfilled').map(r=>r.value.data)
      count=ids.length
      // Unavailable resources are never displayed from a cached metadata snapshot.
      if(results.some(r=>r.status==='rejected'))failure.value='部分歌曲已不可访问；已隐藏不可用内容。'
    }else{
      const response=await getMusicList({current:next,pageSize:20,orderBy:'uploadTime',orderType:'desc',...(route.query.keyword?{keyword:String(route.query.keyword)}:{})})
      records=response.data.records||[];count=Number(response.data.total)||0
    }
    if(ticket!==requestId)return
    songs.value=append?[...new Map([...songs.value,...records].map(song=>[String(song.musicid),song])).values()]:records
    total.value=count;page.value=next
  }catch{if(ticket===requestId)failure.value='曲库加载失败，请检查服务后重试。'}
  finally{if(ticket===requestId)loading.value=false}
}
async function more(){if(limit.value<filtered.value.length)limit.value+=8;else{await load(true);limit.value+=20}}
function resetFilters(){genre.value='全部';sort.value='recent';router.replace({path:route.path,query:{}})}
function playSong(song){if(String(player.current?.musicid)===String(song.musicid))player.toggle();else player.play(song,filtered.value)}
function playFirst(){if(songs.value.length)player.play(songs.value[0],songs.value)}
async function openDetail(song){
  const ticket=++detailId
  detail.value=null;detailError.value='';detailLoading.value=true;drawer.value=true
  try{const response=await getMusicDetail(song.musicid);if(ticket===detailId)detail.value=response.data}
  catch{if(ticket===detailId)detailError.value='这首歌曲当前不可访问，请刷新曲库后重试。'}
  finally{if(ticket===detailId)detailLoading.value=false}
}
watch(()=>route.fullPath,()=>{genre.value=String(route.query.genre||'全部');selectedArtist.value='';load()},{immediate:true})
watch(()=>player.favorites.length,()=>{if(mode.value==='favorites'&&!loading.value)load()})
onMounted(async()=>{
  try{
    const [a,b]=await Promise.all([fetch('/artist-references.json'),fetch('/demo-catalog.json')])
    if(!a.ok||!b.ok)throw new Error()
    references.value=(await a.json()).tracks||[];catalog.value=(await b.json()).audioTracks||[]
  }catch{referenceError.value='歌手资料或授权目录暂时无法加载。'}
})
</script>
<template>
  <section class="pageintro"><div><div class="eyebrow">A SPACE FOR YOUR SOUND</div><h1>{{ titles[0] }}</h1><p>{{ titles[1] }}</p></div><router-link class="upload-btn" to="/upload" aria-label="导入音乐"><Icon name="upload" /><span>导入音乐</span></router-link></section>
  <section class="hero-layout" v-if="!route.query.keyword && !route.query.genre && route.path==='/music'"><div class="hero"><div class="hero-copy"><div class="eyebrow">THE EVENING COLLECTION · VOL. 01</div><h2>音量调低一点，<br>世界慢下来。</h2><p>把忙碌留在门外。<br>让温柔的人声与松弛的节拍，陪你度过这一刻。</p><div class="hero-actions"><button class="primary" @click="playFirst" :disabled="!songs.length"><svg class="icon small" style="fill:currentColor;stroke:none"><use href="#i-play"/></svg>播放精选</button><button class="hero-link" @click="collection?.scrollIntoView({behavior:'smooth'})">浏览曲库<svg class="icon small"><use href="#i-arrow"/></svg></button></div></div><div class="hero-art" aria-hidden="true"><div class="record"></div><div class="sleeve"><div class="circle"></div><div class="hill"></div><div class="hill second"></div><small>SLOWER / SOFTER</small></div></div><div class="hero-bottom"><span></span> CURATED WITH CARE</div></div><div class="feature-stack"><button class="feature" @click="collection?.scrollIntoView({behavior:'smooth'})"><div class="eyebrow">FRESH IN YOUR LIBRARY</div><h3>新声音，刚刚抵达。</h3><p>探索最近添加的音乐</p><svg class="icon"><use href="#i-arrow"/></svg></button><button class="feature alt" @click="router.push('/artists')"><div class="eyebrow">ARTIST SPOTLIGHT</div><h3>熟悉的声音。</h3><p>Post Malone &amp; Drake · 歌曲资料</p><svg class="icon"><use href="#i-arrow"/></svg></button></div></section>
  <section ref="collection" class="sonora-collection">
    <div class="section-heading"><h2>{{ titles[2] }} <span class="count-badge">{{ artistMode?2:total }}</span></h2><button class="link" @click="resetFilters">清除筛选</button></div>
    <template v-if="artistMode">
      <div class="artist-grid"><button v-for="(artist,i) in ['Post Malone','Drake']" :key="artist" class="artist-card" :class="{chosen:selectedArtist===artist}" :aria-pressed="selectedArtist===artist" @click="selectedArtist=selectedArtist===artist?'':artist"><span class="eyebrow">ARTIST / 0{{i+1}}</span><div class="initials" aria-hidden="true">{{i?'DR':'PM'}}</div><h2>{{artist}}</h2><p>{{references.filter(t=>t.artist===artist).length}} 条歌曲资料 · 查看歌曲档案 <Icon name="arrow" /></p></button></div>
      <p class="hint">歌曲资料与官方页面链接，此处未导入这两位歌手的完整音频。</p><input class="artist-search" v-model="artistQuery" type="search" placeholder="搜索歌手资料" aria-label="搜索歌手资料">
      <p v-if="referenceError" class="inline-error" role="alert">{{referenceError}}</p><div v-for="(track,i) in artistRows" :key="track.sourceUrl" class="reference"><span class="ref-index">{{String(i+1).padStart(2,'0')}}</span><div class="ref-info"><div class="ref-title">{{track.title}}</div><small>{{track.artist}} / {{track.album}}</small></div><a v-if="safeLink(track.sourceUrl)" :href="safeLink(track.sourceUrl)" target="_blank" rel="noopener noreferrer">官方页面 ↗</a></div><div v-if="!artistRows.length&&!referenceError" class="empty">没有匹配的歌曲资料。</div>
    </template>
    <template v-else>
      <div class="toolbar"><div class="chips"><button v-for="g in ['全部','流行','电子','民谣','嘻哈']" :key="g" class="chip" :class="{active:genre===g}" :aria-pressed="genre===g" @click="genre=g;limit=8">{{g}}</button></div><div class="viewtools"><select class="sort" v-model="sort" aria-label="歌曲排序"><option value="recent">最近添加</option><option value="name">名称 A → Z</option><option value="duration">时长最短</option></select><div class="viewtoggle"><button :class="{active:layout==='grid'}" :aria-pressed="layout==='grid'" aria-label="封面视图" @click="layout='grid'"><Icon name="grid" /></button><button :class="{active:layout==='list'}" :aria-pressed="layout==='list'" aria-label="列表视图" @click="layout='list'"><Icon name="list" /></button></div></div></div>
      <p v-if="route.query.keyword" class="hint">搜索 “{{route.query.keyword}}” · {{total}} 首结果</p>
      <p v-if="mode==='favorites'||mode==='recent'" class="hint">{{mode==='favorites'?'收藏':'播放历史'}}保存在此浏览器中，按登录账号区分。</p>
      <p v-if="hasMore" class="hint">已加载 {{songs.length}} / {{total}} 首；风格和排序应用于已加载曲目。</p>
      <div v-if="failure" class="inline-error" role="alert">{{failure}} <button class="link" @click="load()">重试</button></div>
      <div v-if="loading&&!songs.length" class="empty" role="status">正在整理你的音乐空间…</div>
      <div v-else class="grid" :class="{listmode:layout==='list'}">
        <article v-for="song in filtered.slice(0,limit)" :key="song.musicid" class="album" :class="{playing:player.playing&&String(player.current?.musicid)===String(song.musicid)}">
          <div class="art-wrap"><div class="cover-holder" v-html="coverFor(song)"></div><div class="art-shade"></div><button v-if="layout==='grid'" class="icon-btn album-like" :class="{selected:player.favoriteSet.has(String(song.musicid))}" :aria-label="(player.favoriteSet.has(String(song.musicid))?'取消收藏 ':'收藏 ')+song.title" :aria-pressed="player.favoriteSet.has(String(song.musicid))" @click="player.toggleFavorite(song)"><Icon name="heart" /></button><button class="album-play" :disabled="player.loading" :aria-label="(player.playing&&String(player.current?.musicid)===String(song.musicid)?'暂停 ':'播放 ')+song.title" @click="playSong(song)"><Icon :name="player.playing&&String(player.current?.musicid)===String(song.musicid)?'pause':'play'" /></button></div>
          <div class="album-info"><div class="album-title"><button :title="song.title" @click="openDetail(song)">{{song.title}}</button><span v-if="player.playing&&String(player.current?.musicid)===String(song.musicid)" class="eq" aria-label="正在播放"><i></i><i></i><i></i></span></div><div class="album-sub"><span class="artist">{{song.artist||'未知歌手'}}</span><span class="track-time">{{durationOf(song)?formatTime(durationOf(song)):'—'}}</span></div></div>
          <button v-if="layout==='list'" class="icon-btn album-like" :class="{selected:player.favoriteSet.has(String(song.musicid))}" :aria-label="(player.favoriteSet.has(String(song.musicid))?'取消收藏 ':'收藏 ')+song.title" :aria-pressed="player.favoriteSet.has(String(song.musicid))" @click="player.toggleFavorite(song)"><Icon name="heart" /></button>
        </article>
        <div v-if="!filtered.length&&!failure" class="empty"><h3>{{mode==='favorites'?'把喜欢的歌，放进这里。':mode==='recent'?'还没有播放记录。':'没有找到匹配的音乐。'}}</h3><p>{{mode==='favorites'?'点击封面上的爱心，留下喜欢的声音。':'试试其他关键词、风格，或导入新的音乐。'}}</p><button class="secondary" @click="resetFilters">清除筛选</button></div>
      </div>
      <button v-if="limit<filtered.length||hasMore" class="loadmore" :disabled="loading" @click="more">{{loading?'正在加载…':'展开更多音乐'}}</button>
    </template>
  </section>
  <footer class="library-footer"><span><b>SONORA</b> &nbsp; 好的音乐，值得被认真收藏。</span><span>封面为原创概念设计</span></footer>
  <el-drawer v-model="drawer" title="歌曲详情" size="min(420px, 100%)">
    <div v-if="detailLoading" role="status" class="hint">正在加载详情…</div><p v-if="detailError" role="alert" class="inline-error">{{detailError}}</p>
    <template v-if="detail"><div class="drawer-art" v-html="coverFor(detail)"></div><h2>{{detail.title}}</h2><div class="drawer-artist">{{detail.artist||'未知歌手'}}</div><div class="detail-line"><span>专辑</span><span>{{detail.album||'未填写'}}</span></div><div class="detail-line"><span>风格</span><span>{{detail.genre||'未分类'}}</span></div><div class="detail-line"><span>时长</span><span>{{formatTime(durationOf(detail))}}</span></div><div class="detail-line"><span>审核状态</span><span>{{detail.approvalStatus||'—'}}</span></div><div v-if="attribution" class="license">{{attribution.license}} · {{attribution.artist}}<br>原音频未修改<br><a v-if="safeLink(attribution.sourceUrl)" :href="safeLink(attribution.sourceUrl)" target="_blank" rel="noopener noreferrer">来源页面 ↗</a> &nbsp; <a v-if="safeLink(attribution.licenseUrl)" :href="safeLink(attribution.licenseUrl)" target="_blank" rel="noopener noreferrer">查看许可 ↗</a></div><button class="primary" :disabled="player.loading" @click="player.play(detail,songs)"><Icon name="play" />播放歌曲</button><router-link class="detail-manage" to="/manage/music" @click="drawer=false">前往资源管理，编辑歌曲资料 ↗</router-link></template>
  </el-drawer>
</template>
