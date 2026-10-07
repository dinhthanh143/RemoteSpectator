import re, subprocess, json, urllib.request, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def detect_antigravity():
    cmd = ["powershell", "-NoProfile", "-Command", 
           "Get-CimInstance Win32_Process -Filter \"Name = 'language_server.exe'\" | Select-Object -Property ProcessId, CommandLine | ConvertTo-Json -Compress"]
    out = subprocess.check_output(cmd, text=True).strip()
    data = json.loads(out)
    if isinstance(data, list): data = data[0]
    
    cmdline = data.get("CommandLine", "")
    pid = data.get("ProcessId")
    
    token_m = re.search(r'--csrf_token\s+([a-f0-9-]+)', cmdline)
    token = token_m.group(1) if token_m else None
    print(f"PID: {pid}, Token: {token}")
    
    if not pid or not token:
        return None
        
    net_cmd = ["powershell", "-NoProfile", "-Command",
               f"Get-NetTCPConnection -OwningProcess {pid} -State Listen | Select-Object -ExpandProperty LocalPort"]
    ports = [int(p.strip()) for p in subprocess.check_output(net_cmd, text=True).strip().splitlines() if p.strip()]
    print("Found listening ports:", ports)
    
    for port in ports:
        req = urllib.request.Request(
            f"https://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/GetCascadeTrajectory",
            data=json.dumps({"cascadeId": "63491d75-f037-436d-9859-d347c40dd7a1"}).encode("utf-8"),
            headers={"x-codeium-csrf-token": token, "Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=1.5) as resp:
                print(f"Port {port} status: {resp.status}")
                if resp.status == 200:
                    return {"port": port, "token": token, "pid": pid}
        except urllib.error.HTTPError as e:
            print(f"Port {port} HTTPError: {e.code}")
            if e.code in (200, 400):
                return {"port": port, "token": token, "pid": pid}
        except Exception as e:
            print(f"Port {port} failed: {e}")
            pass
    return None

print("Result:", detect_antigravity())
