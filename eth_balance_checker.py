import pandas as pd
import requests
import json
import re
import time
from datetime import datetime

class CryptoBalanceChecker:
    def __init__(self, config_file):
        with open(config_file, 'r') as config_file:
            config = json.load(config_file)
        self.api_url = config['api_url']
        self.api_key = config['api_key']
        self.coingecko_api_key = config['coingecko_api_key']
        self.input_filename = config['filename']
        self.current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_filename = f"wallet_balances_{self.current_time}.csv"

    @staticmethod
    def is_valid_ethereum_address(address):
        """
        Validate the format of an Ethereum address.

        :param address: str, Ethereum wallet address
        :return: bool, True if the address is valid, False otherwise
        """
        if re.match(r'^0x[a-fA-F0-9]{40}$', address):
            return True
        return False

    def get_eth_balance(self, wallet_address):
        """
        Retrieve the Ethereum balance for a given wallet address using Etherscan's API.

        :param wallet_address: str, Ethereum wallet address
        :return: float, Ethereum balance in Ether
        """
        endpoint = f"{self.api_url}?module=account&action=balance&address={wallet_address}&tag=latest&apikey={self.api_key}"
        response = requests.get(endpoint)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == '1':
                balance_wei = int(data['result'])
                balance_ether = balance_wei / 10**18
                return balance_ether
            else:
                raise ValueError(f"Error from Etherscan API: {data['message']} - {data['result']}")
        else:
            raise Exception(f"Failed to retrieve data: {response.status_code}")

    def get_eth_price(self):
        """
        Retrieve the current price of Ethereum using the CoinGecko API, with rate limit handling.

        :return: float, current price of Ethereum in USD
        """
        coingecko_url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        retries = 5
        delay = 62
        for attempt in range(retries):
            try:
                response = requests.get(coingecko_url)
                if response.status_code == 200:
                    data = response.json()
                    eth_price = data['ethereum']['usd']
                    return eth_price
                elif response.status_code == 429:
                    print(f"Rate limit exceeded. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise Exception(f"Failed to retrieve Ethereum price: {response.status_code}")
            except requests.RequestException as e:
                print(f"Request error: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2
        raise Exception("Failed to retrieve Ethereum price after multiple attempts")

    def process_wallets(self):
        """
        Process the wallets and save the results to a CSV file.
        """
        wallet_df = pd.read_csv(self.input_filename)
        wallet_balances = []
        print("Starting to retrieve balances for wallet addresses...\n")
        eth_price = self.get_eth_price()
        print(f"Current Ethereum price: ${eth_price:.2f} USD\n")
        for i, row in wallet_df.iterrows():
            address = row['wallet_address']
            hardwarewallet = row['hardwarewallet']
            print(f"Processing {i+1}/{len(wallet_df)}: {address}")
            if not self.is_valid_ethereum_address(address):
                print(f"Invalid Ethereum address: {address}")
                wallet_balances.append({"wallet_address": address, "hardwarewallet": hardwarewallet, "balance_ether": None, "value_usd": None})
                continue
            try:
                balance = self.get_eth_balance(address)
                value_usd = balance * eth_price
                print(f"Balance for {address}: {balance} Ether, Value: ${value_usd:.2f} USD")
                wallet_balances.append({"wallet_address": address, "hardwarewallet": hardwarewallet, "balance_ether": balance, "value_usd": value_usd})
            except ValueError as ve:
                print(f"Error retrieving balance for {address}: {ve}")
                wallet_balances.append({"wallet_address": address, "hardwarewallet": hardwarewallet, "balance_ether": None, "value_usd": None})
            except Exception as e:
                print(f"Unexpected error for {address}: {e}")
                wallet_balances.append({"wallet_address": address, "hardwarewallet": hardwarewallet, "balance_ether": None, "value_usd": None})
        balance_df = pd.DataFrame(wallet_balances)
        total_balance = balance_df['balance_ether'].sum()
        total_value = balance_df['value_usd'].sum()
        summary_row = pd.DataFrame([{"wallet_address": "Total", "hardwarewallet": "", "balance_ether": total_balance, "value_usd": total_value}])
        empty_row = pd.DataFrame([{"wallet_address": "", "hardwarewallet": "", "balance_ether": None, "value_usd": None}])
        price_row = pd.DataFrame([{"wallet_address": "Ethereum Price", "hardwarewallet": "", "balance_ether": None, "value_usd": eth_price}])
        timestamp_row = pd.DataFrame([{"wallet_address": "Timestamp", "hardwarewallet": "", "balance_ether": None, "value_usd": self.current_time}])
        balance_df = pd.concat([balance_df, summary_row], ignore_index=True)
        balance_df = pd.concat([balance_df, empty_row], ignore_index=True)
        balance_df = pd.concat([balance_df, price_row], ignore_index=True)
        balance_df = pd.concat([balance_df, timestamp_row], ignore_index=True)
        balance_df.to_csv(self.output_filename, index=False)
        print(f"\nData saved to {self.output_filename}")

# Example usage:
if __name__ == "__main__":
    checker = CryptoBalanceChecker('config.json')
    checker.process_wallets()
