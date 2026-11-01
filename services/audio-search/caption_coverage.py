"""Bounded generated-caption coverage, without audio/model imports or training readiness."""
from collections import Counter, defaultdict
import hashlib
import json
import math


def require(ok, message):
    if not ok:
        raise ValueError(message)


def numeric_id(value):
    require(type(value) in (str, int) and str(value).isascii() and str(value).isdigit()
            and int(value) > 0, 'Positive decimal source ID required')
    return str(int(value))


class Coverage:
    def __init__(self, allowlist, *, max_line_bytes=65536, min_seconds=15, max_seconds=30):
        require(allowlist and len({numeric_id(r['id']) for r in allowlist}) == len(allowlist),
                'Nonempty unique allowlist required')
        self.allowed = {numeric_id(r['id']): {**r, 'id': numeric_id(r['id'])} for r in allowlist}
        require(all(r['split'] in ('train', 'validation') and type(r['duration_seconds']) in (int, float)
                    and math.isfinite(r['duration_seconds']) and r['duration_seconds'] > 0
                    and isinstance(r['creator_component'], str) for r in allowlist), 'Invalid allowlist metadata')
        require(type(max_line_bytes) is int and max_line_bytes > 0 and 0 < min_seconds <= max_seconds,
                'Invalid line/interval limits')
        self.max_line_bytes, self.minimum, self.maximum = max_line_bytes, min_seconds, max_seconds
        self.lines = self.matched = self.duplicates = 0
        self.ids, self.seen, self.rows = set(), set(), []
        self.rejected = Counter()

    def add(self, raw):
        require(isinstance(raw, bytes) and 0 < len(raw) <= self.max_line_bytes, 'Line exceeds byte bound')
        if not raw.strip():
            return False
        row = json.loads(raw.decode('utf8'), parse_constant=lambda _: require(False, 'Nonfinite JSON constant'))
        require(isinstance(row, dict) and 'id' in row, 'Object with source ID required')
        tid = numeric_id(row['id']); self.ids.add(tid); self.lines += 1
        if tid not in self.allowed:
            return False  # Unknown captions are never retained, validated as supervision, or returned.
        self.matched += 1
        start, end, text = row.get('start_time'), row.get('end_time'), row.get('caption')
        if not (type(start) in (int, float) and type(end) in (int, float)
                and math.isfinite(start) and math.isfinite(end) and 0 <= start < end):
            self.rejected['invalid_time'] += 1
        elif not self.minimum <= end - start <= self.maximum + 1e-6:
            self.rejected['interval_length_outside_policy'] += 1
        elif end > self.allowed[tid]['duration_seconds']:
            self.rejected['beyond_verified_EOF'] += 1
        elif not isinstance(text, str) or not text.strip() or len(text) > 8192:
            self.rejected['invalid_caption'] += 1
        else:
            key = (tid, float(start), float(end), text)
            if key in self.seen:
                self.duplicates += 1
            else:
                self.seen.add(key)
                self.rows.append({'id': tid, 'start_time': float(start), 'end_time': float(end),
                                  'caption': text, 'label_source': 'model_generated',
                                  'raw_line_sha256': hashlib.sha256(raw).hexdigest()})
        return True  # Caller may retain this allowlisted raw line for independent verification.

    def finish(self):
        texts = defaultdict(set)
        for r in self.rows:
            texts[(r['id'], r['start_time'], r['end_time'])].add(r['caption'])
        conflicts = {k for k, v in texts.items() if len(v) > 1}
        accepted = [r for r in self.rows if (r['id'], r['start_time'], r['end_time']) not in conflicts]
        accepted.sort(key=lambda r: (int(r['id']), r['start_time'], r['end_time']))
        counts = Counter(r['id'] for r in accepted)
        overlap_pairs = 0
        for i, a in enumerate(accepted):
            for b in accepted[i + 1:]:
                if a['id'] != b['id']:
                    break
                overlap_pairs += max(a['start_time'], b['start_time']) < min(a['end_time'], b['end_time'])
        summary = {'source_rows': self.lines, 'source_unique_ids': len(self.ids), 'allowlisted_rows': self.matched,
                   'rejected_rows_by_reason': dict(self.rejected), 'exact_duplicate_valid_rows': self.duplicates,
                   'conflicting_intervals': len(conflicts), 'conflict_quarantined_unique_rows': len(self.rows) - len(accepted),
                   'accepted_unique_intervals': len(accepted), 'overlapping_interval_pairs': overlap_pairs,
                   'splits': {}, 'label_source': 'model_generated', 'training_ready': False}
        for split in ('train', 'validation'):
            records = [r for r in self.allowed.values() if r['split'] == split]
            covered = [r for r in records if counts[r['id']]]
            summary['splits'][split] = {'allowlisted_recordings': len(records), 'covered_recordings': len(covered),
                    'covered_creator_components': len({r['creator_component'] for r in covered}),
                    'accepted_intervals': sum(counts[r['id']] for r in records),
                    'intervals_per_recording_histogram': dict(Counter(counts[r['id']] for r in records))}
        return {'summary': summary, 'candidates': accepted}
