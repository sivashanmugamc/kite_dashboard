import configparser
import datetime
import os

from instrument_utils import get_instrument_token, get_all_instruments
from kiteconnect import KiteConnect
from nsetools import Nse
import pandas as pd

from utils.config_loader import config


def get_symbols_from_index(index_name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    index_map = {
        "nifty 50": os.path.join(base_dir, "..", "resources", "nifty_50.csv"),
        "nifty 100": os.path.join(base_dir, "..", "resources", "nifty_100.csv"),
        "nifty 200": os.path.join(base_dir, "..", "resources", "nifty_200.csv"),
        "nifty 500": os.path.join(base_dir, "..", "resources", "nifty_500.csv")
    }
    path = index_map.get(index_name.lower())
    print("Path:", path)
    print("Exists:", os.path.exists(path))
    print("Absolute path:", os.path.abspath(path))
    print("Directory listing:", os.listdir(os.path.dirname(path)))
    if path and os.path.exists(path):
        df = pd.read_csv(path)  # Remove delimiter for auto-detection
        print("Columns in CSV:", df.columns.tolist())
        # Adjust the column name below if needed
        return df["Symbol"].dropna().tolist()
    return []

def fetch_data(symbol, token, kite, start_date, end_date, interval, continuous):
    data = kite.historical_data(
        instrument_token=token,
        from_date=start_date,
        to_date=end_date,
        interval=interval,
        continuous=continuous,
        oi=False
    )
    return pd.DataFrame(data)

def fetch_in_batches(symbol, token, kite, from_date, to_date, interval, continuous=False, max_days=2000):
    results = []
    current_start = from_date
    while current_start <= to_date:
        current_end = min(current_start + datetime.timedelta(days=max_days-1), to_date)
        batch_df = fetch_data(symbol, token, kite, current_start, current_end, interval, continuous)
        results.append(batch_df)
        current_start = current_end + datetime.timedelta(days=1)
    if results:
        return pd.concat(results, ignore_index=True)
    return pd.DataFrame()

def fetch_historical_data(symbols, exchange, instrument_type, kite, instruments_df, from_date, to_date, interval, continuous=False):
    from_date_dt = datetime.datetime.strptime(from_date, "%Y-%m-%d").date()
    to_date_dt = datetime.datetime.strptime(to_date, "%Y-%m-%d").date()
    # Use absolute output directory
    output_dir = os.path.join("/Users/CHIDASX1/Downloads/kite_dashboard/data/history", f"{from_date}_{to_date}")
    os.makedirs(output_dir, exist_ok=True)
    for symbol in symbols:
        token = get_instrument_token(symbol, instrument_type=instrument_type)
        if token:
            try:
                df = fetch_in_batches(symbol, token, kite, from_date_dt, to_date_dt, interval, continuous)
                out_path = os.path.join(output_dir, f"{symbol}_historical.csv")
                df.to_csv(out_path, index=False)
                print(f"✅ Saved historical data for {symbol} to {out_path}")
            except Exception as e:
                print(f"❌ Failed to fetch data for {symbol}: {e}")
        else:
            print(f"⚠️ Instrument token not found for {symbol} in {exchange}")

def main():

    # Zerodha credentials
    api_key = config.get("zerodha","api_key")
    access_token = config.get("zerodha","access_token")

    # Historical data parameters
    from_date = config.get("settings","from_date")
    to_date = config.get("settings","to_date")
    interval = config.get("settings","interval")

    # Get equity symbols from NSE index
    nse_index = config.get("equities","nse_index")

    equity_symbols = get_symbols_from_index(nse_index)
    print("Equity symbols:", equity_symbols)
    futures_symbols = [s.strip() for s in config["futures"]["symbols"].split(",")]

    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)

    instruments_df = get_all_instruments()
    fetch_historical_data(equity_symbols, "NSE", "EQ", kite, instruments_df, from_date, to_date, interval)
    # fetch_historical_data(futures_symbols, "NFO", "FUT", kite, instruments_df, from_date, to_date, interval,
    #                       continuous=True)


if __name__ == "__main__":
    main()
