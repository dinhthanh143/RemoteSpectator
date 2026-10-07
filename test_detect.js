const { execSync } = require('child_process');
const https = require('https');

function getAntigravityEndpoint() {
  try {
    const cmd = "powershell -NoProfile -Command \"Get-CimInstance Win32_Process -Filter \\\"Name = 'language_server.exe'\\\" | Select-Object ProcessId, CommandLine | ConvertTo-Json\"";
    const raw = execSync(cmd, { encoding: 'utf8' }).trim();
    if (!raw) return null;
    
    let proc = JSON.parse(raw);
    if (Array.isArray(proc)) proc = proc[0];
    
    const tokenMatch = proc.CommandLine.match(/--csrf_token\s+([a-f0-9-]+)/i);
    const token = tokenMatch ? tokenMatch[1] : null;
    const pid = proc.ProcessId;

    if (!pid || !token) return null;

    const netCmd = `powershell -NoProfile -Command \"Get-NetTCPConnection -OwningProcess ${pid} -State Listen | Where-Object { $_.LocalAddress -eq '127.0.0.1' } | Select-Object -ExpandProperty LocalPort\"`;
    const portsRaw = execSync(netCmd, { encoding: 'utf8' }).trim();
    const ports = portsRaw.split(/\r?\n/).map(p => parseInt(p.trim())).filter(Boolean);

    return { pid, token, ports };
  } catch (err) {
    console.error("Auto-detect failed:", err.message);
    return null;
  }
}

async function verifyHttpsPort(port, token) {
  return new Promise(resolve => {
    const req = https.request({
      hostname: '127.0.0.1',
      port: port,
      path: '/exa.language_server_pb.LanguageServerService/GetCascadeTrajectory',
      method: 'POST',
      rejectUnauthorized: false,
      timeout: 1000,
      headers: {
        'x-codeium-csrf-token': token,
        'Content-Type': 'application/json'
      }
    }, res => {
      resolve(res.statusCode === 200 || res.statusCode === 400);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => { req.destroy(); resolve(false); });
    req.write(JSON.stringify({ cascadeId: 'dummy' }));
    req.end();
  });
}

async function detectWorkingEndpoint() {
  const info = getAntigravityEndpoint();
  if (!info) return null;
  for (const p of info.ports) {
    if (await verifyHttpsPort(p, info.token)) {
      return { port: p, token: info.token };
    }
  }
  return null;
}

detectWorkingEndpoint().then(res => console.log('Found endpoint:', res));
