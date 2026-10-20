"""Additive V002 migration. Query callback accepts SQL and returns unheaded text rows."""
from pathlib import Path
import re

SQL = Path(__file__).resolve().parents[1] / 'music/src/main/resources/db/baseline/V002__upload_ownership.sql'
TABLES = {'users', 'music_categories', 'file_upload', 'file_chunk', 'music_resources',
          'music_tags', 'music_resource_tags', 'audit_logs', 'recycle_bin',
          'recycle_bin_settings', 'development_schema_version'}
UPLOAD_COLUMNS = {
    'id': ('bigint', 'NO'), 'file_name': ('varchar(255)', 'NO'),
    'file_size': ('bigint', 'NO'), 'file_md5': ('varchar(32)', 'NO'),
    'file_path': ('varchar(255)', 'NO'), 'file_type': ('varchar(50)', 'NO'),
    'chunk_size': ('int', 'NO'), 'chunk_count': ('int', 'NO'),
    'uploaded_chunks': ('int', 'NO'), 'status': ('tinyint', 'NO'),
    'upload_time': ('datetime', 'NO'), 'complete_time': ('datetime', 'YES'),
    'create_time': ('datetime', 'NO'), 'update_time': ('datetime', 'NO'),
    'deleted': ('tinyint', 'NO'),
}


def normalized_type(value):
    # MySQL releases differ in integer display widths, which do not affect storage.
    return re.sub(r'^(bigint|int|tinyint)\(\d+\)', r'\1', value.lower())


def validate_baseline(query):
    names = query('SELECT TABLE_NAME FROM information_schema.tables WHERE table_schema=DATABASE() ORDER BY TABLE_NAME;')
    if len(names) != len(TABLES) or set(names) != TABLES:
        raise RuntimeError('Unexpected baseline table names; no migration or repair attempted.')
    rows = query("SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='file_upload' ORDER BY ORDINAL_POSITION;")
    columns = {}
    for row in rows:
        fields = row.split('\t')
        if len(fields) != 3 or fields[0] in columns:
            raise RuntimeError('Unexpected upload column metadata; no migration attempted.')
        columns[fields[0]] = (normalized_type(fields[1]), fields[2])
    required = {k: v for k, v in columns.items() if k != 'owner_user_id'}
    if required != UPLOAD_COLUMNS:
        raise RuntimeError('Unexpected V001 upload columns; no migration or repair attempted.')
    primary = query("SELECT COLUMN_NAME, NON_UNIQUE FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='file_upload' AND index_name='PRIMARY' ORDER BY SEQ_IN_INDEX;")
    identity = query("SELECT EXTRA FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='file_upload' AND column_name='id';")
    if primary != ['id\t0'] or identity != ['auto_increment']:
        raise RuntimeError('Unexpected upload primary key; no migration attempted.')


def validate_structure(query):
    validate_baseline(query)
    column = query("SELECT COLUMN_TYPE, IS_NULLABLE, IF(COLUMN_DEFAULT IS NULL, '<NULL>', COLUMN_DEFAULT), IF(EXTRA='', '<EMPTY>', EXTRA) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='file_upload' AND column_name='owner_user_id';")
    index = query("SELECT COLUMN_NAME, NON_UNIQUE, INDEX_TYPE FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='file_upload' AND index_name='idx_upload_owner_md5' ORDER BY SEQ_IN_INDEX;")
    if column != ['bigint\tYES\t<NULL>\t<EMPTY>'] or index != [name+'\t1\tBTREE' for name in ['owner_user_id', 'file_md5', 'deleted']]:
        raise RuntimeError('Unexpected upload ownership structure; preserved without repair.')


def migrate(query):
    # Refuse even same-sized substituted schemas before any DDL or marker write.
    validate_baseline(query)
    versions = query('SELECT version FROM development_schema_version ORDER BY version;')
    if versions not in (['1'], ['1', '2']):
        raise RuntimeError('V002 requires the recognized V001 development baseline.')
    column = query("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='file_upload' AND column_name='owner_user_id';")
    if column == ['0']:
        if versions != ['1']:
            raise RuntimeError('Schema version and column disagree; no repair attempted.')
        query(SQL.read_text())  # Single atomic MySQL 8 ALTER, no owner backfill or credential mutation.
    elif column != ['1']:
        raise RuntimeError('Unexpected ownership column count.')
    validate_structure(query)
    # DDL can commit before the version insert. Retry only the exact recognized structure.
    if versions == ['1']:
        query("INSERT INTO development_schema_version (version, description) VALUES (2, 'Upload ownership; legacy records quarantined');")
    return {'version': 2, 'legacy_owner_policy': 'NULL retained; no automatic claim',
            'legacy_rows': int(query('SELECT COUNT(*) FROM file_upload WHERE owner_user_id IS NULL;')[0])}
