with open('gateway/config.py', 'r') as f:
    content = f.read()

new_content = content.replace(
    '''    @property
    def SECRET_KEY(self) -> str:
        return self.get_secret("SECRET_KEY")''',
    '''    @property
    def SECRET_KEY(self) -> str:
        val = self.get_secret("SECRET_KEY")
        if self.ALGORAND_NETWORK in ("testnet", "mainnet") and not val:
            raise RuntimeError("SECRET_KEY must be set in testnet/mainnet")
        return val'''
)

new_content = new_content.replace(
    '''    @property
    def GITHUB_TOKEN(self) -> str:
        return self.get_secret("GITHUB_TOKEN")''',
    '''    @property
    def GITHUB_TOKEN(self) -> str:
        val = self.get_secret("GITHUB_TOKEN")
        if self.ALGORAND_NETWORK in ("testnet", "mainnet") and not val:
            raise RuntimeError("GITHUB_TOKEN must be set in testnet/mainnet")
        return val'''
)

new_content = new_content.replace(
    '''    @property
    def PLATFORM_PRIVATE_KEY(self) -> str:
        return self.get_secret("PLATFORM_PRIVATE_KEY")''',
    '''    @property
    def PLATFORM_PRIVATE_KEY(self) -> str:
        val = self.get_secret("PLATFORM_PRIVATE_KEY")
        if self.ALGORAND_NETWORK in ("testnet", "mainnet") and not val:
            raise RuntimeError("PLATFORM_PRIVATE_KEY must be set in testnet/mainnet")
        return val'''
)

with open('gateway/config.py', 'w') as f:
    f.write(new_content)
