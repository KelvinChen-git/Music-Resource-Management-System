"""Synthetic positive-only regression; no audio, models or human judgments."""
import unittest
import numpy as np
import tag_adapter as a
import mtg_plan as p
import test_mtg_dataset as metadata_fixture
import mtg_dataset as m


class AdapterTest(unittest.TestCase):
    def test_identity_target_stays_identity(self):
        x=np.eye(3);w,r=a.fit(x,x,100)
        np.testing.assert_array_equal(w,np.eye(3));self.assertEqual(r['parameter_delta_frobenius_norm'],0)

    def test_dual_solution_matches_primal_and_minimizes_objective(self):
        rng=np.random.default_rng(42);x=a.unit(rng.normal(size=(7,5)));y=a.unit(rng.normal(size=(7,5)))
        w,r=a.fit(x,y,100)
        primal=np.linalg.solve(x.T@x+100*np.eye(5),x.T@y+100*np.eye(5))
        np.testing.assert_allclose(w,primal,atol=1e-12);self.assertLess(r['objective_after'],r['objective_before']);self.assertGreater(r['parameter_delta_frobenius_norm'],0)

    def test_target_centroid_uses_only_known_positive_tags(self):
        prot=np.eye(3);got=a.targets(prot,[[0,1],[2]])
        np.testing.assert_allclose(got[0],[1/np.sqrt(2),1/np.sqrt(2),0]);np.testing.assert_array_equal(got[1],[0,0,1])

    def test_invalid_or_empty_positive_tags_rejected(self):
        for labels in ([[]],[[0,0]],[[True]],[[4]]):
            with self.assertRaises(ValueError):a.targets(np.eye(3),labels)

    def test_invalid_fit_regularization_or_data_rejected(self):
        for lam in (0,-1,float('nan'),True):
            with self.assertRaises(ValueError):a.fit(np.eye(3),np.eye(3),lam)
        with self.assertRaises(ValueError):a.fit(np.eye(3),np.ones((2,3)),100)
        with self.assertRaises(ValueError):a.fit(np.eye(3)*float('nan'),np.eye(3),100)

    def test_recall_uses_known_count_and_stable_vocabulary_ties(self):
        r=a.observed_recall([[1,0,0]],np.eye(3),[[0,1]],k=1)
        self.assertEqual(r['macro_observed_tag_recall_at5'],.5)
        self.assertIn('not_precision',r['scope'])


class PlanTest(unittest.TestCase):
    def fixture(self):
        pools={}
        for part,prefix in [('train','a'),('validation','b'),('test','c')]:
            pools[part]=[{'source_track_id':prefix+str(i),'official_split':part,'artist_id':prefix+str(i),'artist_name':prefix+'Creator'+str(i),'title':prefix+'Work'+str(i),'audio_sha256':prefix+str(i),'tags':['genre---ambient']}for i in range(8)]
        cfg={'plan_seed':'test-fixed','per_artist_component_cap':1,'planned_counts':{k: 3 for k in pools}}
        return pools,cfg

    def test_deterministic_plan_and_no_cross_partition_groups(self):
        pools,cfg=self.fixture();first=p.group_plan(pools,cfg);self.assertEqual(first,p.group_plan(pools,cfg))
        self.assertEqual(first['summary']['counts'],{'train':3,'validation':3,'test':3})
        sets=[{x['creator_component']for x in rows}for rows in first['selected'].values()]
        self.assertTrue(all(not a&b for i,a in enumerate(sets)for b in sets[i+1:]))

    def test_shared_credit_component_quarantined_across_official_splits(self):
        pools,cfg=self.fixture();pools['train'][0]['artist_name']='Alice & Bob';pools['validation'][0]['artist_name']='Bob'
        r=p.group_plan(pools,cfg);self.assertEqual(r['summary']['quarantine_reasons_nonexclusive']['train:creator_component_across_official_splits'],1)

    def test_shared_work_or_audio_SHA_quarantined(self):
        for key in ('title','audio_sha256'):
            pools,cfg=self.fixture();pools['validation'][0][key]=pools['train'][0][key]
            r=p.group_plan(pools,cfg);self.assertEqual(r['summary']['eligible_after_cross_split_quarantine']['train'],7)

    def test_insufficient_pool_does_not_relax_group_cap(self):
        pools,cfg=self.fixture();cfg['planned_counts']['train']=100
        with self.assertRaises(ValueError):p.group_plan(pools,cfg)

    def test_metadata_optional_pool_preserves_default_and_partition_names(self):
        raw,policy=metadata_fixture.MetadataTest().fixture();default=m.build(raw,policy);pool=m.build(raw,policy,include_pool=True)
        self.assertEqual(default['summary'],pool['summary']);self.assertEqual(len(pool['eligible_pool']),24)
        val=m.build(raw,policy,partition='validation',include_pool=True)
        self.assertEqual(len(val['eligible_pool']),2);self.assertTrue(all(x['official_split']=='validation'for x in val['eligible_pool']))


if __name__=='__main__':unittest.main()
