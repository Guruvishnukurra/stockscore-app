from main import analyze_stock
import json

if __name__ == "__main__":
    res = analyze_stock("AAPL")
    print(f"Final Score: {res.get('score', {}).get('final_score')}")
    print(f"Valuation: {res.get('score', {}).get('module_scores', {}).get('Valuation')}")
