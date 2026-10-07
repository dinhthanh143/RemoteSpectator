import re
path = r'C:\Users\ADMIN\AppData\Local\Programs\antigravity\resources\bin\language_server.exe'
with open(path, 'rb') as f:
    data = f.read()

pos = data.find(b'SendUserCascadeMessageRequest')
while pos != -1:
    snippet = data[pos: pos + 2500]
    json_tags = re.findall(rb'json:"([^"]+)"', snippet)
    if json_tags:
        print('Found struct tags near pos', pos, ':', [t.decode('latin1') for t in json_tags])
    pos = data.find(b'SendUserCascadeMessageRequest', pos + 1)
