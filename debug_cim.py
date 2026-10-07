import subprocess, json

cmd = ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Process -Filter \"Name = 'language_server.exe'\" | Select-Object -Property ProcessId, CommandLine | ConvertTo-Json -Compress"]
out = subprocess.check_output(cmd, text=True)
print("Len:", len(out))
data = json.loads(out)
print("Keys:", data.keys() if isinstance(data, dict) else len(data))
print("CommandLine:", data.get("CommandLine", "")[:150])
