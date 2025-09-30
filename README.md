# Kite Dashboard - Options Trading Strategy System

A comprehensive Python-based trading system for Nifty and BankNifty options strategies using Zerodha Kite API. The system provides real-time market data processing, strategy implementation, and persistent trade tracking.

## Features

### Real-time Data Processing
- **WebSocket Integration**: Live market data streaming using KiteConnect WebSocket
- **Multi-instrument Support**: Nifty, BankNifty spot, futures, and options
- **Automatic Strike Selection**: Dynamic ATM (At-The-Money) strike detection
- **Data Persistence**: JSON-based storage with timestamp-aware duplicate prevention

### Trading Strategies
1. **ATM Straddle Sell**: Multi-leg option selling strategy with individual leg tracking
2. **Reversal at Key Zones**: Mean reversion strategy based on support/resistance levels
3. **Directional Breakout with OI**: Momentum strategy using open interest analysis
4. **Moving Average Strategy**: EMA-based trend following with volume confirmation

### Trade Management
- **Persistent State Tracking**: JSON-based trade state management across sessions
- **Multi-strategy Support**: Independent tracking for different strategy types
- **PnL Calculation**: Real-time profit/loss calculation for open positions
- **Duplicate Prevention**: Intelligent call logging to avoid repeated signals
- **Historical Performance**: Trade history and performance analytics

### Data Management
- **Structured Storage**: Organized data storage by date and instrument type
- **Historical Data Fetching**: Automatic historical data download for backtesting
- **Instrument Management**: Dynamic instrument token management and CSV updates
- **Configuration Management**: Centralized configuration via config files

## Project Structure

```
kite_dashboard/
├── config/
│   ├── config.conf              # Main configuration file
│   └── __init__.py
├── data/
│   ├── live/                    # Real-time market data
│   │   └── YYYY-MM-DD/         # Daily data folders
│   └── __init__.py
├── utils/
│   ├── config_loader.py         # Configuration management
│   ├── generate_access_token.py # Zerodha access token generation
│   ├── instrument_utils.py      # Instrument data handling
│   ├── kite_ws.py              # WebSocket implementation
│   ├── fetch_historical_data.py # Historical data fetching
│   └── __init__.py
├── resources/
│   ├── zerodha_instruments.csv  # Instrument master file
│   └── __init__.py
├── calls/                       # Strategy call logs
│   └── YYYY-MM-DD/
│       └── calls.json
├── trade/                       # Trade state tracking
│   └── YYYY-MM-DD/
│       └── trade_state.json
├── generate_recommendations.py  # Main strategy engine
├── test_kite_ws.py             # WebSocket testing
├── moving_average_strategy.py   # EMA strategy implementation
└── requirements.txt
```

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd kite_dashboard
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Zerodha API credentials**
   - Edit `config/config.conf`
   - Add your Zerodha API key, secret, and access token
   ```ini
   [zerodha]
   api_key = your_api_key
   api_secret = your_api_secret
   access_token = your_access_token
   ```

## Configuration

### Main Configuration (`config/config.conf`)

```ini
[zerodha]
api_key = your_api_key
api_secret = your_api_secret
access_token = your_access_token

[contracts]
nifty_lot_size = 75
banknifty_lot_size = 15
nifty_option_range = 1
banknifty_option_range = 1

[storage]
append_if_unique_timestamp = False

[settings]
from_date = 2019-01-01
to_date = 2025-09-29
base_history_path = /path/to/data/history
interval = day

[equities]
nse_index = nifty 50

[futures]
symbols = INFY24OCTFUT,RELIANCE24OCTFUT
```

## Usage

### 1. Generate Access Token
```bash
python utils/generate_access_token.py
```

### 2. Start Real-time Data Collection
```bash
python test_kite_ws.py
```

### 3. Run Strategy Engine
```bash
python generate_recommendations.py
```

### 4. Fetch Historical Data
```bash
python utils/fetch_historical_data.py
```

### 5. Run Moving Average Strategy
```bash
python moving_average_strategy.py
```

## Key Components

### WebSocket Data Handler (`utils/kite_ws.py`)
- Real-time tick processing
- Automatic option chain subscription
- JSON data persistence with timestamp validation
- Multi-instrument support (Nifty, BankNifty, VIX)

### Strategy Engine (`generate_recommendations.py`)
- Multiple strategy implementations
- Persistent trade state management
- Real-time PnL calculation
- Duplicate signal prevention
- Call logging and performance tracking

### Utility Functions
- **Config Loader**: Centralized configuration management
- **Instrument Utils**: Token mapping and instrument data handling
- **Historical Data**: Automated data fetching for backtesting

## Strategies Implemented

### 1. ATM Straddle Sell
- Sells both Call and Put options at ATM strike
- Multi-leg position tracking
- Individual leg PnL calculation
- Risk management based on spot movement

### 2. Reversal at Key Zones
- Mean reversion strategy
- Support/resistance level identification
- Volume confirmation
- State-based signal generation

### 3. Directional Breakout with OI
- Momentum-based strategy
- Open interest analysis
- Volume breakout confirmation
- Directional bias determination

### 4. Moving Average Strategy
- EMA crossover signals
- Volume confirmation
- Breakout percentage filters
- Forward performance validation

## Data Flow

1. **Real-time Data**: WebSocket → JSON files (by date/instrument)
2. **Strategy Processing**: JSON data → Strategy logic → Trade decisions
3. **State Management**: Trade decisions → State files → PnL tracking
4. **Performance Analytics**: Historical trades → Performance metrics

## Error Handling

- **JSON Corruption**: Automatic file repair and validation
- **Network Issues**: Reconnection logic for WebSocket
- **Data Validation**: Timestamp-based duplicate prevention
- **State Recovery**: Persistent state management across restarts

## File Naming Convention

- **Live Data**: `data/live/YYYY-MM-DD/{instrument}.json`
- **Trade State**: `trade/YYYY-MM-DD/trade_state.json`
- **Strategy Calls**: `calls/YYYY-MM-DD/calls.json`
- **Historical Data**: `data/history/{symbol}_{from}_{to}.csv`

## Dependencies

- **kiteconnect**: Zerodha API integration
- **pandas**: Data manipulation and analysis
- **requests**: HTTP requests for data fetching
- **nsetools**: NSE data and utilities
- **configparser**: Configuration file handling

## Notes

- Ensure proper API rate limits compliance
- Monitor data storage as files can grow large
- Regularly backup trade state files
- Test strategies with paper trading before live deployment
- Keep access tokens secure and rotate regularly

## Troubleshooting

### Common Issues

1. **JSON Decode Errors**: Usually due to incomplete file writes during market hours
   - Solution: Implement file locking or use atomic writes

2. **Access Token Expiry**: Tokens expire daily
   - Solution: Regenerate access token daily using `generate_access_token.py`

3. **Missing Data**: WebSocket disconnections during market hours
   - Solution: Implement reconnection logic and data gap filling

4. **High Memory Usage**: Large JSON files loaded into memory
   - Solution: Implement streaming JSON processing for large files

## License

This project is for educational and research purposes. Ensure compliance with your broker's API terms of service.

## Disclaimer

This software is for educational purposes only. Trading in financial markets involves risk. The authors are not responsible for any financial losses incurred through the use of this software. Always test strategies thoroughly before deploying with real money.
