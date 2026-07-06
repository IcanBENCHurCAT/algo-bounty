with open('gateway/config.py', 'r') as f:
    content = f.read()

new_content = content.replace(
    '''    @property
    def DATABASE_URL(self) -> str:
        return self.get_secret("DATABASE_URL")''',
    '''    @property
    def DATABASE_URL(self) -> str:
        return self.get_secret("DATABASE_URL")

    @property
    def ESCROW_TEMPLATE_APP_ID(self) -> int:
        val = self.get_secret("ESCROW_TEMPLATE_APP_ID", "0")
        try:
            return int(val)
        except ValueError:
            return 0'''
)

with open('gateway/config.py', 'w') as f:
    f.write(new_content)
