import sys
from main import analyze_stock

def dummy_cb(msg):
    pass

if __name__ == "__main__":
    res = analyze_stock("RELIANCE.NS", dummy_cb)
    print("FINISHED")
