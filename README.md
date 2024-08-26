# Ethereum and Token Balance Checker

This tool checks Ethereum and ERC-20 token balances across multiple wallets, fetches real-time price data, and generates detailed reports.

## Features

- Check Ethereum balances for multiple addresses
- Retrieve and filter ERC-20 token balances
- Fetch current token prices
- Calculate total value of holdings
- Generate CSV reports with balance and value information

## Prerequisites

- Python 3.7+
- pip (Python package manager)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/bojane/eth-token-balance-checker.git
   cd your-repo-name
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up your `config.json` file with your API keys and other configuration details.

## Usage

Run the main script:

```
python main.py
```

This will process the wallet addresses, fetch balances and prices, and generate CSV reports.

## Configuration

Edit `config.json` to set:

- API URLs
- API keys for Etherscan and CoinGecko
- Input filename with wallet addresses

## Output

The script generates two CSV files:
- `wallet_balances_YYYYMMDD_HHMMSS.csv`: Ethereum balances
- `token_data_YYYYMMDD_HHMMSS.csv`: Token balances and values

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[MIT License](LICENSE)
