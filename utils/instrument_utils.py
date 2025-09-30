import json
import os
import requests
import pandas as pd

ZERODHA_INSTRUMENTS_URL = "https://api.kite.trade/instruments"
INSTRUMENTS_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "resources", "zerodha_instruments.csv")


def download_instruments_csv(force=False):
    resources_dir = os.path.dirname(INSTRUMENTS_CSV_PATH)
    os.makedirs(resources_dir, exist_ok=True)
    if not os.path.exists(INSTRUMENTS_CSV_PATH) or force:
        r = requests.get(ZERODHA_INSTRUMENTS_URL)
        # Check for successful response and CSV content
        if "text/csv" in r.headers.get("Content-Type", ""):
            with open(INSTRUMENTS_CSV_PATH, "wb") as f:
                f.write(r.content)
        else:
            print("Failed to download CSV. Response was:")
            print(r.text)
            raise Exception("Instrument CSV download failed.")
    return INSTRUMENTS_CSV_PATH


def get_instrument_token(symbol, segment="NSE", instrument_type="EQ"):
    """
    symbol: 'NIFTY', 'BANKNIFTY'
    segment: 'NSE', 'NFO', etc.
    instrument_type: 'EQ', 'FUT', 'OPT'
    """
    csv_path = download_instruments_csv()
    df = pd.read_csv(csv_path)

    if instrument_type == "EQ":
        row = df[(df['tradingsymbol'] == symbol) & (df['segment'] == segment ) & (df['instrument_type'] == instrument_type)]
    elif instrument_type == "FUT":
        row = df[(df['tradingsymbol'].str.startswith(symbol)) & (df['segment'].str.startswith("NFO-FUT"))]
    elif instrument_type == "OPT":
        row = df[(df['name'].str.startswith(symbol)) & (df['segment'].str.startswith("NFO-OPT"))]
    else:
        return None

    if not row.empty:
        return row.iloc[0]['instrument_token']
    return None


def get_all_instruments(force_download=False):
    """
    Returns the entire Zerodha instruments file as a pandas DataFrame.
    Set force_download=True to refresh the file from Zerodha.
    """
    csv_path = download_instruments_csv(force=force_download)
    df = pd.read_csv(csv_path)
    return df

def get_index_token(symbol):
    """
    Returns the instrument token for a given index symbol (e.g., 'NIFTY 50', 'NIFTY BANK', 'INDIA VIX')
    """
    csv_path = download_instruments_csv()
    df = pd.read_csv(csv_path)
    row = df[(df['tradingsymbol'] == symbol) & (df['segment'] == 'INDICES')]
    if not row.empty:
        return int(row.iloc[0]['instrument_token'])
    return None

def get_nifty_banknifty_tokens():
    """
    Returns a dict of live instrument tokens for NIFTY and BANKNIFTY spot, futures, options, and INDIA VIX.
    """
    tokens = {}
    # Spot indices
    tokens['NIFTY_SPOT'] = get_index_token('NIFTY 50')
    tokens['BANKNIFTY_SPOT'] = get_index_token('NIFTY BANK')
    tokens['VIX'] = get_index_token('INDIA VIX')
    # Futures (current month by default)
    tokens['NIFTY_FUT'] = get_instrument_token('NIFTY', 'NFO', 'FUT')
    tokens['BANKNIFTY_FUT'] = get_instrument_token('BANKNIFTY', 'NFO', 'FUT')
    # Options (gets one example token; for full coverage, add strike/expiry logic)
    tokens['NIFTY_OPT'] = get_instrument_token('NIFTY', 'NFO', 'OPT')
    tokens['BANKNIFTY_OPT'] = get_instrument_token('BANKNIFTY', 'NFO', 'OPT')
    # Remove any None values and ensure Python int type
    return {k: int(v) for k, v in tokens.items() if v is not None}

def get_expiry_by_instrument_token(df, instrument_token):
    """
    Returns the expiry date (as string) for the given instrument_token from the instruments DataFrame.
    """
    row = df[df['instrument_token'] == instrument_token]
    if not row.empty:
        return row.iloc[0]['expiry']
    return None

def get_atm_strike(spot, step):
    return int(round(spot / step) * step)

def get_option_tokens_for_atm_range(df, symbol, atm, step, n=5, expiry=None):
    """
    Returns instrument tokens for ATM±n strikes for given symbol.
    symbol: 'NIFTY' or 'BANKNIFTY'
    atm: ATM strike (int)
    step: strike step (50 for NIFTY, 100 for BANKNIFTY)
    n: range (number of strike steps above/below ATM)
    expiry: Optional, expiry date as 'YYYY-MM-DD'
    Returns: dict {(strike, option_type): instrument_token}
    """
    strikes = [atm + i * step for i in range(-n, n + 1)]
    tokens = {}
    for strike in strikes:
        for opt_type in ['CE', 'PE']:
            cond = (
                    (df['name'] == symbol) &
                    (df['strike'] == strike) &
                    (df['instrument_type'] == opt_type) &  # Use 'CE'/'PE' for option type!
                    (df['segment'] == 'NFO-OPT')
            )
            if expiry:
                cond = cond & (df['expiry'] == expiry)
            row = df[cond]
            if not row.empty:
                chosen = row.iloc[0]
                tokens[(strike, opt_type)] = int(chosen['instrument_token'])
    return tokens

def lookup_instrument_details(df, instrument_token):
    """
    Returns a dict with all relevant fields for the given instrument_token.
    """
    row = df[df['instrument_token'] == instrument_token]
    if not row.empty:
        r = row.iloc[0]
        return {
            'instrument_token': int(r['instrument_token']),
            'tradingsymbol': r['tradingsymbol'],
            'strike': float(r.get('strike', 0.0)),
            'expiry': str(r.get('expiry', '')),
            'instrument_type': r['instrument_type'],
            'segment': r['segment']
        }
    return None

def merge_instrument_and_tick(df, tick):
    """
    Merge all instrument info from df and ALL fields from the tick dict.
    """
    details = lookup_instrument_details(df, tick['instrument_token'])
    if details:
        # Add ALL fields from tick (overriding any duplicates from details)
        details.update(tick)
    return details


def write_instruments_to_json(df, tokens, filename):
    data = []
    # Load existing files if exist
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    existing_tokens = {item['instrument_token'] for item in data}
    for token in tokens:
        details = lookup_instrument_details(df, token)
        if details and details['instrument_token'] not in existing_tokens:
            data.append(details)
            existing_tokens.add(details['instrument_token'])
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {len(data)} instruments to {filename}")
