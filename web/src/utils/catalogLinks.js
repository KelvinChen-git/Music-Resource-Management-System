/** Only canonical public music/attribution pages; never retain arbitrary query data. */
export function safeCatalogLink(value) {
  try {
    const url = new URL(value)
    if (url.protocol !== 'https:' || url.username || url.password || url.port) return ''
    if (url.hostname === 'www.jamendo.com') {
      const match = url.pathname.match(/^\/track\/([1-9][0-9]*)(?:\/.*)?$/)
      return match ? `https://www.jamendo.com/track/${match[1]}` : ''
    }
    if (url.hostname === 'creativecommons.org') {
      return /^\/licenses\/by\/(2\.0|2\.5|3\.0|4\.0)\/$/.test(url.pathname)
        ? `https://creativecommons.org${url.pathname}` : ''
    }
    if (!['music.apple.com', 'itunes.apple.com'].includes(url.hostname)) return ''
    const ids = url.searchParams.getAll('i')
    if (ids.length > 1 || (ids.length === 1 && !/^[1-9][0-9]*$/.test(ids[0]))) return ''
    url.search = ''
    url.hash = ''
    if (ids.length) url.searchParams.set('i', ids[0])
    return url.href
  } catch { return '' }
}
