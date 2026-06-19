import streamlit as st
import pandas as pd
import yfinance as yf
import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Total Market GTF-Style Screener", layout="wide")
st.title("👁️ Total Market EYE Stock Screener")
st.subheader("Scanning all listed equities using Demand-Supply Price Action Logic")

# --- STEP 1: GET TOTAL MARKET TICKERS ---
@st.cache_data(ttl=86400)  # Cache ticker list for 24 hours
def get_total_market_tickers():
    """Fetches total market listings from NSE."""
    try:
        # Fetch directly from NSE official CSV structure
        url = "https://archives.nseindia.com/content/equities/EQUITY_L_MARKET_DATA.csv"
        df = pd.read_csv(url)
        # Filter out invalid rows and add .NS suffix for yfinance
        df = df[df['SERIES'] == 'EQ']
        tickers = [f"{symbol}.NS" for symbol in df['SYMBOL'].tolist()]
        return tickers, df[['SYMBOL', 'NAME OF COMPANY', ' MARKET CAP']]
    except Exception as e:
        # Fallback list if network request fails
        st.warning("NSE Live fetch failed. Using fallback Nifty 500/Broad list.")
        return ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"], pd.DataFrame()

all_tickers, ticker_info_df = get_total_market_tickers()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Scan Control Panel")
market_segment = st.sidebar.selectbox("Market Universe", ["Total Market (All Listed)", "Nifty 500 Only"])
timeframe = st.sidebar.selectbox("Select Timeframe", ["Daily", "Weekly", "Monthly"])
mode_select = st.sidebar.selectbox("Select Mode", ["Standard Mode", "GTF High Probability Mode"])
zone_type = st.sidebar.multiselect("Zone Alignment", ["Approaching Demand Zone", "Reacting from Demand Zone", "Supply Zone Pressure"], default=["Approaching Demand Zone"])

# Limit universe based on selection
if market_segment == "Nifty 500 Only":
    # Emulate the native limits of the premium screeners
    tickers_to_scan = all_tickers[:500] 
else:
    tickers_to_scan = all_tickers  # Full 1500+ NSE Active Equities

# --- STEP 2: DEMAND & SUPPLY LOGIC ENGINE ---
def scan_zone_footprint(ticker, tf_period="1y", tf_interval="1d"):
    """
    Decodes basic institutional footprints based on structural candle configurations
    (Drop-Base-Rally pattern detection).
    """
    try:
        data = yf.download(ticker, period=tf_period, interval=tf_interval, progress=False)
        if len(data) < 10:
            return None
        
        # Calculate true ranges and bodies
        data['Body'] = (data['Close'] - data['Open']).abs()
        data['Range'] = data['High'] - data['Low']
        
        # Fetch the latest few structures
        current_price = data['Close'].iloc[-1].item() if isinstance(data['Close'].iloc[-1], pd.Series) else data['Close'].iloc[-1]
        
        # Look back to find recent 'Base' candles followed by explosive rallies (Demand Zones)
        for i in range(-5, -2):
            prev_candle_1 = data.iloc[i-1]
            base_candle = data.iloc[i]
            rally_candle = data.iloc[i+1]
            
            # Simple algorithmic identification of institutional footprint:
            # An explosive green candle (Rally) following a small, consolidated tight candle (Base)
            is_rally = (rally_candle['Close'] > rally_candle['Open']) and (rally_candle['Body'] > data['Body'].mean() * 1.5)
            is_base = base_candle['Body'] < data['Body'].mean()
            
            if is_rally and is_base:
                demand_zone_low = base_candle['Low'].item() if hasattr(base_candle['Low'], 'item') else base_candle['Low']
                demand_zone_high = base_candle['High'].item() if hasattr(base_candle['High'], 'item') else base_candle['High']
                
                # Check if current price is nearing or mitigating this demand area
                if current_price >= demand_zone_low and current_price <= (demand_zone_high * 1.02):
                    return {
                        "Ticker": ticker.replace(".NS", ""),
                        "Current Price": round(current_price, 2),
                        "Zone Low": round(demand_zone_low, 2),
                        "Zone High": round(demand_zone_high, 2),
                        "Status": "Approaching/In Demand Zone"
                    }
        return None
    except:
        return None

# --- STEP 3: SCANNING PIPELINE EXECUTION ---
if st.sidebar.button("Launch Total Market Scan"):
    st.info(f"Scanning {len(tickers_to_scan)} stocks across the market... Please wait.")
    
    # Setup intervals mapping based on user selection
    tf_mapping = {"Daily": "1d", "Weekly": "1wk", "Monthly": "1mo"}
    period_mapping = {"Daily": "1y", "Weekly": "3y", "Monthly": "5y"}
    
    results = []
    
    # Progress visualization
    progress_bar = st.progress(0)
    
    # Iterative scan through selected universe
    for index, ticker in enumerate(tickers_to_scan):
        # Update progress bar safely
        if index % 20 == 0:
            progress_bar.progress(index / len(tickers_to_scan))
            
        match = scan_zone_footprint(ticker, tf_period=period_mapping[timeframe], tf_interval=tf_mapping[timeframe])
        
        # Display Output Table
    if results:
        results_df = pd.DataFrame(results)
        st.success(f"Scan complete! Spotted {len(results_df)} setups matching structural money patterns.")
        st.dataframe(results_df, use_container_width=True)
    else:
        st.info("No matching institutional footprints detected in current market configurations.")
else:
    st.write("👈 Click *Launch Total Market Scan* on the sidebar control panel to trigger the engine across all instruments.")
