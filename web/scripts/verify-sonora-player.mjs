// Verify playback concurrency and account isolation without a server or real media.
import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import { createPinia, setActivePinia } from 'pinia'
import { reactive, nextTick } from 'vue'
const root = fileURLToPath(new URL('../', import.meta.url))
const storage = new Map()
const revoked = []
const originalStorage = globalThis.localStorage
const originalRevoke = URL.revokeObjectURL
const originalUser = globalThis.__sonoraTestUser
const originalMedia = globalThis.__sonoraTestMedia
globalThis.localStorage = { getItem:key=>storage.get(key)??null, setItem:(key,value)=>storage.set(key,value) }
URL.revokeObjectURL = url => revoked.push(url)
globalThis.__sonoraTestUser = reactive({userId:1})
const server = await createServer({configFile:false,root,optimizeDeps:{noDiscovery:true,include:[]},server:{middlewareMode:true},resolve:{alias:{'@':fileURLToPath(new URL('../src',import.meta.url))}},plugins:[{name:'sonora-test-boundaries',load(id){
  if(id.endsWith('/api/music.js')) return 'export const createMusicUrl=(...args)=>globalThis.__sonoraTestMedia(...args)'
  if(id.endsWith('/stores/user.js')) return 'export const useUserStore=()=>globalThis.__sonoraTestUser'
}}]})
try {
  setActivePinia(createPinia())
  const {useSonoraPlayer} = await server.ssrLoadModule('/src/stores/sonoraPlayer.js')
  const player = useSonoraPlayer()
  const audio = {src:'',paused:true,ended:false,currentTime:0,duration:0,volume:1,load(){},pause(){this.paused=true},play(){this.paused=false;return Promise.resolve()},removeAttribute(){this.src=''},getAttribute(){return this.src}}
  player.attach(audio)
  const calls=[]
  globalThis.__sonoraTestMedia=async(...args)=>{calls.push(args);return 'blob:first'}
  await player.play({musicid:7,title:'First'})
  player.sync()
  assert.deepEqual(calls,[[7,true]],'Every playback must request authenticated media through the existing API boundary')
  assert.equal(audio.src,'blob:first')
  assert.equal(player.playing,true)
  assert.deepEqual(player.recent,['7'])
  console.log('PASS authenticated-media boundary and successful-play history')

  const deferred=new Map()
  globalThis.__sonoraTestMedia=id=>new Promise(resolve=>deferred.set(id,resolve))
  const older=player.play({musicid:8,title:'Older'})
  const newer=player.play({musicid:9,title:'Newer'})
  deferred.get(9)('blob:newer');await newer
  deferred.get(8)('blob:older');await older
  assert.equal(audio.src,'blob:newer')
  assert.equal(player.current.musicid,9)
  assert(revoked.includes('blob:older'))
  assert(revoked.includes('blob:first'))
  assert.deepEqual(player.recent,['9','7'])
  console.log('PASS superseded requests cannot replace audio or history; old blobs released')

  player.toggleFavorite({musicid:9})
  assert.equal(storage.get('sonora:1:favorites:v1'),'["9"]')
  const pending=player.play({musicid:10,title:'Pending'})
  globalThis.__sonoraTestUser.userId=2;await nextTick()
  deferred.get(10)('blob:logged-out');await pending
  assert.equal(audio.src,'')
  assert.equal(player.current,null)
  assert.equal(player.loading,false)
  assert.deepEqual(player.favorites,[])
  assert.deepEqual(player.recent,[])
  assert(revoked.includes('blob:newer'))
  assert(revoked.includes('blob:logged-out'))
  console.log('PASS account switch cancels pending playback, clears queue and releases media')

  player.toggleFavorite({musicid:11})
  assert.equal(storage.get('sonora:2:favorites:v1'),'["11"]')
  globalThis.__sonoraTestUser.userId=1;await nextTick()
  assert.deepEqual(player.favorites,['9'])
  assert.deepEqual(player.recent,['9','7'])
  console.log('PASS favorites and history persist separately for each account')

  globalThis.__sonoraTestMedia=async()=>{throw Error('forbidden')}
  await player.play({musicid:12,title:'Denied'})
  assert.equal(player.playing,false)
  assert.equal(player.loading,false)
  assert(player.error)
  assert(!player.recent.includes('12'))
  player.reset()
  console.log('PASS failed media access does not enter history or report playback')
} finally {
  await server.close()
  URL.revokeObjectURL=originalRevoke
  if(originalStorage===undefined)delete globalThis.localStorage;else globalThis.localStorage=originalStorage
  if(originalUser===undefined)delete globalThis.__sonoraTestUser;else globalThis.__sonoraTestUser=originalUser
  if(originalMedia===undefined)delete globalThis.__sonoraTestMedia;else globalThis.__sonoraTestMedia=originalMedia
}
