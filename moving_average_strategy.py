import os
import pandas as pd
import configparser
from glob import glob

def read_config(config_path='config/config.conf'):
    config = configparser.ConfigParser()
    config.read(config_path)
    from_date = config['settings']['from_date']
    to_date = config['settings']['to_date']
    base_history_path = config['settings']['base_history_path']
    return from_date, to_date, base_history_path

def recent_ema_crosses(df, lookback=50, vol_window=20, min_vol_mult=1.2, min_breakout_pct=0.005):
    df = df.copy()
    df['EMA50'] = df['close'].ewm(span=lookback, adjust=False).mean()
    df['prev_close'] = df['close'].shift(1)
    df['prev_ema'] = df['EMA50'].shift(1)
    df['vol_sma'] = df['volume'].rolling(window=vol_window).mean()
    recent = df.reset_index()  # Use all rows
    crosses = []
    for idx, row in recent.iterrows():
        if idx == 0 or idx + 5 >= len(recent):
            continue
        prev = recent.loc[idx-1]
        next_close_1d = recent.loc[idx+1, 'close']
        next_close_1w = recent.loc[idx+5, 'close']
        vol_ok = row['volume'] > min_vol_mult * row['vol_sma']
        breakout = abs(row['close'] - row['EMA50']) / row['EMA50'] > min_breakout_pct
        if (prev['prev_close'] > prev['prev_ema'] and row['close'] < row['EMA50'] and breakout and vol_ok):
            pl_1d = row['close'] - next_close_1d
            pl_1w = row['close'] - next_close_1w
            crosses.append({
                'date': row['date'],
                'type': 'Support',
                'close': row['close'],
                'ema50': row['EMA50'],
                'volume': row['volume'],
                'vol_sma': row['vol_sma'],
                'next_close': next_close_1d,
                'pl_1d': pl_1d,
                'pl_1d_result': "Profit" if pl_1d > 0 else "Loss",
                'next_close_1w': next_close_1w,
                'pl_1w': pl_1w,
                'pl_1w_result': "Profit" if pl_1w > 0 else "Loss"
            })
        if (prev['prev_close'] < prev['prev_ema'] and row['close'] > row['EMA50'] and breakout and vol_ok):
            pl_1d = next_close_1d - row['close']
            pl_1w = next_close_1w - row['close']
            crosses.append({
                'date': row['date'],
                'type': 'Resistance',
                'close': row['close'],
                'ema50': row['EMA50'],
                'volume': row['volume'],
                'vol_sma': row['vol_sma'],
                'next_close': next_close_1d,
                'pl_1d': pl_1d,
                'pl_1d_result': "Profit" if pl_1d > 0 else "Loss",
                'next_close_1w': next_close_1w,
                'pl_1w': pl_1w,
                'pl_1w_result': "Profit" if pl_1w > 0 else "Loss"
            })
    return pd.DataFrame(crosses)


def main():
    from_date, to_date, base_history_path = read_config()
    folder = os.path.join(base_history_path, f"{from_date}_{to_date}")
    csv_files = glob(os.path.join(folder, "*_historical.csv"))
    recent_crosses_all = []

    os.makedirs('results', exist_ok=True)

    for file in csv_files:
        symbol = os.path.basename(file).replace('_historical.csv', '')
        symbol_dir = os.path.join('results', symbol)
        os.makedirs(symbol_dir, exist_ok=True)

        df = pd.read_csv(file)
        if 'date' not in df.columns:
            continue
        df = df.sort_values('date').reset_index(drop=True)

        # Save full EMA50 history for this stock
        df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()
        ema_out = df[['date', 'close', 'EMA50']]
        ema_out.to_csv(os.path.join(symbol_dir, 'ema50_history.csv'), index=False)

        # For breaks_analysis.csv, use all data
        full_crosses_df = recent_ema_crosses(df)
        if not full_crosses_df.empty:
            full_crosses_df['symbol'] = symbol
            full_crosses_df.to_csv(os.path.join(symbol_dir, 'breakout_analysis.csv'), index=False)

        # For summary.txt, use all data
        if not full_crosses_df.empty:
            total = len(full_crosses_df)
            support = full_crosses_df[full_crosses_df['type'] == 'Support']
            resistance = full_crosses_df[full_crosses_df['type'] == 'Resistance']
            profit_1d = (full_crosses_df['pl_1d_result'] == 'Profit').sum()
            profit_1w = (full_crosses_df['pl_1w_result'] == 'Profit').sum()
            summary = [
                f"Symbol: {symbol}",
                f"Total crosses: {total}",
                f"Support crosses: {len(support)}",
                f"Resistance crosses: {len(resistance)}",
                f"1D Profit: {profit_1d} / {total} ({profit_1d / total:.2%})",
                f"1W Profit: {profit_1w} / {total} ({profit_1w / total:.2%})"
            ]
            with open(os.path.join(symbol_dir, 'summary.txt'), 'w') as f:
                f.write('\n'.join(summary))

        # For global recent crosses, use only last 50 days
        crosses_df = recent_ema_crosses(df, lookback=50)
        crosses_list = crosses_df.to_dict('records')
        for c in crosses_list:
            c['symbol'] = symbol
            recent_crosses_all.append(c)

    # Save all recent crosses to a summary CSV with all columns
    if recent_crosses_all:
        out_df = pd.DataFrame(recent_crosses_all)
        out_df = out_df[['symbol', 'date', 'type', 'close', 'ema50', 'next_close', 'pl_1d', 'pl_1d_result',
                         'next_close_1w', 'pl_1w', 'pl_1w_result']]
        out_df.to_csv('results/recent_50day_ema_crosses.csv', index=False)
        print("Recent 50-day EMA crosses saved to `results/recent_50day_ema_crosses.csv`.")

        # Global summary
        total = len(out_df)
        support = out_df[out_df['type'] == 'Support']
        resistance = out_df[out_df['type'] == 'Resistance']
        profit_1d = (out_df['pl_1d_result'] == 'Profit').sum()
        profit_1w = (out_df['pl_1w_result'] == 'Profit').sum()
        summary = [
            f"Total crosses: {total}",
            f"Support crosses: {len(support)}",
            f"Resistance crosses: {len(resistance)}",
            f"1D Profit: {profit_1d} / {total} ({profit_1d / total:.2%})",
            f"1W Profit: {profit_1w} / {total} ({profit_1w / total:.2%})"
        ]
        with open('results/summary.txt', 'w') as f:
            f.write('\n'.join(summary))
        print("Summary saved to `results/summary.txt`.")
    else:
        print("No recent EMA crosses found in the last 50 days.")



if __name__ == "__main__":
    main()
