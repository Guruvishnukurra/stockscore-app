import yfinance as yf
import pandas as pd

def check_reliance():
    ticker = yf.Ticker("RELIANCE.NS")
    print(f"Ticker: {ticker.ticker}")
    print(f"Info FreeCashFlow: {ticker.info.get('freeCashflow')}")
    print(f"Info OperatingCashflow: {ticker.info.get('operatingCashflow')}")
    print(f"Info NetIncome: {ticker.info.get('netIncome')}")
    
    cf = ticker.cashflow
    print("\nCash Flow Index:")
    print(cf.index.tolist())
    
    if "Free Cash Flow" in cf.index:
        print("\nFree Cash Flow values:")
        print(cf.loc["Free Cash Flow"])
    
    if "Operating Cash Flow" in cf.index:
        print("\nOperating Cash Flow values:")
        print(cf.loc["Operating Cash Flow"])
        
    if "Capital Expenditure" in cf.index:
        print("\nCapital Expenditures values:")
        print(cf.loc["Capital Expenditure"])

if __name__ == "__main__":
    check_reliance()
