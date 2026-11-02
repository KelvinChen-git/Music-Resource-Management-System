"""Hand-calculated lexical, weighted-geometry and saved-model attribution controls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import supervision_diagnostic as m
from diagnose_supervision import validate, run
import holdout_contract as h


class SupervisionDiagnosticTests(unittest.TestCase):
    def rows(self):
        return [{'id': str(i//2), 'split': 'train' if i < 4 else 'validation'} for i in range(6)]

    def test_normalization_preserves_negation_and_numbers(self):
        self.assertEqual(m.words("NO vocals; isn't 120.5 BPM."), ['no','vocals',"isn't",'120.5','bpm'])
        for value in ['', '...', '音乐']:
            with self.assertRaises(ValueError): m.words(value)

    def test_phrase_dictionary_uses_distinct_train_recordings_only(self):
        texts=['a warm melody with piano.']*2+['a warm melody with guitar.']*2+['the hidden secret phrase exists.']*2
        public, private, _ = m.text_audit(texts,self.rows(),prevalence=1.)
        self.assertEqual(public['common_5gram_types'],0)
        self.assertEqual(public['exact_normalized_duplicates']['cross_recording_pairs'],0)
        self.assertEqual(private['coverage_by_interval'],[0]*6)

    def test_cross_recording_duplicates_and_full_common_phrase_coverage(self):
        texts=['A bright piano melody plays.']*6
        r,private,_=m.text_audit(texts,self.rows())
        self.assertEqual(r['exact_normalized_duplicates']['all_interval_pairs'],15)
        self.assertEqual(r['exact_normalized_duplicates']['cross_recording_pairs'],12)
        self.assertEqual(r['near_duplicate_5gram_jaccard']['cross_recording_affected_recordings'],3)
        self.assertEqual(r['repeated_sentence_types_across_recordings'],1)
        self.assertEqual(private['coverage_by_interval'],[1]*6)

    def test_recording_weighted_geometry_hand_calculated(self):
        x=np.array([[1.,0.]]*3+[[0.,1.]]*2);ids=['a']*3+['b']*2;r=m.geometry(x,ids)
        self.assertAlmostEqual(r['mean_vector_norm'],2**-.5)
        self.assertAlmostEqual(r['centered_variance_trace'],.5)
        self.assertAlmostEqual(r['centered_participation_ratio'],1)
        self.assertEqual(r['mean_within_recording_distinct_interval_cosine'],1)
        self.assertEqual(r['mean_between_distinct_recordings_cosine'],0)

    def test_constant_embeddings_have_zero_centered_rank(self):
        r=m.geometry(np.array([[1.,0.]]*4),['a','a','b','b'])
        self.assertEqual(r['centered_participation_ratio'],0)
        self.assertEqual(r['centered_variance_trace'],0)

    def test_saved_ridge_rhs_and_common_direction_without_solver(self):
        x=np.eye(2)[[0,0,1,1]];t=np.tile([1.,0.],(4,1));w=np.array([[1.,0.],[1/3,2/3]])
        with patch('numpy.linalg.solve',side_effect=AssertionError('No new solve allowed')):
            r=m.ridge_attribution(x,t,['a','a','b','b'],w)
        self.assertLess(r['normal_equation_maxabs'],1e-15)
        self.assertAlmostEqual(r['saved_update_energy_in_common_residual_target_direction'],1)
        self.assertAlmostEqual(r['rhs_to_mean_cosine'],2**-.5)
        self.assertAlmostEqual(r['mean_outer_rhs_norm'],.5)

    def test_score_contrasts_do_not_treat_same_song_as_other_recording(self):
        x=np.eye(2)[[0,0,0,1,1]];ids=['a','a','a','b','b'];r=m.score_contrasts(x,x,ids,np.eye(2))
        self.assertEqual(r['known_pair_cosine'],1)
        self.assertEqual(r['other_recording_mean_cosine'],0)
        self.assertEqual(r['known_minus_other_same_recording_interval_mean'],0)
        self.assertEqual(r['known_minus_best_other_recording'],1)

    def test_language_OOV_is_word_occurrence_and_recording_weighted(self):
        r=m.language_coverage(['piano piano unknown','piano unknown','guitar'],['a','a','b'],{'piano'},[5,4,3])
        self.assertAlmostEqual(r['word_occurrence_OOV_from_train']['mean'],(1/3+1/2)/4+.5)

    def test_unbalanced_recording_weight_cannot_be_replaced_by_interval_mean(self):
        x=np.eye(2)[[0,0,0,1,1]];ids=['a','a','a','b','b'];y=np.tile([1.,0.],(5,1))
        r=m.score_contrasts(x,y,ids,np.eye(2));self.assertAlmostEqual(r['known_pair_cosine'],.5)
        self.assertAlmostEqual(m.summary([1,1,1,0,0])['mean'],.6)

    def test_rank_changes_have_stable_ties_and_distinguish_thresholds(self):
        r=m.ranking_changes(np.eye(2),np.eye(2),['a','b'],['a','b'],np.eye(2),np.array([[0.,1.],[1.,0.]]))
        self.assertEqual(r['paired_rank_changed_queries'],2);self.assertEqual(r['paired_rank_threshold_R1_changed_queries'],2)
        self.assertEqual(r['paired_rank_threshold_R5_changed_queries'],0);self.assertEqual(r['top5_set_changed_queries'],0)
        self.assertEqual(r['full_order_changed_queries'],2)

    def test_frozen_config_forbids_training_label_changes_or_threshold_search(self):
        cfg=json.loads((h.ROOT/'docs/evaluation/MUS-059-diagnostic-config.json').read_text());validate(cfg)
        for key,value in [('fits',1),('label_edits',1),('near_duplicate_jaccard',.5),('automatic_selection_or_deployment',True)]:
            c=copy.deepcopy(cfg);c[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(c)

    def test_existing_claim_blocks_new_output_before_creation(self):
        c={'task_directory':'.local/a/mus059'}
        with patch('diagnose_supervision.h.assets.document',return_value=c),patch('diagnose_supervision.validate'),patch('diagnose_supervision.subprocess.check_output',return_value=b''),patch('pathlib.Path.exists',return_value=True),patch('diagnose_supervision.h.private_output')as output:
            with self.assertRaisesRegex(ValueError,'already attempted'):run(config='config',config_sha256='a'*64,output=h.ROOT/'.local/a/mus059/other')
            output.assert_not_called()


if __name__=='__main__':unittest.main()
