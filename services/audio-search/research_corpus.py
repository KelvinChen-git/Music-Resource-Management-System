"""Pinned, read-only two-provider research assets; no API, credentials or labels."""
from pathlib import Path
import stat

import review_pack as rp
import source_review_pack as source_review

SOURCE_DECODE_VERSION = 'soundfile-read-out-65536-actual-eof-v1'


def decode_source_mono(path, recorded_decode):
    """Read valid MP3 frames to actual EOF; historical header length is only a binding."""
    import librosa
    import numpy as np
    import soundfile as sf
    from preprocess import SAMPLE_RATE

    rp.require(isinstance(recorded_decode, dict) and set(recorded_decode) ==
               {'frames', 'sample_rate_hz', 'channels', 'format', 'duration_ms'},
               'Expected historical source decode metadata')
    for key in ('frames', 'sample_rate_hz', 'channels', 'duration_ms'):
        rp.require(type(recorded_decode[key]) is int, 'Historical decode fields must be integers')
    with sf.SoundFile(path) as source:
        declared, rate, channels = source.frames, source.samplerate, source.channels
        rp.require(type(declared) is int and type(rate) is int and type(channels) is int
                   and source.format == 'MP3' and 8000 <= rate <= 192000 and channels in (1, 2)
                   and 0 < declared <= rate * 600,
                   'Unsupported source format/channels/rate/declared duration')
        rp.require(recorded_decode == {'frames': declared, 'sample_rate_hz': rate,
                   'channels': channels, 'format': source.format, 'duration_ms': declared * 1000 // rate},
                   'Historical source header binding mismatch')
        rp.require(source.tell() == 0, 'Source decoder must begin at frame zero')
        buffer = np.empty((65536, channels), dtype=np.float32)
        parts, actual = [], 0
        while True:
            before = source.tell()
            # Supplying out bypasses soundfile._check_frames(), which clamps to the estimated header.
            # No fill_value: only the returned valid view may be copied before the buffer is reused.
            block = source.read(frames=65536, out=buffer)
            after = source.tell()
            rp.require(isinstance(block, np.ndarray) and block.dtype == np.float32 and block.ndim == 2
                       and block.shape[1] == channels and block.flags.c_contiguous and len(block) <= 65536,
                       'Invalid actual-EOF decoder return buffer')
            count = len(block)
            rp.require(type(before) is int and type(after) is int and before == actual
                       and after - before == count, 'Decoder position/actual frame count mismatch')
            rp.require(np.isfinite(block).all(), 'Nonfinite actual source samples')
            if count == 0:
                break
            actual += count
            rp.require(actual <= rate * 600, 'Actual source exceeds 600-second decode cap')
            parts.append(block.copy())
        rp.require(rate * 30 <= actual <= rate * 600, 'Actual source must contain 30..600 seconds')
        info = {'format': source.format, 'source_frames': actual, 'declared_source_frames': declared,
                'source_sample_rate_hz': rate, 'source_channels': channels}
    samples = np.concatenate(parts).mean(axis=1)
    if rate != SAMPLE_RATE:
        expected = (actual * SAMPLE_RATE + rate - 1) // rate
        samples = librosa.resample(samples, orig_sr=rate, target_sr=SAMPLE_RATE,
                                   res_type='soxr_hq', fix=False)
        samples = librosa.util.fix_length(samples, size=expected)
    rp.require(len(samples) == (actual * SAMPLE_RATE + rate - 1) // rate
               and np.isfinite(samples).all(), 'Invalid actual-EOF resampled source samples')
    info.update(sample_rate_hz=SAMPLE_RATE, decoded_samples=len(samples),
                duration_ms=len(samples) * 1000 // SAMPLE_RATE)
    return np.ascontiguousarray(samples, dtype=np.float32), info


def checked_assets(*, catalog, audio_root, source_manifest, decode_report, baseline_catalog,
                   selection, queries, catalog_sha256, manifest_sha256, decode_sha256,
                   baseline_sha256, selection_sha256, queries_sha256):
    """Check imported40 and E7 provenance, returning canonical assets in Java-ID order."""
    pins = ((catalog, catalog_sha256), (source_manifest, manifest_sha256),
            (decode_report, decode_sha256), (baseline_catalog, baseline_sha256),
            (selection, selection_sha256), (queries, queries_sha256))
    for _, digest in pins:
        rp.sha(digest)  # No omitted/None pin can disable validation.
    for path, digest in pins:
        rp.read_json(path, expected=digest)
    expected = source_review.prepare(source_manifest, decode_report, catalog, queries,
        manifest_sha256, decode_sha256, catalog_sha256, queries_sha256, selection, baseline_catalog)
    rp.require(expected['provenance']['source_selection_sha256'] == selection_sha256,
               'Source selection explicit pin differs from manifest')
    manifest, _ = rp.read_json(source_manifest, expected=manifest_sha256)
    rp.require(manifest['baseline_catalog_sha256'] == baseline_sha256,
               'Baseline explicit pin differs from manifest')
    imported, _ = rp.read_json(catalog, expected=catalog_sha256)
    decoded, _ = rp.read_json(decode_report, expected=decode_sha256)
    decoded = {row['source_id']: row for row in decoded['tracks']}
    source_by_id = {row['source_id']: row for row in manifest['tracks']}
    root = Path(audio_root).absolute()
    rp.require(not any(path.is_symlink() for path in (root, *root.parents))
               and root.is_dir(), 'Audio root must be an independent regular directory')
    root = root.resolve(strict=True)
    source_root = Path(source_manifest).parent.resolve(strict=True)
    rp.require(root != source_root and not root.is_relative_to(source_root)
               and not source_root.is_relative_to(root), 'Imported audio must be independent of source batch')
    files = {}

    def read_asset(name, limit, directory=root):
        rp.require(isinstance(name, str) and name == Path(name).name and name not in ('', '.', '..'),
                   'Invalid asset filename')
        path = directory / name
        rp.require(not any(p.is_symlink() for p in (path, *path.parents))
                   and path.resolve(strict=True).is_relative_to(directory), 'Asset escapes root or traverses symlink')
        info = path.stat()
        rp.require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                   and 0 < info.st_size <= limit, 'Expected bounded independent regular asset, not a hard link')
        with path.open('rb') as handle:
            raw = handle.read(limit + 1)
        rp.require(len(raw) == info.st_size and 0 < len(raw) <= limit, 'Asset changed while being read')
        files[path] = (rp.digest(raw), limit)
        return raw

    seen_tracks, seen_files, seen_sources, seen_contents = set(), set(), set(), set()
    providers = {'jamendo': 0, 'incompetech': 0}
    assets = []
    for row in imported['audioTracks']:
        provider = row['sourceProvider']
        rp.require(provider in providers, 'Unknown source provider')
        tid = rp.identity(row['musicId'], catalog=True)
        fid = rp.identity(row['fileId'], catalog=True)
        sid = row['sourceId']
        if provider == 'jamendo':
            rp.identity(sid)
        else:
            rp.require(isinstance(sid, str) and source_review.ISRC.fullmatch(sid)
                       and sid in source_by_id, 'Invalid or unknown source ISRC')
        rp.require(tid not in seen_tracks and fid not in seen_files and (provider, sid) not in seen_sources,
                   'Duplicate Java or provider/source identity')
        source_url, license_url = row['sourceUrl'], row['licenseUrl']
        if provider == 'jamendo':
            _, license_url = rp.public_urls(source_url, sid, license_url)
        else:
            rp.require(source_url == source_review.BASE + 'index.html?isrc=' + sid
                       and license_url == source_review.LICENSE, 'Source identity/CC BY4 URL mismatch')
        name = provider + '-' + sid
        raw = read_asset(name + '.mp3', 30 * 1024 * 1024)
        digest = rp.digest(raw)
        rp.require(digest == rp.sha(row['sha256']) and digest not in seen_contents,
                   'Audio/catalog mismatch or duplicate content')
        proof_raw = read_asset(name + '.download.json', 2 * 1024 * 1024)
        proof, _ = rp.read_json(root / (name + '.download.json'))
        if provider == 'jamendo':
            rp.require(isinstance(proof, dict) and set(proof) == {'sha256', 'size', 'source', 'license'},
                       'Unexpected original download proof fields')
            proof_source, proof_license = rp.public_urls(proof['source'], sid, proof['license'])
            recorded_source, _ = rp.public_urls(source_url, sid, license_url)
            rp.require(proof_source == recorded_source and proof['source'] == source_url
                       and proof_license == license_url and proof['sha256'] == digest
                       and type(proof['size']) is int and proof['size'] == len(raw),
                       'Original proof/catalog/audio mismatch')
        else:
            source = source_by_id[sid]
            original_proof = read_asset(sid + '.download.json', 2 * 1024 * 1024, source_root)
            rp.require(proof_raw == original_proof and source['sha256'] == digest
                       and row['contentBytes'] == len(raw) == source['bytes'],
                       'Imported source proof bytes/content differ from original batch')
        asset = {'track_id': tid, 'source_id': sid, 'source_provider': provider,
                 'asset_filename': name + '.mp3', 'content_sha256': digest, 'bytes': len(raw),
                 'download_proof_sha256': rp.digest(proof_raw), 'source_url': source_url,
                 'license_url': license_url, 'title': rp.text(row['title'], 500),
                 'artist': rp.text(row['artist'], 500),
                 'provider_duration_seconds': rp.integer(row['durationSeconds'], 1, 600)}
        if provider == 'incompetech':
            asset['recorded_decode'] = {key: decoded[sid][key] for key in
                                       ('frames', 'sample_rate_hz', 'channels', 'format', 'duration_ms')}
        assets.append(asset)
        providers[provider] += 1
        seen_tracks.add(tid); seen_files.add(fid); seen_sources.add((provider, sid)); seen_contents.add(digest)
    rp.require(providers == {'jamendo': 20, 'incompetech': 20} and len(assets) == 40,
               'Expected original20 plus new20 source assets')
    for path, digest in pins:
        rp.read_json(path, expected=digest)
    for path, (digest, limit) in files.items():
        rp.require(rp.digest(read_asset(path.name, limit, path.parent)) == digest,
                   'Imported/source evidence changed during asset validation')
    return sorted(assets, key=lambda asset: int(asset['track_id']))
