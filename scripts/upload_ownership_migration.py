"""Additive V002 migration. Query callback accepts SQL and returns unheaded text rows."""
from pathlib import Path

SQL = Path(__file__).resolve().parents[1] / 'music/src/main/resources/db/baseline/V002__upload_ownership.sql'


def validate_structure(query):
    column = query("SELECT COLUMN_TYPE, IS_NULLABLE FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='file_upload' AND column_name='owner_user_id';")
    index = query("SELECT COLUMN_NAME FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='file_upload' AND index_name='idx_upload_owner_md5' ORDER BY SEQ_IN_INDEX;")
    if column != ['bigint\tYES'] or index != ['owner_user_id', 'file_md5', 'deleted']:
        raise RuntimeError('Unexpected upload ownership structure; preserved without repair.')


def migrate(query):
    if query('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE();') != ['11']:
        raise RuntimeError('Expected exactly 11 baseline tables; no migration attempted.')
    versions = query('SELECT version FROM development_schema_version ORDER BY version;')
    if versions not in (['1'], ['1', '2']):
        raise RuntimeError('V002 requires the recognized V001 development baseline.')
    column = query("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='file_upload' AND column_name='owner_user_id';")
    if column == ['0']:
        if versions != ['1']:
            raise RuntimeError('Schema version and column disagree; no repair attempted.')
        query(SQL.read_text())  # Single atomic MySQL 8 ALTER; no DROP, owner backfill or credential mutation.
    elif column != ['1']:
        raise RuntimeError('Unexpected ownership column count.')
    validate_structure(query)
    # DDL can commit before the version insert. A retry accepts only the exact expected structure.
    if versions == ['1']:
        query("INSERT INTO development_schema_version (version, description) VALUES (2, 'Upload ownership; legacy records quarantined');")
    return {'version': 2, 'legacy_owner_policy': 'NULL retained; no automatic claim',
            'legacy_rows': int(query('SELECT COUNT(*) FROM file_upload WHERE owner_user_id IS NULL;')[0])}
