import pandas as pd
import numpy as np
import unittest
from unittest.mock import MagicMock, patch
from valuation import ValuationAnalyzer

class TestAnalystDCF(unittest.TestCase):
    def setUp(self):
        self.data_cache = {
            "info": {
                "symbol": "AAPL",
                "currentPrice": 150.0,
                "sharesOutstanding": 1000000,
                "forwardEps": 6.0,
                "revenueGrowth": 0.1
            },
            "financials": {
                "cash_flow": pd.DataFrame({
                    "2023-12-31": [100000000],
                    "2022-12-31": [90000000]
                }, index=["Free Cash Flow"])
            }
        }
        self.industry_avg = {"averages": {"pe": 25}}

    @patch('yfinance.Ticker')
    def test_analyze_with_analyst_estimates(self, mock_ticker):
        # Mock earnings estimate
        ee_df = pd.DataFrame({
            "Year 1": [7.0],
            "Year 2": [8.0]
        }, index=["Avg"])
        
        # Mock revenue estimate
        re_df = pd.DataFrame({
            "Year 1": [100.0],
            "Year 2": [110.0]
        }, index=["Avg"])
        
        instance = mock_ticker.return_value
        instance.earnings_estimate = ee_df
        instance.revenue_estimate = re_df
        
        analyzer = ValuationAnalyzer(self.data_cache, self.industry_avg)
        res = analyzer.analyze()
        
        dcf = res["dcf"]
        print(f"Data Source: {dcf['data_source']}")
        print(f"Analyst Growth Used: {dcf['analyst_growth_used']}")
        print(f"Growth Rate Used: {dcf['growth_rate_used']:.4f}")
        
        self.assertEqual(dcf["data_source"], "Analyst Estimates")
        self.assertTrue(dcf["analyst_growth_used"])
        # (8-7)/7 = 0.1428...
        self.assertAlmostEqual(dcf["growth_rate_used"], 0.142857, places=4)
        self.assertIn("intrinsic_value_per_share", dcf)
        self.assertGreater(dcf["intrinsic_value_per_share"], 0)

    @patch('yfinance.Ticker')
    def test_analyze_fallback_to_historical(self, mock_ticker):
        # Mock empty estimates
        instance = mock_ticker.return_value
        instance.earnings_estimate = pd.DataFrame()
        instance.revenue_estimate = pd.DataFrame()
        
        analyzer = ValuationAnalyzer(self.data_cache, self.industry_avg)
        res = analyzer.analyze()
        
        dcf = res["dcf"]
        print(f"Data Source: {dcf['data_source']}")
        print(f"Analyst Growth Used: {dcf['analyst_growth_used']}")
        
        self.assertEqual(dcf["data_source"], "Historical FCF")
        self.assertFalse(dcf["analyst_growth_used"])
        # Falls back to revenueGrowth 0.1
        self.assertEqual(dcf["growth_rate_used"], 0.1)

if __name__ == "__main__":
    unittest.main()
