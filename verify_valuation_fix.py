from valuation import ValuationAnalyzer
import pandas as pd
import numpy as np

def test_valuation_fix():
    # Mock data for Reliance based on our check_reliance_data.py output
    financials = {
        "cash_flow": pd.DataFrame({
            "2025-03-31": [3.8736e11],
            "2024-03-31": [5.9050e10],
            "2023-03-31": [-2.5956e11]
        }, index=["Free Cash Flow"])
    }
    
    info = {
        "currentPrice": 1414.40,
        "marketCap": 19140328816640,
        "sharesOutstanding": 13532472634,
        "revenueGrowth": 0.12,
        "forwardEps": 110.0,
        "sector": "Energy"
    }
    
    analyzer = ValuationAnalyzer({"info": info, "financials": financials}, {"averages": {"pe": 20}})
    res = analyzer.analyze()
    
    print(f"Score: {res['score']}/{res['max']}")
    print(f"Intrinsic Value: {res['dcf']['intrinsic_value_per_share']}")
    print(f"Upside: {res['dcf']['upside_pct']}%")
    print(f"Flags: {res['flags']}")

if __name__ == "__main__":
    test_valuation_fix()
