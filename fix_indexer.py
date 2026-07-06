with open('gateway/indexer.py', 'r') as f:
    content = f.read()

# I noticed there was a leftover line in my replace from before:
# The original code might have had an issue with multiple search_kwargs replacements

content = content.replace(
'''    try:
        # Use indexer to get application data in bulk, avoiding N+1 algod calls
        search_kwargs = {"limit": 100}
        template_app_id = settings.ESCROW_TEMPLATE_APP_ID
        if template_app_id > 0:
            search_kwargs["application_id"] = template_app_id

        # Use indexer to get application data in bulk, avoiding N+1 algod calls
        search_kwargs = {"limit": 100}
        template_app_id = settings.ESCROW_TEMPLATE_APP_ID
        if template_app_id > 0:
            search_kwargs["application_id"] = template_app_id
        apps_response = client.search_applications(**search_kwargs)''',
'''    try:
        # Use indexer to get application data in bulk, avoiding N+1 algod calls
        search_kwargs = {"limit": 100}
        template_app_id = settings.ESCROW_TEMPLATE_APP_ID
        if template_app_id > 0:
            search_kwargs["application_id"] = template_app_id
        apps_response = client.search_applications(**search_kwargs)'''
)

with open('gateway/indexer.py', 'w') as f:
    f.write(content)
