import unittest
import numpy as np
from preprocess import prepare_window, WINDOW_SAMPLES


class PreprocessingTest(unittest.TestCase):
    def test_short_audio_is_zero_padded_without_repetition(self):
        result, info = prepare_window(np.ones(48000, dtype=np.float32), 48000)
        self.assertEqual(result.shape, (WINDOW_SAMPLES,))
        self.assertTrue(np.all(result[:48000] == 1))
        self.assertTrue(np.all(result[48000:] == 0))
        self.assertEqual(info['padded_samples'], 432000)

    def test_exact_window_is_unchanged(self):
        original = np.linspace(-0.5, 0.5, WINDOW_SAMPLES, dtype=np.float32)
        result, info = prepare_window(original, 48000)
        np.testing.assert_array_equal(result, original)
        self.assertEqual(info['padded_samples'], 0)

    def test_stereo_downmix_is_mean(self):
        result, _ = prepare_window(np.array([[0.2, 0.6]], dtype=np.float32), 48000)
        self.assertAlmostEqual(float(result[0]), 0.4)

    def test_resample_tracks_real_length(self):
        result, info = prepare_window(np.zeros(44100, dtype=np.float32), 44100)
        self.assertEqual(info['real_samples'], 48000)
        self.assertEqual(info['padded_samples'], 432000)
        self.assertEqual(result.dtype, np.float32)

    def test_ten_second_resample_does_not_overflow_window(self):
        result, info = prepare_window(np.zeros(441000, dtype=np.float32), 44100)
        self.assertEqual(info['real_samples'], WINDOW_SAMPLES)
        self.assertEqual(info['padded_samples'], 0)

    def test_fractional_resample_length_uses_integer_ceiling(self):
        _, info = prepare_window(np.zeros(2, dtype=np.float32), 44100)
        self.assertEqual(info['real_samples'], 3)

    def test_long_audio_requires_explicit_slicing(self):
        with self.assertRaises(ValueError):
            prepare_window(np.zeros(480001), 48000)

    def test_empty_nonfinite_and_bad_shape_are_rejected(self):
        for audio in [[], [float('nan')], [float('inf')], np.zeros((1, 1, 1))]:
            with self.subTest(audio=str(audio)), self.assertRaises(ValueError):
                prepare_window(audio, 48000)

    def test_invalid_rate_is_rejected(self):
        for rate in [0, -1, 44100.5]:
            with self.subTest(rate=rate), self.assertRaises(ValueError):
                prepare_window([0.0], rate)


if __name__ == '__main__':
    unittest.main()
