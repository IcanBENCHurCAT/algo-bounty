with open('gateway/indexer.py', 'r') as f:
    content = f.read()

new_content = content.replace(
    'from .algod_client import get_indexer_client, get_algod_client',
    'from .algod_client import get_indexer_client, get_algod_client\nfrom .config import settings'
)

new_content = new_content.replace(
    'apps_response = client.search_applications(limit=100)',
    '''
        # Use indexer to get application data in bulk, avoiding N+1 algod calls
        search_kwargs = {"limit": 100}
        template_app_id = settings.ESCROW_TEMPLATE_APP_ID
        if template_app_id > 0:
            search_kwargs["application_id"] = template_app_id
        apps_response = client.search_applications(**search_kwargs)'''
)

new_content = new_content.replace(
    '''        # Use indexer to get application data in bulk, avoiding N+1 algod calls

        # Use indexer to get application data in bulk, avoiding N+1 algod calls
        search_kwargs = {"limit": 100}''',
    '''        # Use indexer to get application data in bulk, avoiding N+1 algod calls
        search_kwargs = {"limit": 100}'''
)

with open('gateway/indexer.py', 'w') as f:
    f.write(new_content)
