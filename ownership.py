import pandas as pd
import numpy as np

class OwnershipAnalyzer:
    def __init__(self, info, balance_sheet_df):
        self.info = info or {}
        self.bs = balance_sheet_df if balance_sheet_df is not None else pd.DataFrame()

    def analyze(self):
        try:
            raw_insider = self.info.get("heldPercentInsiders")
            insider = None
            if raw_insider is not None:
                if raw_insider < 0.01:
                    insider = raw_insider * 10000
                elif raw_insider <= 1:
                    insider = raw_insider * 100
                else:
                    insider = raw_insider
                if insider > 100: insider /= 100
                    
            # Bug Fix: Indian Insider Data Sanity Check
            symbol = self.info.get("symbol", "")
            if (symbol.endswith(".NS") or symbol.endswith(".BO")) and insider is not None:
                if insider < 5:
                    insider = None
                    # flags will be added later in scoring block
                    
            raw_inst = self.info.get("heldPercentInstitutions")
            inst = None
            if raw_inst is not None:
                if raw_inst < 0.01:
                    inst = raw_inst * 10000
                elif raw_inst <= 1:
                    inst = raw_inst * 100
                else:
                    inst = raw_inst
                if inst > 100: inst /= 100

            sector = self.info.get("sector")
            is_bank = sector == "Financial Services"
            
            op_margin = None
            if is_bank:
                pm = self.info.get("profitMargins")
                if pm is not None: op_margin = pm * 100
            else:
                om = self.info.get("operatingMargins")
                if om is not None: op_margin = om * 100
                
            efficiency_metric = None
            if is_bank:
                roa = self.info.get("returnOnAssets")
                if roa is not None: efficiency_metric = roa * 100
            else:
                rev = self.info.get("totalRevenue")
                ta = None
                if not self.bs.empty and "Total Assets" in self.bs.index:
                    row = self.bs.loc["Total Assets"].dropna()
                    if not row.empty: ta = row.iloc[0]
                if rev and ta and ta > 0:
                    efficiency_metric = rev / ta
                    
            beta = self.info.get("beta")
            
            metrics = {
                "promoter_pct": insider,
                "institutional_pct": inst
            }
            
            if insider is not None:
                metrics["Promoter Holding"] = f"{insider:.2f}%"
            else:
                metrics["Promoter Holding"] = "N/A"
                
            if inst is not None:
                metrics["Institutional Holding"] = f"{inst:.2f}%"
            else:
                metrics["Institutional Holding"] = "N/A"
                
            metrics["Operating Margin" if not is_bank else "Net Margin"] = f"{op_margin:.2f}%" if op_margin is not None else "N/A"
            metrics["Asset Turnover" if not is_bank else "Return on Assets"] = f"{efficiency_metric:.2f}x" if not is_bank and efficiency_metric is not None else f"{efficiency_metric:.2f}%" if efficiency_metric is not None else "N/A"
            metrics["Beta"] = f"{beta:.2f}" if beta is not None else "N/A"
            
            score = 0
            flags = []
            
            if insider is None and inst is None:
                return {
                    "score": 5.0, "max": 10, "metrics": metrics,
                    "flags": ["[-] Missing ownership data"], "limited_data": True
                }
                
            # Ownership Quality (6)
            if not is_bank:
                if insider is not None:
                    if insider >= 35: score += 3; flags.append("[+] Strong Promoter/Insider stake (>=35%)")
                    elif insider >= 20: score += 2; flags.append("[*] Healthy Promoter holding (20-35%)")
                    elif insider >= 5: score += 1; flags.append("[*] Modest Promoter stake (5-20%)")
                    else: flags.append("[-] Low Promoter/Insider stake (<5%)")
                elif (symbol.endswith(".NS") or symbol.endswith(".BO")):
                    # Data was discarded due to unreliability (BUG 5)
                    score += 0
                    flags.append("[*] Promoter data unavailable for this stock (skipped)")
                    
                if inst is not None:
                    if inst >= 20: score += 3; flags.append("[+] Strong institutional backing (>=20%)")
                    elif inst >= 10: score += 2; flags.append("[*] Healthy institutional backing (10-20%)")
                    elif inst >= 3: score += 1; flags.append("[*] Modest institutional backing (3-10%)")
            else:
                if inst is not None:
                    if inst >= 40: score += 4; flags.append("[+] Very Strong institutional backing for Bank (>=40%)")
                    elif inst >= 20: score += 3; flags.append("[+] Strong institutional backing (20-40%)")
                    elif inst >= 10: score += 2; flags.append("[*] Healthy institutional backing (10-20%)")
                    elif inst >= 3: score += 1; flags.append("[*] Modest institutional backing (3-10%)")
                    
                if insider is not None:
                    if insider >= 10: score += 2; flags.append("[+] Good promoter/govt skin in the game (>=10%)")
                    elif insider >= 1: score += 1; flags.append("[*] Modest promoter/govt stake (>=1%)")
                    
            # Efficiency (4)
            if op_margin is not None:
                if op_margin >= 15: score += 2
                elif op_margin >= 5: score += 1
                
            if efficiency_metric is not None:
                if not is_bank:
                    if efficiency_metric >= 0.5: score += 2
                    elif efficiency_metric >= 0.2: score += 1
                else:
                    if efficiency_metric >= 1.0: score += 2
                    elif efficiency_metric >= 0.5: score += 1
                    
            final_score = min(max(float(score), 0), 10)
            
            return {
                "score": final_score,
                "max": 10,
                "metrics": metrics,
                "flags": flags,
                "limited_data": False
            }
            
        except Exception:
            return {
                "score": 5.0, "max": 10, "metrics": {},
                "flags": ["[-] Ownership computation error"], "limited_data": True
            }
