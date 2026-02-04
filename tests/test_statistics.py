import unittest
from src.core.statistics import StatisticsCalculator, TranscriptionStatistics

class TestStatisticsCalculator(unittest.TestCase):
    def test_calculate_basic(self):
        text = "Esta es una prueba de transcripción. Tiene varias palabras."
        duration = 60.0 # 1 minuto
        
        stats = StatisticsCalculator.calculate(text, duration)
        
        self.assertEqual(stats.word_count, 9)
        self.assertEqual(stats.words_per_minute, 9.0)
        self.assertEqual(stats.sentence_count, 2)
        self.assertEqual(stats.duration_seconds, 60.0)

    def test_calculate_empty(self):
        stats = StatisticsCalculator.calculate("", 10.0)
        self.assertEqual(stats.word_count, 0)
        self.assertEqual(stats.words_per_minute, 0.0)
        self.assertEqual(stats.sentence_count, 0)

    def test_format_duration(self):
        self.assertEqual(StatisticsCalculator.format_duration(65), "01:05")
        self.assertEqual(StatisticsCalculator.format_duration(3665), "01:01:05")
        self.assertEqual(StatisticsCalculator.format_duration(0), "00:00")

    def test_format_duration_verbose(self):
        self.assertEqual(StatisticsCalculator.format_duration_verbose(65), "1 minuto, 5 segundos")
        self.assertEqual(StatisticsCalculator.format_duration_verbose(3665), "1 hora, 1 minuto, 5 segundos")

if __name__ == "__main__":
    unittest.main()
