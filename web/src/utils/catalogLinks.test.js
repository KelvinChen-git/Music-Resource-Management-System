import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { safeCatalogLink } from './catalogLinks.js'

test('all existing catalog and reference links retain permitted destinations', () => {
  const local = JSON.parse(readFileSync(new URL('../../public/demo-catalog.json', import.meta.url)))
  const external = JSON.parse(readFileSync(new URL('../../public/artist-references.json', import.meta.url)))
  for (const track of local.audioTracks) {
    assert.equal(safeCatalogLink(track.sourceUrl), `https://www.jamendo.com/track/${track.sourceId}`)
    assert.equal(safeCatalogLink(track.licenseUrl), track.licenseUrl)
  }
  for (const track of external.tracks) {
    const original = new URL(track.sourceUrl)
    const safe = new URL(safeCatalogLink(track.sourceUrl))
    assert.equal(safe.origin, original.origin)
    assert.equal(safe.pathname, original.pathname)
    assert.equal(safe.searchParams.get('i'), original.searchParams.get('i'))
  }
})

test('Jamendo output uses only the validated track identity', () => {
  assert.equal(safeCatalogLink('https://www.jamendo.com/track/123/slug?client_id=canary#token'), 'https://www.jamendo.com/track/123')
  assert.equal(safeCatalogLink('https://www.jamendo.com/download/123'), '')
})

test('license output strips query and fragment and limits license family', () => {
  assert.equal(safeCatalogLink('https://creativecommons.org/licenses/by/4.0/?client_id=canary#token'), 'https://creativecommons.org/licenses/by/4.0/')
  assert.equal(safeCatalogLink('https://creativecommons.org/licenses/by-nc/4.0/'), '')
})

test('Apple retains only a single numeric song identity', () => {
  for (const host of ['music.apple.com', 'itunes.apple.com']) {
    assert.equal(safeCatalogLink(`https://${host}/us/album/fixture/123?i=456&client_id=canary#secret`), `https://${host}/us/album/fixture/123?i=456`)
  }
})

test('invalid and ambiguous song identity queries are rejected', () => {
  for (const query of ['i=canary', 'i=1&i=2', 'i=', 'i=0']) {
    assert.equal(safeCatalogLink(`https://music.apple.com/us/album/fixture/123?${query}`), '')
  }
})

test('userinfo, disguised hosts and unexpected ports are rejected', () => {
  for (const value of ['https://canary@www.jamendo.com/track/123', 'https://user:canary@music.apple.com/album/123',
    'https://www.jamendo.com.evil.invalid/track/123', 'https://www.jamendo.com:444/track/123']) {
    assert.equal(safeCatalogLink(value), '')
  }
})

test('non-HTTPS and invalid inputs cannot become links', () => {
  for (const value of ['http://www.jamendo.com/track/123', 'javascript:alert(1)', 'file:///tmp/fixture', '', null, undefined]) {
    assert.equal(safeCatalogLink(value), '')
  }
})

test('unknown HTTPS hosts are rejected', () => {
  assert.equal(safeCatalogLink('https://example.invalid/track/123?client_id=canary'), '')
})
