import traceback
import logging

from data_collector import DataCollector
from fundamental import FundamentalAnalyzer
from technical import TechnicalAnalyzer
from valuation import ValuationAnalyzer
from ownership import OwnershipAnalyzer
from scorer import ScoreEngine

logging.basicConfig(level=logging.INFO)

def analyze_stock(ticker, progress_cb=None):
    result = {
        "ticker": ticker,
        "error": False,
        "error_msg": "",
        "info": {},
        "industry_avg": {},
        "fundamental": {"score": 0, "max": 35, "ratios": {}, "flags": [], "limited_data": True},
        "technical": {"score": 0, "max": 20, "indicators": {}, "flags": [], "limited_data": True, "price_df_with_indicators": None},
        "valuation": {"score": 0, "max": 25, "dcf": {}, "pe_valuation": {}, "flags": [], "limited_data": True},
        "ownership": {"score": 0, "max": 10, "metrics": {}, "flags": [], "limited_data": True},
        "score": {"final_score": 0, "rating": "Error", "raw_score": 0, "max_raw": 90, "rating_emoji": "⚠️", "reasoning": [], "module_scores": {}}
    }
    
    try:
        if progress_cb: progress_cb("Fetching market data...")
        collector = DataCollector(ticker)
        
        try:
            info = collector.get_info()
            result["info"] = info
        except Exception as e:
            result["error"] = True
            result["error_msg"] = f"Failed to fetch info: {e}\n{traceback.format_exc()}"
            return result
            
        try:
            collector.get_financials()
        except: pass
        
        try:
            price_df = collector.get_price_history()
        except Exception as e:
            price_df = None
            
        try:
            industry_avg = collector.get_industry_averages()
            result["industry_avg"] = industry_avg
        except Exception as e:
            industry_avg = {}
            
        # Analysis modules
        if progress_cb: progress_cb("Analyzing fundamentals...")
        try:
            fund_analyzer = FundamentalAnalyzer(collector._cache, industry_avg)
            result["fundamental"] = fund_analyzer.analyze()
        except Exception as e:
            logging.error(f"Fundamental Analysis Error:\n{traceback.format_exc()}")
            result["fundamental"].update({"flags": [f"[-] Fundamental Error: {e}"]})
            
        if progress_cb: progress_cb("Computing technical indicators...")
        try:
            tech_analyzer = TechnicalAnalyzer(price_df)
            result["technical"] = tech_analyzer.analyze()
        except Exception as e:
            logging.error(f"Technical Analysis Error:\n{traceback.format_exc()}")
            result["technical"].update({"flags": [f"[-] Technical Error: {e}"]})
            
        if progress_cb: progress_cb("Running DCF valuation...")
        try:
            val_analyzer = ValuationAnalyzer(collector._cache, industry_avg)
            result["valuation"] = val_analyzer.analyze()
        except Exception as e:
            logging.error(f"Valuation Analysis Error:\n{traceback.format_exc()}")
            result["valuation"].update({"flags": [f"[-] Valuation Error: {e}"]})
            
        if progress_cb: progress_cb("Checking ownership...")
        try:
            bs = collector._cache.get("financials", {}).get("balance_sheet")
            own_analyzer = OwnershipAnalyzer(info, bs)
            result["ownership"] = own_analyzer.analyze()
        except Exception as e:
            logging.error(f"Ownership Analysis Error:\n{traceback.format_exc()}")
            result["ownership"].update({"flags": [f"[-] Ownership Error: {e}"]})
            
        if progress_cb: progress_cb("Calculating final score...")
        try:
            scorer = ScoreEngine()
            result["score"] = scorer.combine(result["fundamental"], result["technical"], result["valuation"], result["ownership"])
        except Exception as e:
            result["error"] = True
            result["error_msg"] = f"Failed to score: {e}\n{traceback.format_exc()}"
            
        return result
        
    except Exception as e:
        result["error"] = True
        result["error_msg"] = str(e) + "\n" + traceback.format_exc()
        return result
