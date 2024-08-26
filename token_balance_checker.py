import pandas as pd
import requests
import re
import time
import json
from datetime import datetime

class TokenBalanceChecker:
    def __init__(self, config_file):
        with open(config_file, 'r') as config_file:
            config = json.load(config_file)
        self.api_url = config['api_url']
        self.api_key = config['api_key']
        self.coingecko_api_key = config['coingecko_api_key']
        self.filename = config['filename']
        self.current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_filename = f"token_data_{self.current_time}.csv"

    def get_token_price(self, contract_address, remaining_calls):
        url = f"https://api.coingecko.com/api/v3/simple/token_price/ethereum?contract_addresses={contract_address}&vs_currencies=usd&x-api-key={self.coingecko_api_key}"
        max_retries = 5
        retry_delay = 65
        print(f"Fetching price for {contract_address} (Remaining calls: {remaining_calls})")

        for attempt in range(max_retries):
            response = requests.get(url)
            print(f"Attempt {attempt + 1} for price: HTTP status {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                return data.get(contract_address, {}).get('usd', "Price data not available")
            elif response.status_code == 429:
                print(f"Rate limit hit, sleeping for {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                break

        return "API request failed after retries"

    def get_token_balances(self, address):
        params = {
            'module': 'account',
            'action': 'tokentx',
            'address': address,
            'startblock': 0,
            'endblock': 999999999,
            'sort': 'asc',
            'apikey': self.api_key
        }
        print(f"Requesting token balances for {address}")
        response = requests.get(self.api_url, params=params)
        data = response.json()
        if data.get('status') != '1' or 'result' not in data:
            print(f"API error for address {address}: {data.get('result', 'No error message available')}")
            return []
        return data['result']

    def filter_tokens(self, tokens, address):
        filtered = {}
        max_length = 50
        pattern = r'\bhttps?://\S+|\bwww\.[\w-]+\.\w+\b|\b[\w-]+\.\w+\b|visit\b|claim\b|reward\b'
        print("Filtering tokens...")

        for token in tokens:
            token_name = token.get('tokenName', '')
            token_symbol = token.get('tokenSymbol', '')
            contract_address = token.get('contractAddress', '')
            token_value = int(token.get('value', 0)) / (10 ** int(token.get('tokenDecimal', 0)))
            
            if not re.search(pattern, token_name, re.I) and len(token_name) <= max_length:
                key = f"{token_symbol} ({token_name})"
                if key not in filtered:
                    filtered[key] = {'value': 0, 'contract_address': contract_address, 'wallet_addresses': {}}
                
                if token['to'].lower() == address.lower():
                    filtered[key]['value'] += token_value
                elif token['from'].lower() == address.lower():
                    filtered[key]['value'] -= token_value
                
                filtered[key]['wallet_addresses'][address.lower()] = filtered[key]['value']
                print(f"Token {key} updated with balance: {filtered[key]['value']}")
            else:
                reason = "unwanted content" if re.search(pattern, token_name, re.I) else "excessive length"
                print(f"Token {token_name} filtered out due to {reason}.")

        return filtered

    @staticmethod
    def is_valid_eth_address(address):
        return address.startswith('0x') and len(address) == 42

    def sum_token_balances_and_fetch_prices(self):
        df = pd.read_csv(self.filename)
        print(f"Loaded {len(df)} addresses from CSV.")
        total_balances = {}
        unique_tokens = {}
        data_list = []
        all_filtered_tokens = {}

        for address in df['wallet_address']:
            if not self.is_valid_eth_address(address):
                print(f"Skipping invalid address: {address}")
                continue
            
            tokens = self.get_token_balances(address)
            filtered = self.filter_tokens(tokens, address)

            for token, info in filtered.items():
                if token not in total_balances:
                    total_balances[token] = 0
                    all_filtered_tokens[token] = {'wallet_addresses': {}}
                total_balances[token] += info['value']
                unique_tokens[token] = info['contract_address']
                all_filtered_tokens[token]['wallet_addresses'].update(info['wallet_addresses'])
                print(f"Added/Updated balance for {token}, new total: {total_balances[token]}")

        # Filter out tokens with a total balance less than 0.01
        initial_token_count = len(total_balances)
        filtered_balances = {token: balance for token, balance in total_balances.items() if balance >= 0.01}
        filtered_token_count = initial_token_count - len(filtered_balances)
        print(f"Filtered out {filtered_token_count} tokens with a balance < 0.01")
        
        filtered_unique_tokens = {token: addr for token, addr in unique_tokens.items() if token in filtered_balances}
        
        remaining_calls = len(filtered_unique_tokens)
        total_prices = {}
        for token, addr in filtered_unique_tokens.items():
            total_prices[token] = self.get_token_price(addr, remaining_calls)
            remaining_calls -= 1
        print("Completed fetching prices for all tokens.")

        for token, balance in filtered_balances.items():
            contract_address = unique_tokens[token]
            price_info = total_prices.get(token, "Price data not available")
            total_value = None
            try:
                if price_info not in ["Price data not available", "API request failed after retries"]:
                    price = float(price_info)
                    total_value = int(balance * price)  # Remove decimals by converting to integer
            except ValueError:
                price = price_info
                total_value = "Error in price conversion"

            # Collect wallet addresses that hold more than 0.01 of this token
            wallet_addresses = ', '.join([addr for addr, bal in all_filtered_tokens[token]['wallet_addresses'].items() if bal > 0.01])
            
            data_list.append({
                "Token": token,
                "Balance": balance,
                "Price": price_info,
                "Total Value": total_value,
                "Wallet Addresses": wallet_addresses,
                "Contract Address": contract_address
            })

        result_df = pd.DataFrame(data_list)
        result_df = result_df[(result_df['Price'] != "Price data not available") & (result_df['Total Value'] >= 10)]

        # Sort the DataFrame by "Total Value" in descending order
        result_df = result_df.sort_values(by="Total Value", ascending=False)

        # Add the total row for "Total Value"
        total_value_sum = result_df["Total Value"].sum()
        total_row = pd.DataFrame([{"Token": "Total", "Balance": "", "Price": "", "Total Value": total_value_sum, "Wallet Addresses": "", "Contract Address": ""}])
        result_df = pd.concat([result_df, total_row], ignore_index=True)

        # Add the date and time to the last row
        timestamp_row = pd.DataFrame([{"Token": "Timestamp", "Balance": "", "Price": "", "Total Value": self.current_time, "Wallet Addresses": "", "Contract Address": ""}])
        result_df = pd.concat([result_df, timestamp_row], ignore_index=True)

        result_df.to_csv(self.output_filename, index=False)
        print(f"Data saved to {self.output_filename}")
        return filtered_balances, total_prices

# Example usage:
if __name__ == "__main__":
    checker = TokenBalanceChecker('config.json')
    checker.sum_token_balances_and_fetch_prices()
