import pandas as pd
import numpy as np
import yfinance as yf

class ValuationAnalyzer:
    def __init__(self, data_cache, industry_avg):
        self.info = data_cache.get("info", {})
        self.financials = data_cache.get("financials", {})
        self.industry_avg = industry_avg.get("averages", {}) if isinstance(industry_avg, dict) else industry_avg

    def analyze(self):
        using_proxy = False
        using_analyst_estimates = False
        fcf = None
        
        # STEP 1 — Fetch analyst estimates
        analyst_eps = []
        analyst_revenue = []
        try:
            t = yf.Ticker(self.info.get("symbol",""))
            
            # Robust extraction function
            def extract_from_df(df):
                vals = []
                if df is None or df.empty: return vals
                
                # Check rows vs cols structure
                # We want 0y and +1y estimates
                target_periods = ['0y', '+1y', 'Current Year', 'Next Year']
                target_cols = ['avg', 'Avg', 'Avg. Estimate']
                
                # Case A: Periods are in index, values in columns (Indian/New style)
                idx_names = [str(i) for i in df.index]
                for p in target_periods:
                    if p in idx_names:
                        for c in target_cols:
                            if c in df.columns:
                                val = df.loc[p, c]
                                if val and not pd.isna(val) and float(val) != 0:
                                    vals.append(float(val))
                                    break
                
                # Case B: Estimates in index, Periods in columns (Older style)
                if not vals:
                    for r in target_cols:
                        if r in df.index:
                            for c in target_periods:
                                if c in df.columns:
                                    val = df.loc[r, c]
                                    if val and not pd.isna(val) and float(val) != 0:
                                        vals.append(float(val))
                return vals

            analyst_eps = extract_from_df(t.earnings_estimate)
            analyst_revenue = extract_from_df(t.revenue_estimate)
        except:
            pass

        try:
            cf_df = self.financials.get("cash_flow", pd.DataFrame())
            
            # Step 1
            fcf_info = self.info.get("freeCashflow")
            if fcf_info is not None and fcf_info != 0:
                fcf = float(fcf_info)
            else:
                # Step 2
                if not cf_df.empty and "Free Cash Flow" in cf_df.index:
                    row = cf_df.loc["Free Cash Flow"].dropna()
                    if not row.empty:
                        # yfinance sorts newest first - use latest for valuation accuracy
                        fcf = row.iloc[0]
                
                # Step 3
                if fcf is None and not cf_df.empty and "Operating Cash Flow" in cf_df.index and "Capital Expenditure" in cf_df.index:
                    ocf_row = cf_df.loc["Operating Cash Flow"].dropna()
                    cap_row = cf_df.loc["Capital Expenditure"].dropna()
                    
                    if not ocf_row.empty and not cap_row.empty:
                        avg_ocf = ocf_row.iloc[0]
                        avg_cap = cap_row.iloc[0]
                        fcf = avg_ocf - abs(avg_cap)
                        
                # Step 4
                if fcf is None:
                    ocf_info = self.info.get("operatingCashflow")
                    if ocf_info is not None:
                        fcf = float(ocf_info) * 0.7
                        using_proxy = True
                        
                # Step 5
                if fcf is None:
                    ni_info = self.info.get("netIncome")
                    if ni_info is None:
                        ic_df = self.financials.get("income_statement", pd.DataFrame())
                        if not ic_df.empty and "Net Income" in ic_df.index:
                            ni_row = ic_df.loc["Net Income"].dropna()
                            if not ni_row.empty:
                                ni_info = ni_row.iloc[0]
                    if ni_info is not None:
                        fcf = float(ni_info) * 0.5
                        using_proxy = True

            curr_price = self.info.get("currentPrice") or self.info.get("regularMarketPrice") or self.info.get("previousClose")
            market_cap = self.info.get("marketCap")
            shares = None
            
            if self.info.get("sharesOutstanding"):
                shares = self.info.get("sharesOutstanding")
            elif self.info.get("impliedSharesOutstanding"):
                shares = self.info.get("impliedSharesOutstanding")
            elif self.info.get("floatShares"):
                shares = self.info.get("floatShares")
            elif market_cap and curr_price and curr_price > 0:
                shares = market_cap / curr_price


            # STEP 2 — Calculate growth rate from analyst estimates if available:
            analyst_growth = None

            if len(analyst_eps) >= 2:
                # Use analyst EPS growth as growth rate
                g_rates = []
                for i in range(1, len(analyst_eps)):
                    if analyst_eps[i-1] > 0:
                        g = (analyst_eps[i] - analyst_eps[i-1]) / analyst_eps[i-1]
                        g_rates.append(g)
                if g_rates:
                    analyst_growth = sum(g_rates) / len(g_rates)
                    # Cap between -5% and 20%
                    analyst_growth = min(max(analyst_growth, -0.05), 0.20)

            elif len(analyst_revenue) >= 2:
                # Fall back to revenue growth estimate
                if analyst_revenue[0] > 0:
                    analyst_growth = (analyst_revenue[1] - analyst_revenue[0]) / analyst_revenue[0]
                    analyst_growth = min(max(analyst_growth, -0.05), 0.20)

            # Use analyst growth if available, else fall back to historical
            if analyst_growth is not None:
                growth_rate = analyst_growth
                using_analyst_estimates = True
            else:
                rev_growth = self.info.get("revenueGrowth")
                growth_rate = 0.05
                if rev_growth is not None:
                    growth_rate = min(max(float(rev_growth), -0.05), 0.15)
                using_analyst_estimates = False

            # STEP 3 — Use forward EPS to anchor FCF
            fwd_eps = self.info.get("forwardEps")
            
            if fwd_eps and fwd_eps > 0 and shares:
                implied_net_income = fwd_eps * shares
                # FCF is typically 80-110% of net income for quality companies
                # Use a conservative 85% conversion
                analyst_fcf = implied_net_income * 0.85
                
                # Only use analyst FCF if it is reasonably close to historical FCF (within 5x)
                if fcf is not None and fcf > 0:
                    ratio = analyst_fcf / fcf
                    if 0.2 <= ratio <= 5.0:
                        # Blend: 60% analyst, 40% historical
                        fcf = analyst_fcf * 0.6 + fcf * 0.4
                    else:
                        # Estimates too different from reality, use historical only
                        pass
                elif fcf is None or fcf <= 0:
                    # No historical FCF, use analyst
                    fcf = analyst_fcf
                    using_proxy = True
                
            dcf_score = 0
            flags = []
            
            dcf_res = {
                "intrinsic_value_per_share": None,
                "current_price": curr_price,
                "upside_pct": None,
                "projected_fcfs": [],
                "pv_sum": None,
                "terminal_value": None,
                "data_source": ("Analyst Estimates" if using_analyst_estimates else "Historical FCF"),
                "analyst_growth_used": (analyst_growth is not None),
                "growth_rate_used": growth_rate
            }
            
            if fcf is None or shares is None or curr_price is None or shares <= 0:
                dcf_score = 7.5
                flags.append("[-] Insufficient data for DCF valuation")
            elif fcf <= 0:
                dcf_score = 0
                flags.append("[-] Negative Free Cash Flow (Cannot run DCF)")
            else:
                terminal_growth = 0.03
                wacc = 0.12
                
                projected = []
                pv_sum = 0
                for n in range(1, 6):
                    p_fcf = fcf * ((1 + growth_rate) ** n)
                    projected.append(p_fcf)
                    pv_sum += p_fcf / ((1 + wacc) ** n)
                    
                tv = (projected[4] * (1 + terminal_growth)) / (wacc - terminal_growth)
                pv_tv = tv / ((1 + wacc) ** 5)
                
                intrinsic_total = pv_sum + pv_tv
                intrinsic_ps = intrinsic_total / shares
                upside = (intrinsic_ps - curr_price) / curr_price * 100
                
                dcf_res["intrinsic_value_per_share"] = intrinsic_ps
                dcf_res["upside_pct"] = upside
                dcf_res["projected_fcfs"] = projected
                dcf_res["pv_sum"] = pv_sum
                dcf_res["terminal_value"] = tv
                
                if not using_proxy:
                    if upside > 25: dcf_score = 10; flags.append("[+] Huge upside based on DCF (>25%)")
                    elif upside > 10: dcf_score = 8; flags.append("[+] Strong upside based on DCF (>10%)")
                    elif upside > 0: dcf_score = 6; flags.append("[*] Fairly valued according to DCF (>0%)")
                    elif upside > -20: dcf_score = 4; flags.append("[-] Slightly overvalued according to DCF (>-20%)")
                    elif upside > -40: dcf_score = 2; flags.append("[-] Overvalued according to DCF (>-40%)")
                    elif upside > -65: dcf_score = 1; flags.append("[-] Highly overvalued according to DCF (>-65%)")
                    else: flags.append("[-] Extreme overvaluation according to DCF (<-65%)")
                else:
                    if upside > 25: dcf_score = 6; flags.append("[+] Upside indicated by proxy DCF (>25%)")
                    elif upside > 10: dcf_score = 4; flags.append("[+] Moderate upside by proxy DCF (>10%)")
                    elif upside > 0: dcf_score = 3; flags.append("[*] Fairly valued by proxy DCF (>0%)")
                    elif upside > -20: dcf_score = 2; flags.append("[-] Slightly overvalued by proxy DCF (>-20%)")
                    elif upside > -40: dcf_score = 1; flags.append("[-] Overvalued by proxy DCF (>-40%)")
                    else: flags.append("[-] Overvalued according to proxy DCF")

            pe_score = 0
            pe_res = {
                "forward_eps": None, "industry_pe": self.industry_avg.get("pe", 20),
                "fair_value": None, "current_price": curr_price,
                "upside_pct": None, "forward_pe": None, "relative_pe": None
            }
            
            fwd_eps = self.info.get("forwardEps")
            ind_pe = self.industry_avg.get("pe", 20)
            
            if fwd_eps is None or fwd_eps <= 0 or curr_price is None or ind_pe <= 0:
                # FIX 4 — Use calculated PE as proxy
                cached_pe = self.info.get("_calculated_pe")
                if cached_pe and curr_price and ind_pe and ind_pe > 0:
                    fwd_pe = cached_pe * 0.95
                    rel_pe = fwd_pe / ind_pe
                    
                    pe_res["forward_pe"] = fwd_pe
                    pe_res["relative_pe"] = rel_pe
                    
                    if rel_pe < 0.7: pe_score = 10; flags.append("[+] Forward PE implies significant discount to Industry (<0.7x)")
                    elif rel_pe < 0.9: pe_score = 8; flags.append("[+] Forward PE implies discount to Industry (<0.9x)")
                    elif rel_pe < 1.1: pe_score = 6; flags.append("[*] Forward Valuation inline with Industry Peers (<1.1x)")
                    elif rel_pe < 1.3: pe_score = 4; flags.append("[*] Forward Valuation slightly above Industry (<1.3x)")
                    elif rel_pe < 1.6: pe_score = 2; flags.append("[-] Forward PE suggests moderate premium (<1.6x)")
                    elif rel_pe < 2.0: pe_score = 1; flags.append("[-] Forward PE suggests high premium (<2.0x)")
                    else: flags.append("[-] High valuation premium relative to industry peers (>2.0x)")
                else:
                    pe_score = 5
            else:
                fwd_pe = curr_price / fwd_eps
                rel_pe = fwd_pe / ind_pe
                fair_val = fwd_eps * ind_pe
                upside = (fair_val - curr_price) / curr_price * 100
                
                pe_res["forward_eps"] = fwd_eps
                pe_res["fair_value"] = fair_val
                pe_res["upside_pct"] = upside
                pe_res["forward_pe"] = fwd_pe
                pe_res["relative_pe"] = rel_pe
                
                if rel_pe < 0.7: pe_score = 10; flags.append("[+] Forward PE implies significant discount to Industry (<0.7x)")
                elif rel_pe < 0.9: pe_score = 8; flags.append("[+] Forward PE implies discount to Industry (<0.9x)")
                elif rel_pe < 1.1: pe_score = 6; flags.append("[*] Forward Valuation inline with Industry Peers (<1.1x)")
                elif rel_pe < 1.3: pe_score = 4; flags.append("[*] Forward Valuation slightly above Industry (<1.3x)")
                elif rel_pe < 1.6: pe_score = 2; flags.append("[-] Forward PE suggests moderate premium (<1.6x)")
                elif rel_pe < 2.0: pe_score = 1; flags.append("[-] Forward PE suggests high premium (<2.0x)")
                else: flags.append("[-] High valuation premium relative to industry peers (>2.0x)")
                
            # Quality Bonus (max 5)
            quality_bonus = 0
            roe = self.info.get("returnOnEquity")
            net_margin = self.info.get("netMargins")
            rev_growth = self.info.get("revenueGrowth")
            
            if roe and net_margin:
                if (roe * 100) > 15 and (net_margin * 100) > 10:
                    quality_bonus += 3
                    flags.append("[+] Quality Bonus: High ROE and Net Margins")
            
            if rev_growth:
                if (rev_growth * 100) > 10:
                    quality_bonus += 2
                    flags.append("[+] Quality Bonus: Strong Revenue Growth")
                    
            total_score = dcf_score + pe_score + quality_bonus
            total_score = min(max(total_score, 0), 25)
            
            return {
                "score": float(total_score),
                "max": 25,
                "dcf": dcf_res,
                "pe_valuation": pe_res,
                "flags": flags,
                "limited_data": (not dcf_res.get("projected_fcfs"))
            }
            
        except Exception:
            return {
                "score": 12.5, "max": 25, "dcf": {}, "pe_valuation": {}, 
                "flags": ["[-] Valuation computation error"], "limited_data": True
            }
