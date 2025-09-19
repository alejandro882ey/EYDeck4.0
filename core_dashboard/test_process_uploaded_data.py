import unittest
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from process_uploaded_data import build_merged_df


class TestProcessUploadedData(unittest.TestCase):
    def test_perdida_column_used(self):
        # Create a minimal engagement dataframe with a Perdida column
        eng = pd.DataFrame({
            'EngagementID': ['E1', 'E2'],
            'EngagementPartner': ['P1', 'P2'],
            'EngagementManager': ['M1', 'M2'],
            'Perdida Dif. Camb.': [100.0, 200.0],
            'FYTD_ANSRAmt': [1000.0, 2000.0]
        })
        rev = pd.DataFrame()  # not used in this test
        week = pd.to_datetime('2025-08-29').date()

        merged = build_merged_df(eng, rev, week)

        # diferencial_final should be negative of the Perdida column (sign convention)
        self.assertIn('diferencial_final', merged.columns)
        self.assertEqual(merged.loc[0, 'diferencial_final'], -100.0)
        self.assertEqual(merged.loc[1, 'diferencial_final'], -200.0)

    def test_perdida_missing_for_2025_07_11(self):
        # Engagement lacks Perdida column
        eng = pd.DataFrame({
            'EngagementID': ['E1'],
            'EngagementPartner': ['P1'],
            'EngagementManager': ['M1'],
            'FYTD_ANSRAmt': [1500.0]
        })
        rev = pd.DataFrame()
        week = pd.to_datetime('2025-07-11').date()

        merged = build_merged_df(eng, rev, week)

        # For the exceptional date the script must set diferencial to 0
        self.assertIn('diferencial_final', merged.columns)
        self.assertEqual(merged.loc[0, 'diferencial_final'], -0.0)


if __name__ == '__main__':
    unittest.main()
