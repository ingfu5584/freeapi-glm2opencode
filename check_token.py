import json
from auth import is_token_valid, decode_jwt_payload

with open('token_store.json', 'r', encoding='utf-8') as f:
    store = json.load(f)

auth = store.get('captured_authorization', '')
print(f'Has auth: {bool(auth)}')

if auth:
    payload = decode_jwt_payload(auth)
    print(f'JWT keys: {list(payload.keys())}')
    guest = payload.get('is_guest')
    print(f'is_guest: {guest}')
    print(f'exp: {payload.get(\"exp\")}')

print(f'is_token_valid: {is_token_valid()}')
