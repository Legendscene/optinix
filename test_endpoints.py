from app import app
test = app.test_client()
endpoints = [
    ('GET', '/api/system-info'),
    ('POST', '/api/optimize/cleanup'),
    ('POST', '/api/optimize/network'),
    ('POST', '/api/optimize/disk'),
    ('POST', '/api/optimize/performance'),
    ('POST', '/api/optimize/gaming'),
    ('POST', '/api/optimize/security'),
    ('POST', '/api/optimize/developer'),
    ('POST', '/api/optimize/services'),
    ('POST', '/api/optimize/overclock'),
    ('POST', '/api/optimize/all'),
    ('GET', '/api/registry/scan'),
    ('GET', '/api/tweaks/list'),
    ('GET', '/api/services'),
    ('GET', '/api/startup'),
    ('GET', '/api/game-mode/status'),
    ('GET', '/api/bios/info'),
    ('GET', '/api/debloat/categories'),
    ('POST', '/api/ram-boost'),
    ('GET', '/api/extreme/mode'),
    ('GET', '/api/security/check'),
    ('GET', '/api/drivers/scan'),
    ('GET', '/api/drivers/missing'),
    ('GET', '/api/network-priority/bufferbloat/presets'),
    ('POST', '/api/tweaks/apply'),
]
errors = []
for method, path in endpoints:
    try:
        if method == 'GET':
            r = test.get(path)
        else:
            r = test.post(path)
        status = 'OK' if r.status_code == 200 else 'ERR'
        data = r.get_json() or {}
        err = data.get('error', '') if isinstance(data, dict) else ''
        if err:
            errors.append(f'{status} {method} {path} -> {err[:100]}')
        else:
            pass
    except Exception as e:
        errors.append(f'EXCEPTION {method} {path} -> {e}')
if errors:
    for e in errors:
        print(e)
else:
    print('ALL OK')
