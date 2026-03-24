import pandas as pd
import numpy as np

class FundamentalAnalyzer:
    def __init__(self, data_cache, industry_avg):
        self.info = data_cache.get("info", {})
        self.financials = data_cache.get("financials", {})
        self.industry_avg = industry_avg.get("averages", {}) if isinstance(industry_avg, dict) else industry_avg

    def _get_df_val(self, df_type, row_name):
        try:
            df = self.financials.get(df_type, pd.DataFrame())
            if df.empty or row_name not in df.index:
                return None
            row = df.loc[row_name]
            valid_vals = row.dropna()
            if not valid_vals.empty:
                return float(valid_vals.iloc[0])
            return None
        except Exception:
            return None

    def _safe_get(self, info_key):
        val = self.info.get(info_key)
        if val is not None and not pd.isna(val):
            return float(val)
            
        # Fallbacks
        if info_key == "returnOnEquity":
            ni = self._get_df_val("income_statement", "Net Income")
            eq = self._get_df_val("balance_sheet", "Stockholders Equity")
            if ni and eq and eq != 0: return ni / eq
        elif info_key == "returnOnAssets":
            ni = self._get_df_val("income_statement", "Net Income")
            ta = self._get_df_val("balance_sheet", "Total Assets")
            if ni and ta and ta != 0: return ni / ta
        elif info_key == "netMargins":
            ni = self._get_df_val("income_statement", "Net Income")
            tr = self._get_df_val("income_statement", "Total Revenue")
            if ni and tr and tr != 0: return ni / tr
        elif info_key == "operatingMargins":
            oi = self._get_df_val("income_statement", "Operating Income")
            if oi is None:
                oi = self._get_df_val("income_statement", "EBIT")
            tr = self._get_df_val("income_statement", "Total Revenue")
            if oi and tr and tr != 0: return oi / tr
        elif info_key == "currentRatio":
            ca = self._get_df_val("balance_sheet", "Current Assets")
            cl = self._get_df_val("balance_sheet", "Current Liabilities")
            if ca and cl and cl != 0: return ca / cl
            
        return None

    def _calc_3y_growth(self, df_type, row_name):
        try:
            df = self.financials.get(df_type, pd.DataFrame())
            if df.empty or row_name not in df.index:
                return None
            row = df.loc[row_name].dropna()
            if len(row) < 2:
                return None
            # yfinance returns newest first, reverse it to oldest first
            vals = list(row)[:4] # get up to 4 newest available
            vals.reverse() 
            
            changes = []
            for i in range(1, len(vals)):
                prev = vals[i-1]
                curr = vals[i]
                if prev is None or curr is None or prev == 0:
                    continue
                # Simple handling of negative denominators
                if prev < 0 and curr > prev:
                    chg = abs((curr - prev) / prev)
                elif prev < 0 and curr < prev:
                    chg = -abs((curr - prev) / prev)
                else:
                    chg = (curr - prev) / prev
                changes.append(chg)
            
            if not changes:
                return None
            avg_chg = sum(changes) / len(changes) * 100
            return min(avg_chg, 40.0) # Cap at 40%
        except Exception:
            return None

    def analyze(self):
        roe_raw = self._safe_get("returnOnEquity")
        roe = roe_raw * 100 if roe_raw is not None else None
        
        roa_raw = self._safe_get("returnOnAssets")
        roa = roa_raw * 100 if roa_raw is not None else None
        
        net_margin_raw = self._safe_get("netMargins")
        net_margin = net_margin_raw * 100 if net_margin_raw is not None else None
        
        op_margin_raw = self._safe_get("operatingMargins")
        op_margin = op_margin_raw * 100 if op_margin_raw is not None else None
        
        # Revenue Growth
        rg_1y_raw = self.info.get("revenueGrowth")
        rg_1y = float(rg_1y_raw) * 100 if rg_1y_raw is not None else None
        rg_3y = self._calc_3y_growth("income_statement", "Total Revenue")
        
        rev_growth = None
        if rg_1y is not None and rg_3y is not None:
            rev_growth = min(rg_1y, rg_3y)
        elif rg_1y is not None:
            rev_growth = min(rg_1y, 40.0)
        elif rg_3y is not None:
            rev_growth = min(rg_3y, 40.0)
            
        # Earnings Growth
        eg_1y_raw = self.info.get("earningsGrowth")
        eg_1y = float(eg_1y_raw) * 100 if eg_1y_raw is not None else None
        eg_3y = self._calc_3y_growth("income_statement", "Net Income")
        
        earn_growth = None
        if eg_1y is not None and eg_3y is not None:
            earn_growth = min(eg_1y, eg_3y)
        elif eg_1y is not None:
            earn_growth = min(eg_1y, 40.0)
        elif eg_3y is not None:
            earn_growth = min(eg_3y, 40.0)
            
        # Valuations
        pe = self._safe_get("trailingPE")
        if pe is None:
            pe = self.info.get("forwardPE")
                
        # FIX 3 — Calculate PE from price and EPS as a persistent fallback
        if pe is None:
            price = self.info.get("currentPrice")
            # Try trailing EPS first
            eps = self.info.get("trailingEps")
            if eps is None or eps <= 0:
                # Calculate EPS from net income / shares
                ni = self._get_df_val("income_statement", "Net Income")
                shares = self.info.get("sharesOutstanding")
                if ni and shares and shares > 0:
                    eps = ni / shares
            if price and eps and eps > 0 and price > 0:
                pe = price / eps
                # Sanity check - PE should be between 1 and 500
                if pe < 1 or pe > 500:
                    pe = None
                    
        # FIX 4 — Store calculated PE back in the info dict
        if pe is not None:
            self.info["_calculated_pe"] = pe

        pb = self._safe_get("priceToBook")
        if pb is None:
            price = self.info.get("currentPrice")
            mcap = self.info.get("marketCap")
            ta = self._get_df_val("balance_sheet", "Total Assets")
            tl = self._get_df_val("balance_sheet", "Total Liabilities Net Minority Interest")
            if mcap and ta and tl:
                book_value = ta - tl
                shares = self.info.get("sharesOutstanding")
                if book_value and shares and shares > 0:
                    bvps = book_value / shares
                    cp = self.info.get("currentPrice")
                    if cp and bvps > 0:
                        pb = cp / bvps
                        
        peg = self.info.get("trailingPegRatio")
        if peg is None and pe is not None and earn_growth is not None and earn_growth > 0:
            peg = pe / earn_growth
            
        # Financial Strength
        debt_equity = None
        td = self._get_df_val("balance_sheet", "Total Debt")
        eq = self._get_df_val("balance_sheet", "Stockholders Equity")
        if td is not None and eq is not None and eq != 0:
            debt_equity = td / eq
        if debt_equity is None:
            de_raw = self.info.get("debtToEquity")
            if de_raw is not None:
                debt_equity = de_raw / 100.0 if de_raw > 20 else de_raw
                
        current_ratio = self._safe_get("currentRatio")
        
        interest_cov = None
        if self.info.get("sector") != "Financial Services":
            oi = self._get_df_val("income_statement", "Operating Income")
            if oi is None:
                oi = self._get_df_val("income_statement", "EBIT")
            ie = self._get_df_val("income_statement", "Interest Expense Non Operating")
            if ie is None:
                ie = self._get_df_val("income_statement", "Interest Expense")
            if oi is not None and ie is not None and ie != 0:
                interest_cov = oi / abs(ie)
                
        # FCF
        fcf = self.info.get("freeCashflow")
        if fcf is None:
            fcf = self._get_df_val("cash_flow", "Free Cash Flow")
        if fcf is None:
            ocf = self._get_df_val("cash_flow", "Operating Cash Flow")
            cap = self._get_df_val("cash_flow", "Capital Expenditure")
            if ocf is not None and cap is not None:
                fcf = ocf - abs(cap)
        if fcf is None:
            ocf_info = self.info.get("operatingCashflow")
            if ocf_info: fcf = ocf_info * 0.7
            
        fcf_margin = None
        tr = self.info.get("totalRevenue") or self._get_df_val("income_statement", "Total Revenue")
        if fcf is not None and tr is not None and tr != 0:
            fcf_margin = (fcf / tr) * 100
            
        asset_turnover = None
        ta = self._get_df_val("balance_sheet", "Total Assets")
        if tr is not None and ta is not None and ta != 0:
            asset_turnover = tr / ta
            
        ebitda_margin = None
        ebitda = self._get_df_val("income_statement", "EBITDA") or self._get_df_val("income_statement", "Normalized EBITDA")
        if ebitda is not None and tr is not None and tr != 0:
            ebitda_margin = (ebitda / tr) * 100

        ev_ebitda = self.info.get("enterpriseToEbitda")
        if ev_ebitda is None:
            ev = self.info.get("enterpriseValue")
            ebitda_val = self._get_df_val("income_statement", "EBITDA") or self._get_df_val("income_statement", "Normalized EBITDA")
            if ev and ebitda_val and ebitda_val != 0:
                ev_ebitda = ev / ebitda_val

        # SCORING
        score = 0.0
        max_possible = 0.0
        flags = []
        is_financial = self.info.get("sector") == "Financial Services"
        
        # Profitability (10)
        if roe is not None:
            max_possible += 3
            if roe >= 15: score += 3; flags.append("[+] Strong Return on Equity (>=15%)")
            elif roe >= 8: score += 2; flags.append("[*] Healthy ROE (8-15%)")
            elif roe >= 4: score += 1; flags.append("[*] Modest ROE (4-8%)")
            else: flags.append("[-] Weak Return on Equity (<4%)")
            
        if net_margin is not None:
            max_possible += 3
            if net_margin >= 12: score += 3; flags.append("[+] Good Net Margins (>=12%)")
            elif net_margin >= 5: score += 2; flags.append("[*] Healthy Net Margins (5-12%)")
            elif net_margin >= 2: score += 1; flags.append("[*] Thin Net Margins (2-5%)")
            else: flags.append("[-] Low Net Margins (<2%)")
            
        if op_margin is not None:
            max_possible += 2
            if op_margin >= 15: score += 2; flags.append("[+] Strong Operating Margins (>=15%)")
            elif op_margin >= 7: score += 1; flags.append("[*] Healthy Operating Margins (7-15%)")
            else: flags.append("[-] Thin Operating Margins (<7%)")
            
        if fcf_margin is not None:
            max_possible += 2
            if fcf_margin >= 10: score += 2; flags.append("[+] Strong Free Cash Flow generation (>=10%)")
            elif fcf_margin >= 3: score += 1; flags.append("[*] Healthy FCF conversion (3-10%)")
            else: flags.append("[-] Poor Free Cash Flow conversion (<3%)")

        # Growth (8)
        if rev_growth is not None:
            max_possible += 4
            if rev_growth >= 12: score += 4; flags.append("[+] Strong Revenue Growth (>=12%)")
            elif rev_growth >= 5: score += 2; flags.append("[*] Steady Revenue Growth (5-12%)")
            elif rev_growth >= 1: score += 1; flags.append("[*] Modest Revenue Growth (1-5%)")
            else: flags.append("[-] Sluggish Revenue Growth (<1%)")
            
        if earn_growth is not None:
            max_possible += 4
            if earn_growth >= 15: score += 4; flags.append("[+] Strong Earnings Growth (>=15%)")
            elif earn_growth >= 7: score += 2; flags.append("[*] Healthy Earnings Growth (7-15%)")
            elif earn_growth >= 1: score += 1; flags.append("[*] Modest Earnings Growth (1-7%)")
            else: flags.append("[-] Weak Earnings Growth (<1%)")

        # Relative Valuation Section Removed - Moved to Valuation Module

        # Financial Strength (11)
        if not is_financial and debt_equity is not None:
            max_possible += 3
            if debt_equity <= 0.5: score += 3; flags.append("[+] Low Debt-to-Equity burden (<=0.5)")
            elif debt_equity <= 1.5: score += 2; flags.append("[*] Moderate Debt-to-Equity ratio (0.5-1.5)")
            elif debt_equity <= 3.0: score += 1; flags.append("[-] High Debt-to-Equity ratio (1.5-3.0)")
            else: flags.append("[-] Dangerous Debt levels (>3.0)")
            
        if current_ratio is not None:
            max_possible += 2
            if current_ratio >= 1.2: score += 2; flags.append("[+] Strong near-term liquidity (>=1.2)")
            elif current_ratio >= 0.8: score += 1; flags.append("[*] Adequate near-term liquidity (0.8-1.2)")
            else: flags.append("[-] Poor near-term liquidity (<0.8)")
            
        if not is_financial and interest_cov is not None:
            max_possible += 4
            if interest_cov >= 3: score += 4; flags.append("[+] Safe Interest Coverage cushion (>=3x)")
            elif interest_cov >= 1.5: score += 2; flags.append("[*] Adequate Interest Coverage (1.5-3x)")
            else: flags.append("[-] Weak Interest Coverage ratio (<1.5x)")

        # Bug Fix: FCF Positive and Gross Margin (2 pts)
        if fcf is not None:
            max_possible += 1
            if fcf > 0:
                score += 1
                flags.append("[+] Positive Free Cash Flow generation")
                
        gm_raw = self.info.get("grossMargins")
        if gm_raw is not None:
            gm = float(gm_raw) * 100
            max_possible += 1
            if gm > 30:
                score += 1
                flags.append(f"[+] Healthy Gross Margins ({gm:.1f}%)")

        # Bug fix: Proportional Normalization Problem
        limited_data = False
        if max_possible < 20:
            # Denominator stays at 35, missing data counts as zero
            final_score = (score / 35.0) * 35.0 
            limited_data = True
        else:
            final_score = (score / max_possible * 35) if max_possible > 0 else 0
            
        final_score = max(0.0, min(float(final_score), 35.0))

        # final_score is already calculated above with the sparse data fix
        
        if roe is None and net_margin is None and rev_growth is None:
            limited_data = True

        ratios = {
            "ROE": roe, "ROA": roa, "Net Margin": net_margin,
            "Operating Margin": op_margin, "FCF Margin": fcf_margin,
            "EBITDA Margin": ebitda_margin, "Revenue Growth": rev_growth,
            "Earnings Growth": earn_growth, "PE Ratio": pe,
            "PB Ratio": pb, "PEG Ratio": peg, "Debt/Equity": debt_equity,
            "Current Ratio": current_ratio, "Interest Coverage": interest_cov,
            "Asset Turnover": asset_turnover, "EV/EBITDA": ev_ebitda,
            "Price/Sales": self.info.get("priceToSalesTrailing12Months")
        }
        
        return {
            "score": final_score,
            "max": 35,
            "ratios": ratios,
            "flags": flags,
            "limited_data": limited_data
        }
