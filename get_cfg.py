import urllib.request, ssl, json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request(
    'https://127.0.0.1:55112/exa.language_server_pb.LanguageServerService/GetCascadeTrajectory',
    data=json.dumps({'cascadeId': '63491d75-f037-436d-9859-d347c40dd7a1'}).encode('utf-8'),
    headers={
        'x-codeium-csrf-token': '7037d5ee-1ecd-4d7b-9aa5-fc90c52d072f',
        'Content-Type': 'application/json'
    }
)
with urllib.request.urlopen(req, context=ctx) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    steps = data.get('trajectory', {}).get('steps', [])
    for s in reversed(steps):
        if s.get('type') == 'CORTEX_STEP_TYPE_USER_INPUT':
            ui = s.get('userInput', {})
            text = ui.get('userResponse', '')
            cfg = ui.get('userConfig')
            print(f'User prompt: {text[:40]} | Has userConfig: {cfg is not None}')
            if cfg:
                print('  planModel in userConfig:', cfg.get('plannerConfig', {}).get('planModel'))
                with open('working_template.json', 'w', encoding='utf-8') as f:
                    json.dump(cfg, f, indent=2)
                break
