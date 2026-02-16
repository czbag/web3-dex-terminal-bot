from eth_account import Account


def wallet_name_check(name: str) -> str:
    if len(name) in range(11):
        return name
    
    raise ValueError

def private_key_check(private_key: str) -> str:
    try:
        if not private_key.startswith("0x"):
            private_key = f"0x{private_key}"
        Account.from_key(private_key)
        return private_key
    except Exception:
        raise ValueError

