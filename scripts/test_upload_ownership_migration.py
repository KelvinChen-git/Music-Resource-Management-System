import unittest
from unittest.mock import Mock
from upload_ownership_migration import migrate, validate_structure

class MigrationTest(unittest.TestCase):
    def query(self, versions, column):
        def respond(sql):
            if 'COUNT(*) FROM information_schema.tables' in sql:return ['11']
            if 'SELECT version' in sql:return versions
            if 'SELECT COUNT(*) FROM information_schema.columns' in sql:return column
            if 'SELECT COLUMN_TYPE' in sql:return ['bigint\tYES']
            if 'SELECT COLUMN_NAME' in sql:return ['owner_user_id','file_md5','deleted']
            if 'SELECT COUNT(*) FROM file_upload' in sql:return ['7']
            return []
        return Mock(side_effect=respond)
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
        q=self.query(['1','2'],['1']);migrate(q)
        self.assertTrue(all(c.args[0].startswith('SELECT') for c in q.call_args_list))
    def test_unknown_version_or_structure_is_preserved(self):
        with self.assertRaises(RuntimeError):migrate(self.query(['1','3'],['0']))
        q=self.query(['1','2'],['0'])
        with self.assertRaises(RuntimeError):migrate(q)
        bad=Mock(return_value=['wrong'])
        with self.assertRaises(RuntimeError):validate_structure(bad)

if __name__=='__main__':unittest.main()
