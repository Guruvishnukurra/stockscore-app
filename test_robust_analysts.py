import pandas as pd
import numpy as np
import unittest
from unittest.mock import MagicMock, patch
from valuation import ValuationAnalyzer

class TestRobustAnalysts(unittest.TestCase):
    def setUp(self):
        self.data_cache = {
            "info": {
                "symbol": "RELIANCE.NS",
                "currentPrice": 2900.0,
                "sharesOutstanding": 6650000000,
                "forwardEps": 65.0
            },
            "financials": {}
        }
        self.industry_avg = {"averages": {}}

    @patch('yfinance.Ticker')
    def test_indian_style_estimates(self, mock_ticker):
        # Indian style: periods in index, avg in columns (lowercase)
        ee_df = pd.DataFrame({
            "avg": [59.3, 65.8]
        }, index=["0y", "+1y"])
        
        instance = mock_ticker.return_value
        instance.earnings_estimate = ee_df
        instance.revenue_estimate = pd.DataFrame() # Skip revenue
        
        analyzer = ValuationAnalyzer(self.data_cache, self.industry_avg)
        res = analyzer.analyze()
        
        dcf = res["dcf"]
        print(f"Indian Style - Data Source: {dcf['data_source']}")
        print(f"Growth Rate: {dcf['growth_rate_used']:.4f}")
        
        self.assertEqual(dcf["data_source"], "Analyst Estimates")
        # (65.8 - 59.3) / 59.3 = 0.1096
        self.assertAlmostEqual(dcf["growth_rate_used"], 0.109612, places=4)

    @patch('yfinance.Ticker')
    def test_us_style_estimates(self, mock_ticker):
        # US style: "Avg. Estimate" in index, periods in columns
        ee_df = pd.DataFrame({
            "Current Year": [1.95],
            "Next Year": [1.73]
        }, index=["Avg. Estimate"])
        
        instance = mock_ticker.return_value
        instance.earnings_estimate = ee_df
        instance.revenue_estimate = pd.DataFrame()
        
        self.data_cache["info"]["symbol"] = "AAPL"
        analyzer = ValuationAnalyzer(self.data_cache, self.industry_avg)
        res = analyzer.analyze()
        
        dcf = res["dcf"]
        print(f"US Style - Data Source: {dcf['data_source']}")
        
        self.assertEqual(dcf["data_source"], "Analyst Estimates")

if __name__ == "__main__":
    unittest.main()
