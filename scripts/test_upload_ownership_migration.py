import unittest
from unittest.mock import Mock
from upload_ownership_migration import migrate, validate_structure, TABLES, UPLOAD_COLUMNS

class MigrationTest(unittest.TestCase):
    def query(self, versions, column, override=None):
        def respond(sql):
            if override:
                answer=override(sql)
                if answer is not None:return answer
            if 'SELECT TABLE_NAME ' in sql:return sorted(TABLES)
            if 'SELECT COLUMN_NAME, COLUMN_TYPE' in sql:
                return ['\t'.join([name,kind,nullable]) for name,(kind,nullable) in UPLOAD_COLUMNS.items()]
            if 'SELECT COLUMN_NAME, NON_UNIQUE' in sql:
                if "index_name='PRIMARY'" in sql:return ['id\t0']
                return [name+'\t1\tBTREE' for name in ['owner_user_id','file_md5','deleted']]
            if 'SELECT EXTRA ' in sql:return ['auto_increment']
            if 'SELECT version' in sql:return versions
            if 'SELECT COUNT(*) FROM information_schema.columns' in sql:return column
            if 'SELECT COLUMN_TYPE' in sql:return ['bigint\tYES\t<NULL>\t<EMPTY>']
            if 'SELECT COUNT(*) FROM file_upload' in sql:return ['7']
            return []
        return Mock(side_effect=respond)
    def assert_no_writes(self,q):
        self.assertTrue(all(c.args[0].startswith('SELECT') for c in q.call_args_list))
    def test_existing_rows_are_quarantined_without_backfill(self):
        q=self.query(['1'],['0']);result=migrate(q)
        self.assertEqual(7,result['legacy_rows'])
        sql='\n'.join(c.args[0] for c in q.call_args_list)
        self.assertIn('ALTER TABLE file_upload',sql)
        self.assertNotIn('UPDATE file_upload',sql)
        self.assertNotIn('DROP ',sql)
    def test_retry_after_ddl_before_version_insert_does_not_alter_again(self):
        q=self.query(['1'],['1']);migrate(q)
        self.assertFalse(any('ALTER TABLE' in c.args[0] for c in q.call_args_list))
        self.assertTrue(any('INSERT INTO development_schema_version' in c.args[0] for c in q.call_args_list))
    def test_repeat_completed_migration_is_read_only(self):
        q=self.query(['1','2'],['1']);migrate(q);self.assert_no_writes(q)
    def test_unknown_version_or_structure_is_preserved(self):
        for versions,column in [(['1','3'],['0']),(['1','2'],['0'])]:
            q=self.query(versions,column)
            with self.assertRaises(RuntimeError):migrate(q)
            self.assert_no_writes(q)
    def test_same_count_substituted_table_is_refused_before_ddl(self):
        q=self.query(['1'],['0'],lambda sql: sorted(TABLES-{'file_chunk'}|{'file_chunk_unexpected'}) if 'SELECT TABLE_NAME ' in sql else None)
        with self.assertRaises(RuntimeError):migrate(q)
        self.assert_no_writes(q)
    def test_missing_table_is_refused(self):
        q=self.query(['1'],['0'],lambda sql:sorted(TABLES-{'file_chunk'}) if 'SELECT TABLE_NAME ' in sql else None)
        with self.assertRaises(RuntimeError):migrate(q)
        self.assert_no_writes(q)
    def test_missing_or_wrong_required_column_is_refused(self):
        for columns in [{k:v for k,v in UPLOAD_COLUMNS.items() if k!='file_md5'}, {**UPLOAD_COLUMNS,'file_size':('int','NO')}]:
            q=self.query(['1'],['0'],lambda sql:['\t'.join([n,*v]) for n,v in columns.items()] if 'SELECT COLUMN_NAME, COLUMN_TYPE' in sql else None)
            with self.assertRaises(RuntimeError):migrate(q)
            self.assert_no_writes(q)
    def test_missing_primary_or_identity_is_refused(self):
        for marker in ["index_name='PRIMARY'",'SELECT EXTRA ']:
            q=self.query(['1'],['0'],lambda sql:[] if marker in sql else None)
            with self.assertRaises(RuntimeError):migrate(q)
            self.assert_no_writes(q)
    def test_owner_default_generated_or_nullable_mismatch_is_refused(self):
        for shape in ['bigint\tYES\t1\t<EMPTY>','bigint\tNO\t<NULL>\t<EMPTY>','bigint\tYES\t<NULL>\tSTORED GENERATED']:
            q=self.query(['1'],['1'],lambda sql:[shape] if 'SELECT COLUMN_TYPE' in sql else None)
            with self.assertRaises(RuntimeError):migrate(q)
            self.assert_no_writes(q)
    def test_unique_or_reordered_owner_index_is_refused(self):
        for rows in [[n+'\t0\tBTREE' for n in ['owner_user_id','file_md5','deleted']], [n+'\t1\tBTREE' for n in ['file_md5','owner_user_id','deleted']]]:
            q=self.query(['1'],['1'],lambda sql:rows if "index_name='idx_upload_owner_md5'" in sql else None)
            with self.assertRaises(RuntimeError):migrate(q)
            self.assert_no_writes(q)

if __name__=='__main__':unittest.main()
