from token_balance_checker import TokenBalanceChecker
from eth_balance_checker import CryptoBalanceChecker

def main():
    token_checker = TokenBalanceChecker('config.json')
    token_balances, token_prices = token_checker.sum_token_balances_and_fetch_prices()
    
    crypto_checker = CryptoBalanceChecker('config.json')
    crypto_checker.process_wallets()

if __name__ == "__main__":
    main()