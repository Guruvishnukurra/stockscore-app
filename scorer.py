class ScoreEngine:
    def combine(self, fundamental, technical, valuation, ownership):
        f = max(0, min(float(fundamental.get("score", 0)), 35))
        t = max(0, min(float(technical.get("score", 0)), 20))
        v = max(0, min(float(valuation.get("score", 0)), 25))
        o = max(0, min(float(ownership.get("score", 0)), 10))
        
        total = f + t + v + o
        normalized = round((total / 90) * 100)
        normalized = max(0, min(normalized, 100))
        
        # Ratings logic
        if normalized >= 70:
            rating = "Strong Buy"
            emoji = "🟢"
        elif normalized >= 58:
            rating = "Good Investment"
            emoji = "🟢"
        elif normalized >= 44:
            rating = "Average / Hold"
            emoji = "🟡"
        elif normalized >= 32:
            rating = "Risky / Weak"
            emoji = "🟠"
        else:
            rating = "Avoid"
            emoji = "🔴"
            
        all_flags = []
        all_flags.extend(fundamental.get("flags", []))
        all_flags.extend(technical.get("flags", []))
        all_flags.extend(valuation.get("flags", []))
        all_flags.extend(ownership.get("flags", []))
        
        positive = []
        neutral = []
        negative = []
        
        neg_words = ["weak", "poor", "negative", "below", "overvalued", "death", "downtrend", "debt", "insufficient", "missing", "risky", "limited", "avoid", "error", "low"]
        neut_words = ["average", "moderate", "fair", "hold", "watch", "mixed", "caution", "warning"]
        
        for flag in all_flags:
            text_lower = flag.lower()
            if flag.startswith("[+]"):
                positive.append(flag)
            elif flag.startswith("[-]"):
                negative.append(flag)
            elif flag.startswith("[*]"):
                neutral.append(flag)
            elif any(w in text_lower for w in neg_words):
                negative.append(flag)
            elif any(w in text_lower for w in neut_words):
                neutral.append(flag)
            else:
                positive.append(flag)
                
        reasoning = positive + neutral + negative
        
        module_scores = {
            "Fundamentals": {"score": f, "max": 35, "limited_data": fundamental.get("limited_data", False)},
            "Technicals": {"score": t, "max": 20, "limited_data": technical.get("limited_data", False)},
            "Valuation": {"score": v, "max": 25, "limited_data": valuation.get("limited_data", False)},
            "Ownership": {"score": o, "max": 10, "limited_data": ownership.get("limited_data", False)}
        }
        
        return {
            "final_score": normalized,
            "raw_score": total,
            "max_raw": 90,
            "rating": rating,
            "rating_emoji": emoji,
            "reasoning": reasoning,
            "module_scores": module_scores
        }
