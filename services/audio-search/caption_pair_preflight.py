"""Conservative source metadata reconciliation and bounded codec-version diagnostics."""
from collections import Counter
import hashlib
import math
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit


def require(ok, message):
    if not ok: raise ValueError(message)


def norm(text):
    return ''.join(c for c in unicodedata.normalize('NFKC', text).casefold() if c.isalnum())


def license_uri(value):
    if not isinstance(value, str): return None
    p = urlsplit(value)
    m = re.fullmatch(r'/licenses/(by(?:-nc)?(?:-sa|-nd)?)/(\d\.\d)/(?:[a-z]{2}/)?', p.path)
    if p.scheme not in ('http', 'https') or p.netloc != 'creativecommons.org' or p.query or p.fragment or not m:
        return None
    return ('https://creativecommons.org'+p.path, m[1])


def reference_url(value, tid):
    if not isinstance(value, str): return None
    p = urlsplit(value)
    if (p.scheme not in ('http', 'https') or not p.hostname or p.netloc != p.hostname
            or not re.fullmatch(r'prod-[0-9]+\.storage\.jamendo\.com', p.hostname)
            or p.path != '/download/track/'+tid+'/mp32/' or p.query or p.fragment): return None
    return urlunsplit(('https', p.netloc, p.path, '', ''))


def reconcile(original, rows, *, duration_tolerance=1.0):
    tid = original['id']; reasons = []; licenses = [license_uri(r.get('license_ccurl')) for r in rows]
    if not rows: reasons.append('missing_source_metadata')
    if any(str(r.get('id')) != tid for r in rows): reasons.append('source_ID_mismatch')
    if not licenses or any(v is None or v[1] not in ('by', 'by-sa') for v in licenses):
        reasons.append('license_outside_explicit_BY_BYSA')
    if len({v[0] for v in licenses if v}) > 1: reasons.append('conflicting_license_URIs')
    if any(type(r.get('audiodownload_allowed')) is not bool or r['audiodownload_allowed'] is not True for r in rows):
        reasons.append('download_not_unanimously_allowed')
    if any(str(r.get('artist_id')) != original['artist_id'] or not isinstance(r.get('name'), str)
           or norm(r['name']) != norm(original['title']) for r in rows): reasons.append('artist_or_work_identity_mismatch')
    durations = [r.get('duration') for r in rows]
    if any(type(d) not in (int, float) or not math.isfinite(d) or abs(d-original['duration_seconds']) > duration_tolerance
           for d in durations): reasons.append('duration_disagrees_with_actual_EOF')
    if len({float(d) for d in durations if type(d) in (int, float) and math.isfinite(d)}) > 1:
        reasons.append('conflicting_metadata_duration')
    urls = [reference_url(r.get('audiodownload'), tid) for r in rows]
    if not urls or any(u is None for u in urls) or len(set(urls)) != 1: reasons.append('unresolved_download_source')
    return {'id': tid, 'metadata_rows': len(rows), 'eligible': not reasons, 'reasons': reasons,
            'source_license_URIs': sorted({v[0] for v in licenses if v}),
            'reference_url': urls[0] if not reasons else None,
            'reference_is_exact_teacher_artifact': False}


def choose_references(originals, verdicts, captions, count, seed):
    counts = Counter(r['id'] for r in captions); good = {v['id'] for v in verdicts if v['eligible']}
    candidates = [r for r in originals if r['id'] in good and r['split'] == 'train' and counts[r['id']] >= 3]
    candidates.sort(key=lambda r: (hashlib.sha256((seed+'\n'+r['id']).encode()).hexdigest(), int(r['id'])))
    selected, groups = [], set()
    for r in candidates:
        if r['creator_component'] not in groups:
            selected.append(r['id']); groups.add(r['creator_component'])
            if len(selected) == count: break
    return selected


def anchor_intervals(captions):
    ordered = sorted(captions, key=lambda r: (r['start_time'], r['end_time']))
    require(len(ordered) >= 3, 'Three fixed interval anchors required')
    return [ordered[i] for i in sorted({0, len(ordered)//2, len(ordered)-1})]


def sample_bounds(start, end, rate, samples):
    require(type(rate) is int and rate > 0 and type(samples) is int and samples > 0
            and type(start) in (int, float) and type(end) in (int, float)
            and math.isfinite(start) and math.isfinite(end) and 0 <= start < end <= samples/rate,
            'Finite interval inside verified EOF required')
    a, b = round(start*rate), round(end*rate)
    require(0 <= a < b <= samples, 'Invalid discrete sample interval')
    return a, b


def correlation_curve(x, reference_search):
    import numpy as np
    from scipy.signal import correlate
    x = np.asarray(x, dtype=np.float64); y = np.asarray(reference_search, dtype=np.float64)
    require(x.ndim == y.ndim == 1 and 0 < len(x) <= len(y) and np.isfinite(x).all() and np.isfinite(y).all(),
            'Finite mono reference arrays required')
    centered = x-x.mean(); energy = float(centered@centered)
    require(energy > 1e-12, 'Silent anchor cannot establish alignment')
    sums = np.concatenate(([0.], np.cumsum(y))); squares = np.concatenate(([0.], np.cumsum(y*y)))
    n = len(x); sums = sums[n:]-sums[:-n]; variances = squares[n:]-squares[:-n]-sums*sums/n
    denominator = np.sqrt(energy*np.maximum(variances, 0))
    dots = correlate(y, centered, mode='valid', method='fft')
    return np.divide(dots, denominator, out=np.zeros_like(dots), where=denominator > 1e-12)


def align(original, reference, intervals, cfg):
    import numpy as np
    from scipy.signal import resample_poly
    require(cfg['sample_rate_hz'] == 48000 and cfg['diagnostic_rate_hz'] == 8000, 'Fixed audio rate recipe required')
    require(original.ndim == reference.ndim == 1 and np.isfinite(original).all() and np.isfinite(reference).all(),
            'Finite decoded mono required')
    a = resample_poly(original, 1, 6); b = resample_poly(reference, 1, 6)
    rate = cfg['diagnostic_rate_hz']; n = rate*10; radius = round(rate*cfg['search_lag_seconds'])
    duration_delta = abs(len(original)-len(reference))/48000; reports = []; probes = {}
    for i, interval in enumerate(anchor_intervals(intervals)):
        first, last = sample_bounds(interval['start_time'], interval['end_time'], 48000, len(original))
        start = ((first+last)//2-48000*5)//6
        require(start >= radius and start+n+radius <= len(b) and start+n <= len(a), 'Reference lacks full fixed anchor search')
        x, y = a[start:start+n], b[start-radius:start+n+radius]
        curve = correlation_curve(x, y); lags = np.arange(len(curve))-radius
        best = int(np.lexsort((lags, np.abs(lags), -curve))[0]); lag = float(lags[best]/rate)
        passed = float(curve[best]) >= cfg['min_normalized_correlation'] and abs(lag) <= cfg['max_accepted_lag_seconds']
        reports.append({'caption_start': interval['start_time'], 'caption_end': interval['end_time'],
                        'original_sample_start': first, 'original_sample_end': last, 'anchor8k_start': start,
                        'best_correlation': float(curve[best]), 'zero_lag_correlation': float(curve[radius]),
                        'best_lag_seconds': lag, 'passed': bool(passed)})
        probes['x'+str(i)] = x; probes['reference'+str(i)] = y
    return {'duration_delta_seconds': duration_delta, 'anchors': reports,
            'passed': duration_delta <= cfg['max_duration_delta_seconds'] and all(r['passed'] for r in reports),
            'scope': 'current same-ID reference snapshot only, not exact teacher bytes or all recordings'}, probes
