import configparser
import os
from kiteconnect import KiteConnect

def update_access_token_in_config(config_path, new_token):
    config = configparser.ConfigParser()
    config.read(config_path)
    config.set('zerodha', 'access_token', new_token)
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    print(f"Updated access_token in {config_path}")

def main():
    # Adjust the config path as needed
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config.conf")
    config = configparser.ConfigParser()
    config.read(config_path)
    api_key = config.get('zerodha', 'api_key').strip('"')
    api_secret = config.get('zerodha', 'api_secret').strip('"')

    print("Go to this URL and login to get your request_token:")
    print(f"https://kite.trade/connect/login?api_key={api_key}")

    request_token = input("Paste the request_token here: ").strip()
    kite = KiteConnect(api_key=api_key)
    try:
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]
        print(f"Your access_token is: {access_token}")
        update_access_token_in_config(config_path, access_token)
    except Exception as e:
        print("Error generating access token:", e)

if __name__ == "__main__":
    main()
