import yfinance as yf # Updated: 2026-03-21 16:45
import pandas as pd
import numpy as np
import time
import json
import os
import tempfile
from datetime import datetime, timedelta

SECTOR_OVERRIDES = {
    "RELIANCE.NS": "Default",
    "ITC.NS": "Consumer Defensive",
    "M&M.NS": "Consumer Cyclical",
    "TATAMOTORS.NS": "Consumer Cyclical",
    "ADANIENT.NS": "Default"
}

class DataCollector:
    def __init__(self, ticker: str):
        self.ticker_str = ticker.upper()
        self.ticker = yf.Ticker(self.ticker_str)
        self.is_indian = self.ticker_str.endswith(".NS") or self.ticker_str.endswith(".BO")
        self.currency_symbol = "₹" if self.is_indian else "$"
        self._cache = {}

    def get_price_history(self, period="2y"):
        if "price_history" in self._cache:
            return self._cache["price_history"]
        
        try:
            df = self.ticker.history(period=period)
            df = df.reset_index()
            # Ensure Date column exists
            for col in df.columns:
                if col.lower() in ["date", "datetime"]:
                    df = df.rename(columns={col: "Date"})
                    break
            
            # If fewer than 60 rows, retry with 'max'
            if len(df) < 60 and period != "max":
                df = self.ticker.history(period="max")
                df = df.reset_index()
                for col in df.columns:
                    if col.lower() in ["date", "datetime"]:
                        df = df.rename(columns={col: "Date"})
                        break
            
            valid_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
            df = df[[col for col in valid_cols if col in df.columns]]
            
            self._cache["price_history"] = df
            return df
        except Exception:
            empty_df = pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])
            self._cache["price_history"] = empty_df
            return empty_df

    def get_financials(self):
        if "financials" in self._cache:
            return self._cache["financials"]
            
        financials = {"income_statement": pd.DataFrame(), "balance_sheet": pd.DataFrame(), "cash_flow": pd.DataFrame()}
        
        try:
            financials["income_statement"] = self.ticker.income_stmt
        except Exception:
            pass
            
        try:
            financials["balance_sheet"] = self.ticker.balance_sheet
        except Exception:
            pass
            
        try:
            financials["cash_flow"] = self.ticker.cash_flow
        except Exception:
            pass
            
        self._cache["financials"] = financials
        return financials

    def get_info(self):
        if "info" in self._cache:
            return self._cache["info"]
            
        info = {}
        for attempt in range(3):
            try:
                data = self.ticker.info
                if data and isinstance(data, dict) and len(data) >= 5:
                    info = data
                    break
            except Exception:
                pass
            time.sleep(1)
            
        # Ensure info is a dictionary before extraction
        if not isinstance(info, dict):
            info = {}

        # Safe extraction with defaults
        fields = [
            "trailingPE", "forwardPE", "priceToBook", "trailingEps", "forwardEps",
            "returnOnEquity", "returnOnAssets", "netMargins", "operatingMargins",
            "grossMargins", "revenueGrowth", "earningsGrowth", "debtToEquity",
            "currentRatio", "freeCashflow", "operatingCashflow", "totalRevenue",
            "netIncome", "sharesOutstanding", "floatShares", "heldPercentInsiders",
            "heldPercentInstitutions", "marketCap", "enterpriseValue", "beta",
            "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "regularMarketPrice",
            "currentPrice", "previousClose", "sector", "industry", "longName",
            "shortName", "trailingPegRatio", "priceToSalesTrailing12Months",
            "enterpriseToEbitda", "enterpriseToRevenue", "pegRatio"
        ]
        
        extracted = {}
        for field in fields:
            try:
                extracted[field] = info.get(field)
            except:
                extracted[field] = None

        # Current Price Resolution (Prioritize fast_info if available)
        curr_price = None
        try:
            curr_price = self.ticker.fast_info.last_price
        except:
            pass
            
        if curr_price is None or pd.isna(curr_price):
            curr_price = extracted.get("currentPrice") or extracted.get("regularMarketPrice") or extracted.get("previousClose")
            
        extracted["currentPrice_resolved"] = curr_price
        extracted["currentPrice"] = curr_price
        extracted["symbol"] = self.ticker_str
        
        # marketCap Fallback
        mcap = extracted.get("marketCap")
        if mcap is None or pd.isna(mcap):
            try:
                mcap = self.ticker.fast_info.market_cap
            except:
                pass
        extracted["marketCap"] = mcap
        
        # sharesOutstanding Fallback
        shares = extracted.get("sharesOutstanding")
        if shares is None or pd.isna(shares):
            try:
                shares = self.ticker.fast_info.shares_outstanding
            except:
                pass
        extracted["sharesOutstanding"] = shares

        # SHARES SCALE CHECK
        if shares and curr_price and mcap:
            expected = mcap / curr_price
            ratio = expected / shares
            if ratio > 500000:
                shares = shares * 1000000
            elif ratio > 500:
                shares = shares * 1000
            elif ratio < 0.002:
                shares = shares / 1000
            extracted["sharesOutstanding"] = shares
            
        extracted["Company Name"] = extracted.get("longName") or extracted.get("shortName") or self.ticker_str
        extracted["sector"] = extracted.get("sector") or extracted.get("industry") or "Default"
        extracted["currency_symbol"] = self.currency_symbol
        
        self._cache["info"] = extracted
        return extracted

    def get_industry_averages(self):
        info = self.get_info()
        symbol = info.get("symbol", "")
        sector = SECTOR_OVERRIDES.get(symbol) or info.get("sector", "Unknown")
        
        cache_dir = os.path.join(tempfile.gettempdir(), "stockscore_cache")
        os.makedirs(cache_dir, exist_ok=True)
        safe_sector = "".join(x for x in sector if x.isalnum())
        cache_file = os.path.join(cache_dir, f"{safe_sector}_avgs.json")
        
        if os.path.exists(cache_file):
            try:
                file_time = os.path.getmtime(cache_file)
                if time.time() - file_time < 86400: # 24 hours
                    with open(cache_file, "r") as f:
                        return json.load(f)
            except Exception:
                pass
                
        fallbacks = {
            "Financial Services": {"pe": 18, "pb": 2.2, "roe": 14, "net_margin": 18, "debt_equity": 8.0, "rev_growth": 10, "operating_margin": 20, "roa": 1.2, "current_ratio": 1.0, "earn_growth": 10},
            "Technology": {"pe": 28, "pb": 6.5, "roe": 20, "net_margin": 15, "debt_equity": 0.3, "rev_growth": 12, "operating_margin": 22, "roa": 8.0, "current_ratio": 2.5, "earn_growth": 14},
            "Energy": {"pe": 12, "pb": 1.8, "roe": 12, "net_margin": 8, "debt_equity": 0.6, "rev_growth": 5, "operating_margin": 12, "roa": 5.0, "current_ratio": 1.2, "earn_growth": 6},
            "Consumer Defensive": {"pe": 45, "pb": 8.0, "roe": 35, "net_margin": 12, "debt_equity": 0.4, "rev_growth": 8, "operating_margin": 18, "roa": 9.0, "current_ratio": 1.5, "earn_growth": 9},
            "Consumer Cyclical": {"pe": 20, "pb": 3.5, "roe": 15, "net_margin": 8, "debt_equity": 0.5, "rev_growth": 10, "operating_margin": 12, "roa": 6.0, "current_ratio": 1.3, "earn_growth": 11},
            "Healthcare": {"pe": 30, "pb": 4.5, "roe": 16, "net_margin": 14, "debt_equity": 0.3, "rev_growth": 12, "operating_margin": 20, "roa": 7.0, "current_ratio": 2.0, "earn_growth": 13},
            "Basic Materials": {"pe": 10, "pb": 1.5, "roe": 12, "net_margin": 7, "debt_equity": 0.7, "rev_growth": 6, "operating_margin": 10, "roa": 5.0, "current_ratio": 1.2, "earn_growth": 6},
            "Default": {"pe": 20, "pb": 2.5, "roe": 12, "net_margin": 8, "debt_equity": 0.5, "rev_growth": 8, "operating_margin": 14, "roa": 6.0, "current_ratio": 1.5, "earn_growth": 8}
        }
        
        peer_map = {
            "Financial Services": ["HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS", "SBIN.NS"],
            "Energy": ["RELIANCE.NS", "ONGC.NS", "BPCL.NS", "IOC.NS", "GAIL.NS"],
            "Technology": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"],
            "Consumer Defensive": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "DABUR.NS", "MARICO.NS"],
            "Consumer Cyclical": ["MARUTI.NS", "TATAMOTORS.NS", "HEROMOTOCO.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS"],
            "Healthcare": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "LUPIN.NS"],
            "Basic Materials": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "SAIL.NS", "VEDL.NS"],
            "US Technology": ["AAPL", "MSFT", "GOOGL", "META", "NVDA"],
            "US Financials": ["JPM", "BAC", "GS", "MS", "WFC"]
        }
        
        # Select base fallbacks
        base_fallback = fallbacks.get(sector, fallbacks["Default"])
        
        peers = peer_map.get(sector, [])
        if not peers and not self.is_indian:
            if "Technology" in sector:
                peers = peer_map["US Technology"]
            elif "Financial" in sector:
                peers = peer_map["US Financials"]
                
        metrics = {k: [] for k in base_fallback.keys()}
        
        if peers:
            start_time = time.time()
            for p in peers:
                if time.time() - start_time > 15: # 15s budget
                    break
                try:
                    p_info = yf.Ticker(p).info
                    
                    if p_info.get("trailingPE") and 0 <= p_info["trailingPE"] <= 100:
                        metrics["pe"].append(p_info["trailingPE"])
                    if p_info.get("priceToBook") and p_info["priceToBook"] > 0:
                        metrics["pb"].append(p_info["priceToBook"])
                    if p_info.get("returnOnEquity"):
                        metrics["roe"].append(p_info["returnOnEquity"] * 100)
                    if p_info.get("netMargins"):
                        metrics["net_margin"].append(p_info["netMargins"] * 100)
                    if p_info.get("operatingMargins"):
                        metrics["operating_margin"].append(p_info["operatingMargins"] * 100)
                    if p_info.get("returnOnAssets"):
                        metrics["roa"].append(p_info["returnOnAssets"] * 100)
                    if p_info.get("debtToEquity"):
                        d_e = p_info["debtToEquity"]
                        if d_e > 20: d_e = d_e / 100
                        metrics["debt_equity"].append(d_e)
                    if p_info.get("currentRatio"):
                        metrics["current_ratio"].append(p_info["currentRatio"])
                    if p_info.get("revenueGrowth"):
                        metrics["rev_growth"].append(p_info["revenueGrowth"] * 100)
                    if p_info.get("earningsGrowth"):
                        metrics["earn_growth"].append(p_info["earningsGrowth"] * 100)
                except Exception:
                    continue
                    
        result_avgs = {}
        for k, v in metrics.items():
            if len(v) >= 3:
                result_avgs[k] = float(np.median(v))
            else:
                result_avgs[k] = base_fallback[k]
                
        result = {"averages": result_avgs, "source": "computed" if any(len(v) >= 3 for v in metrics.values()) else "fallback"}
        
        try:
            with open(cache_file, "w") as f:
                json.dump(result, f)
        except Exception:
            pass
            
        return result
