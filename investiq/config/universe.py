"""
InvestIQ — the tracked security universe (broad: Nifty 50 + many funds).

Equities are yfinance tickers; the benchmark is the Nifty 50 index. Mutual funds
are given as (name substring, category) targets that `mfapi_adapter` resolves to
a concrete scheme code (preferring Direct-Growth plans). Everything here is just a
starting set — it's data, easily edited/extended.
"""

BENCHMARK = "^NSEI"  # Nifty 50 index

# Nifty 50 constituents (snapshot; membership changes over time).
NIFTY50 = [
    "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "TCS.NS",
    "ITC.NS", "LT.NS", "AXISBANK.NS", "SBIN.NS", "BHARTIARTL.NS",
    "KOTAKBANK.NS", "HINDUNILVR.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "HCLTECH.NS", "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "WIPRO.NS",
    "NESTLEIND.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "TATAMOTORS.NS",
    "TATASTEEL.NS", "JSWSTEEL.NS", "ADANIENT.NS", "ADANIPORTS.NS", "COALINDIA.NS",
    "BAJAJFINSV.NS", "GRASIM.NS", "HDFCLIFE.NS", "SBILIFE.NS", "BRITANNIA.NS",
    "CIPLA.NS", "DRREDDY.NS", "EICHERMOT.NS", "HEROMOTOCO.NS", "HINDALCO.NS",
    "DIVISLAB.NS", "BPCL.NS", "TECHM.NS", "INDUSINDBK.NS", "APOLLOHOSP.NS",
    "BAJAJ-AUTO.NS", "TATACONSUM.NS", "LTIM.NS", "M&M.NS", "SHRIRAMFIN.NS",
]

# Mutual fund targets: (name substring to search on mfapi, fallback category label).
FUND_TARGETS = [
    ("Parag Parikh Flexi Cap", "Flexi Cap"),
    ("HDFC Flexi Cap", "Flexi Cap"),
    ("Kotak Flexicap", "Flexi Cap"),
    ("Quant Flexi Cap", "Flexi Cap"),
    ("Mirae Asset Large Cap", "Large Cap"),
    ("ICICI Prudential Bluechip", "Large Cap"),
    ("Axis Bluechip", "Large Cap"),
    ("Nippon India Large Cap", "Large Cap"),
    ("SBI Bluechip", "Large Cap"),
    ("Canara Robeco Bluechip Equity", "Large Cap"),
    ("Mirae Asset Emerging Bluechip", "Large & Mid Cap"),
    ("Kotak Emerging Equity", "Mid Cap"),
    ("HDFC Mid-Cap Opportunities", "Mid Cap"),
    ("Motilal Oswal Midcap", "Mid Cap"),
    ("Axis Midcap", "Mid Cap"),
    ("DSP Midcap", "Mid Cap"),
    ("Nippon India Small Cap", "Small Cap"),
    ("SBI Small Cap", "Small Cap"),
    ("Axis Small Cap", "Small Cap"),
    ("Quant Small Cap", "Small Cap"),
    ("ICICI Prudential Value Discovery", "Value"),
    ("SBI Contra", "Contra"),
    ("UTI Nifty 50 Index", "Index"),
    ("HDFC Index Fund Nifty 50", "Index"),
    ("UTI Nifty Next 50 Index", "Index"),
    ("ICICI Prudential Technology", "Sectoral/Thematic"),
    ("Tata Digital India", "Sectoral/Thematic"),
    ("Nippon India Pharma", "Sectoral/Thematic"),
    ("HDFC Balanced Advantage", "Hybrid"),
    ("ICICI Prudential Balanced Advantage", "Hybrid"),
    ("SBI Equity Hybrid", "Hybrid"),
]
