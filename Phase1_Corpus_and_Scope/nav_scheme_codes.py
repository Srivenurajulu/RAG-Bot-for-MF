"""
Scheme codes (AMFI) for NAV fetch via MFapi.in.
Map: fund_name as in funds.json -> scheme_code (Regular Plan - Growth).
Using Regular Plan so NAV matches the AMC scheme page (which shows Regular by default).
Source: https://api.mfapi.in/mf/search?q=... (AMFI scheme codes).
"""
# fund_name (must match funds.json) -> AMFI scheme_code for Regular Plan - Growth
NAV_SCHEME_CODES = {
    "ICICI Prudential Large Cap Fund": 108466,       # (erstwhile Bluechip) - Growth
    "ICICI Prudential MidCap Fund": 102528,
    "ICICI Prudential ELSS Tax Saver Fund": 100354,
    "ICICI Prudential Multi Asset Fund": 101144,
    "ICICI Prudential Balanced Advantage Fund": 104685,
    "ICICI Prudential Energy Opportunities Fund": 152726,
    "ICICI Prudential Multicap Fund": 101228,
    "ICICI Prudential US Bluechip Equity Fund": 117620,
    "ICICI Prudential NASDAQ 100 Index Fund": 149218,
    "ICICI Prudential Smallcap Fund": 106823,
}

# MFapi.in base URL (no auth required)
NAV_API_BASE = "https://api.mfapi.in/mf"

# AMC scheme page URL for each fund — used as Source link when answering NAV-related questions
FUND_SCHEME_PAGE_URLS = {
    "ICICI Prudential Large Cap Fund": "https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-bluechip-fund/211",
    "ICICI Prudential MidCap Fund": "https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-midcap-fund/15",
    "ICICI Prudential ELSS Tax Saver Fund": "https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-elss-tax-saver-fund/2",
    "ICICI Prudential Multi Asset Fund": "https://www.icicipruamc.com/mutual-fund/hybrid-funds/icici-prudential-multi-asset-fund/55",
    "ICICI Prudential Balanced Advantage Fund": "https://www.icicipruamc.com/mutual-fund/hybrid-funds/icici-prudential-balanced-advantage-fund/202",
    "ICICI Prudential Energy Opportunities Fund": "https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-energy-opportunities-fund/1878",
    "ICICI Prudential Multicap Fund": "https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-multicap-fund/22",
    "ICICI Prudential US Bluechip Equity Fund": "https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-us-bluechip-equity-fund/437",
    "ICICI Prudential NASDAQ 100 Index Fund": "https://www.icicipruamc.com/mutual-fund/index-funds/icici-prudential-nasdaq-100-index-fund/1827",
    "ICICI Prudential Smallcap Fund": "https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-smallcap-fund/168",
}
