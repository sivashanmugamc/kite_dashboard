import datetime
import os
import json

from kiteconnect import KiteTicker

from .config_loader import config
from .instrument_utils import (
    get_all_instruments,
    get_nifty_banknifty_tokens,
    get_atm_strike,
    get_expiry_by_instrument_token,
    get_option_tokens_for_atm_range,
    merge_instrument_and_tick,
)
API_KEY = config.get("zerodha", "api_key")
ACCESS_TOKEN = config.get("zerodha", "access_token")
banknifty_option_range = config.getint("contracts", "banknifty_option_range")
nifty_option_range = config.getint("contracts", "nifty_option_range")
append_if_unique = config.getboolean("storage", "append_if_unique_timestamp", fallback=False)

# Global tick store
latest_spots = {'NIFTY_SPOT': None, 'BANKNIFTY_SPOT': None}
latest_ticks_by_token = {}

# Flags to ensure options are subscribed only once
options_subscribed = {'NIFTY': False, 'BANKNIFTY': False}

# Output directory
today_str = datetime.date.today().isoformat()
LIVE_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data/live', today_str)
os.makedirs(LIVE_DATA_DIR, exist_ok=True)

# Load instrument data and token mappings
df = get_all_instruments()
tokens_dict = get_nifty_banknifty_tokens()

nifty_opts = {}
bn_opts = {}
def deep_serialize(obj):
    """
    Recursively convert all datetime/date objects in a dict/list to ISO strings for JSON.
    """
    if isinstance(obj, dict):
        return {k: deep_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [deep_serialize(i) for i in obj]
    elif isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    return obj


def write_json(filename, data):
    path = os.path.join(LIVE_DATA_DIR, filename)
    # If appending is disabled, overwrite the file directly
    if not append_if_unique:
        with open(path, 'w') as f:
            json.dump(deep_serialize(data), f, indent=2)
        print(f"✅ Overwrote {filename} (append disabled)")
        return

    # If appending to a list of dicts (e.g., options)
    if isinstance(data, list):
        existing = []
        if os.path.exists(path):
            with open(path, 'r') as f:
                try:
                    existing = json.load(f)
                except Exception:
                    existing = []
        # Only append new records with unique exchange_timestamp
        existing_timestamps = {item.get('exchange_timestamp') for item in existing if isinstance(item, dict)}
        new_records = [item for item in data if item.get('exchange_timestamp') not in existing_timestamps]
        all_data = existing + new_records
        with open(path, 'w') as f:
            json.dump(deep_serialize(all_data), f, indent=2)
        print(f"✅ Wrote {filename} with {len(new_records)} new record(s), {len(all_data)} total")
    elif isinstance(data, dict):
        # For dict, append only if exchange_timestamp is new
        existing = []
        if os.path.exists(path):
            with open(path, 'r') as f:
                try:
                    existing = json.load(f)
                except Exception:
                    existing = []
        if isinstance(existing, list):
            timestamps = {item.get('exchange_timestamp') for item in existing if isinstance(item, dict)}
            if data.get('exchange_timestamp') not in timestamps:
                existing.append(data)
                with open(path, 'w') as f:
                    json.dump(deep_serialize(existing), f, indent=2)
                print(f"✅ Appended {filename} with token {data.get('instrument_token', 'unknown')}")
            else:
                print(f"⚠️ Skipped {filename}: duplicate exchange_timestamp")
        else:
            with open(path, 'w') as f:
                json.dump(deep_serialize(data), f, indent=2)
            print(f"✅ Wrote {filename} with token {data.get('instrument_token', 'unknown')}")
    else:
        with open(path, 'w') as f:
            json.dump(deep_serialize(data), f, indent=2)
        print(f"✅ Wrote {filename}")

def on_ticks(ws, ticks):
    global nifty_opts, bn_opts
    print("✅ Received Ticks:")
    for tick in ticks:
        token = tick['instrument_token']
        latest_ticks_by_token[token] = tick
        enriched = merge_instrument_and_tick(df, tick)
        print(f"📈 Tick received for token {token} | Last Price: {tick['last_price']}")

        # Update spot prices
        if token == tokens_dict['NIFTY_SPOT']:
            latest_spots['NIFTY_SPOT'] = tick['last_price']
            write_json("nifty_spot.json", enriched)
        elif token == tokens_dict['BANKNIFTY_SPOT']:
            latest_spots['BANKNIFTY_SPOT'] = tick['last_price']
            write_json("banknifty_spot.json", enriched)
        elif token == tokens_dict['NIFTY_FUT']:
            write_json("nifty_future.json", enriched)
        elif token == tokens_dict['BANKNIFTY_FUT']:
            write_json("banknifty_future.json", enriched)
        elif token == tokens_dict['VIX']:
            write_json("india_vix.json", enriched)

        # Subscribe to NIFTY options
        if latest_spots['NIFTY_SPOT'] and not options_subscribed['NIFTY']:
            nifty_atm = get_atm_strike(latest_spots['NIFTY_SPOT'], 50)
            expiry = get_expiry_by_instrument_token(df, tokens_dict['NIFTY_OPT'])
            nifty_opts = get_option_tokens_for_atm_range(df, 'NIFTY', nifty_atm, 50, n=nifty_option_range, expiry=expiry)
            if nifty_opts:
                ws.subscribe(list(nifty_opts.values()))
                ws.set_mode("full", list(nifty_opts.values()))
                options_subscribed['NIFTY'] = True
                print("📌 Subscribed to NIFTY options.")

        # Subscribe to BANKNIFTY options
        if latest_spots['BANKNIFTY_SPOT'] and not options_subscribed['BANKNIFTY']:
            bn_atm = get_atm_strike(latest_spots['BANKNIFTY_SPOT'], 100)
            expiry = get_expiry_by_instrument_token(df, tokens_dict['BANKNIFTY_OPT'])
            bn_opts = get_option_tokens_for_atm_range(df, 'BANKNIFTY', bn_atm, 100, n=nifty_option_range, expiry=expiry)
            if bn_opts:
                ws.subscribe(list(bn_opts.values()))
                ws.set_mode("full", list(bn_opts.values()))
                options_subscribed['BANKNIFTY'] = True
                print("📌 Subscribed to BANKNIFTY options.")

        # Write NIFTY options data if subscribed
        if options_subscribed['NIFTY']:
            nifty_result = []
            for label, token in nifty_opts.items():
                tick = latest_ticks_by_token.get(token)
                if tick:
                    merged = merge_instrument_and_tick(df, tick)
                    if merged:
                        nifty_result.append(merged)
            if nifty_result:
                write_json("nifty_options.json", nifty_result)

        # Write BANKNIFTY options data if subscribed
        if options_subscribed['BANKNIFTY']:
            banknifty_result = []
            for label, token in bn_opts.items():
                tick = latest_ticks_by_token.get(token)
                if tick:
                    merged = merge_instrument_and_tick(df, tick)
                    if merged:
                        banknifty_result.append(merged)
            if banknifty_result:
                write_json("banknifty_options.json", banknifty_result)

def on_connect(ws, response=None):
    print("🔌 Connected to WebSocket")
    initial_tokens = [
        tokens_dict['NIFTY_SPOT'],
        tokens_dict['BANKNIFTY_SPOT'],
        tokens_dict['NIFTY_FUT'],
        tokens_dict['BANKNIFTY_FUT'],
        tokens_dict['VIX']
    ]
    ws.subscribe(initial_tokens)
    ws.set_mode("full", initial_tokens)

def start_ws():
    print(f"API_KEY: {API_KEY}, ACCESS_TOKEN: {ACCESS_TOKEN[:5]}... (truncated)")
    kws = KiteTicker(API_KEY, ACCESS_TOKEN)
    kws.on_ticks = on_ticks
    kws.on_connect = on_connect
    kws.connect(threaded=True)

def on_close(ws, code=None, reason=None):
    print(f"❌ WebSocket closed | Code: {code} | Reason: {reason}")

def on_error(ws, code=None, reason=None):
    print(f"⚠️ WebSocket error | Code: {code} | Reason: {reason}")
