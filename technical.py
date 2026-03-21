import pandas as pd
import numpy as np

class TechnicalAnalyzer:
    def __init__(self, price_df: pd.DataFrame):
        self.df = price_df.copy() if price_df is not None else pd.DataFrame()

    def analyze(self):
        if self.df.empty or len(self.df) < 50:
            return {
                "score": 8.0,
                "max": 20,
                "indicators": {},
                "price_df_with_indicators": self.df,
                "flags": ["[-] Insufficient price history for technical analysis"],
                "limited_data": True
            }

        # Ensure Date column
        if "Date" not in self.df.columns:
            self.df = self.df.reset_index()
            for col in self.df.columns:
                if col.lower() in ["date", "datetime"]:
                    self.df = self.df.rename(columns={col: "Date"})
                    break
                    
        if "Close" not in self.df.columns:
            return {
                "score": 8.0, "max": 20, "indicators": {}, "price_df_with_indicators": self.df,
                "flags": ["[-] Missing Close price data"], "limited_data": True
            }

        df = self.df.copy()
        
        # MAs
        df["MA50"] = df["Close"].rolling(50).mean()
        df["MA200"] = df["Close"].rolling(200).mean()
        
        # RSI Wilder Smoothing
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        
        avg_gain = pd.Series(index=df.index, dtype=float)
        avg_loss = pd.Series(index=df.index, dtype=float)
        
        if len(df) > 14:
            avg_gain.iloc[14] = gain.iloc[1:15].mean()
            avg_loss.iloc[14] = loss.iloc[1:15].mean()
            
            for i in range(15, len(df)):
                avg_gain.iloc[i] = (avg_gain.iloc[i-1] * 13 + gain.iloc[i]) / 14
                avg_loss.iloc[i] = (avg_loss.iloc[i-1] * 13 + loss.iloc[i]) / 14
                
        rs = avg_gain / avg_loss.replace(0, 0.0001)
        df["RSI"] = 100 - (100 / (1 + rs))
        df["RSI"] = df["RSI"].clip(0, 100)
        
        # MACD
        ema12 = df["Close"].ewm(span=12, adjust=False).mean()
        ema26 = df["Close"].ewm(span=26, adjust=False).mean()
        df["MACD_Line"] = ema12 - ema26
        df["Signal_Line"] = df["MACD_Line"].ewm(span=9, adjust=False).mean()
        df["MACD_Hist"] = df["MACD_Line"] - df["Signal_Line"]
        
        # Support / Resistance
        df["Support"] = df["Low"].rolling(60).min()
        df["Resistance"] = df["High"].rolling(60).max()
        
        curr_price = df["Close"].iloc[-1]
        
        # Momentum 3M
        if len(df) >= 63:
            price_63d_ago = df["Close"].iloc[-63]
            momentum_3m = (curr_price - price_63d_ago) / price_63d_ago * 100
        else:
            momentum_3m = None
            
        # 52w pos
        if len(df) >= 252:
            low_52w = df["Low"].tail(252).min()
            high_52w = df["High"].tail(252).max()
        else:
            low_52w = df["Low"].min()
            high_52w = df["High"].max()
            
        pos_52w = (curr_price - low_52w) / (high_52w - low_52w) if (high_52w - low_52w) > 0 else 0.5
        
        # Crosses
        df["Golden_Cross"] = (df["MA50"] > df["MA200"]) & (df["MA50"].shift(1) <= df["MA200"].shift(1))
        df["Death_Cross"] = (df["MA50"] < df["MA200"]) & (df["MA50"].shift(1) >= df["MA200"].shift(1))
        
        golden_cross = df["Golden_Cross"].tail(30).any()
        death_cross = df["Death_Cross"].tail(30).any()
        
        ma50 = df["MA50"].iloc[-1]
        ma200 = df["MA200"].iloc[-1]
        rsi = df["RSI"].iloc[-1]
        macd_line = df["MACD_Line"].iloc[-1]
        signal = df["Signal_Line"].iloc[-1]
        hist = df["MACD_Hist"].iloc[-1]
        hist_prev = df["MACD_Hist"].iloc[-2] if len(df) >= 2 else 0
        support = df["Support"].iloc[-1]
        resistance = df["Resistance"].iloc[-1]
        
        vol_10d = df["Volume"].tail(10).mean()
        vol_60d = df["Volume"].tail(60).mean()
        
        score = 0
        flags = []
        
        # Trend (5)
        if not pd.isna(ma50) and not pd.isna(ma200):
            if curr_price > ma50 and curr_price > ma200:
                score += 3
                flags.append("[+] Bullish Trend (Price > MAs)")
            elif curr_price > ma200:
                score += 1
                flags.append("[*] Long-term support intact (Price > MA200)")
            else:
                flags.append("[-] Bearish Trend (Price < MAs)")
                
        if golden_cross:
            score += 2
            flags.append("[+] Recent Golden Cross (Bullish signal)")
        if death_cross:
            score -= 2
            flags.append("[-] Recent Death Cross (Bearish signal)")
            
        score = max(0, score) # min 0 for trend
            
        # Momentum (8)
        # RSI
        if not pd.isna(rsi):
            if 50 <= rsi <= 65: score += 3; flags.append("[+] Ideal Bullish RSI (50-65)")
            elif 65 < rsi <= 75: score += 2; flags.append("[+] Strong RSI momentum")
            elif 40 <= rsi < 50: score += 2; flags.append("[*] Neutral RSI tracking")
            elif 75 < rsi <= 80: score += 1; flags.append("[-] Warning: RSI approaching overbought")
            elif 30 <= rsi < 40: score += 1; flags.append("[-] Weak RSI momentum, nearing oversold")
            elif rsi > 80: flags.append("[-] Asset overbought (RSI > 80)")
            elif rsi < 30: flags.append("[-] Asset heavily oversold (RSI < 30)")
            
        # MACD
        if not pd.isna(macd_line) and not pd.isna(signal):
            if macd_line > signal and hist > 0 and hist > hist_prev:
                score += 3
                flags.append("[+] Strong Bullish MACD (Expanding)")
            elif macd_line > signal:
                score += 2
                flags.append("[+] Bullish MACD Cross")
            elif macd_line < signal and hist > hist_prev:
                score += 1
                flags.append("[*] Negative MACD but histogram improving")
            else:
                flags.append("[-] Bearish MACD momentum")
                
        # 3M
        if momentum_3m is not None:
            if momentum_3m > 10: score += 2; flags.append("[+] Strong quarterly momentum")
            elif momentum_3m > 0: score += 1
            else: flags.append("[-] Negative quarterly momentum")
            
        # S/R (4)
        if pos_52w > 0.5:
            score += 1
            
        if not pd.isna(support) and not pd.isna(resistance):
            midpoint = (support + resistance) / 2
            if curr_price > midpoint:
                score += 2
            if (curr_price - support) / support < 0.05 and curr_price >= support:
                score += 1
                flags.append("[+] Price near support levels")
                
        # Volume (3)
        if not pd.isna(vol_10d) and not pd.isna(vol_60d) and vol_60d > 0:
            if vol_10d > vol_60d:
                score += 3
                flags.append("[+] Rising volume supporting price action")
            elif (vol_10d / vol_60d) >= 0.8:
                score += 1
                
        final_score = max(0.0, min(float(score), 20.0))
        limited_data = len(df) < 200
        
        indicators = {
            "MA50": ma50, "MA200": ma200, "RSI": rsi,
            "MACD_Line": macd_line, "Signal_Line": signal, "MACD_Hist": hist,
            "Golden_Cross": bool(golden_cross), "Death_Cross": bool(death_cross),
            "Momentum_3M": momentum_3m, "Pos_52W": pos_52w
        }
        
        return {
            "score": final_score,
            "max": 20,
            "indicators": indicators,
            "price_df_with_indicators": df,
            "flags": flags,
            "limited_data": limited_data
        }
