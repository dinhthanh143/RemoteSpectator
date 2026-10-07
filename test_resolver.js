const { execSync } = require('child_process');
const https = require('https');

const AGY_HTTPS = new https.Agent({
  rejectUnauthorized: false,
  keepAlive: true,
});

let cachedEndpoint = null;
let lastCheckTime = 0;

function queryAntigravityProcess() {
  try {
    const cmd = "powershell -NoProfile -Command \"Get-CimInstance Win32_Process -Filter \\\"Name = 'language_server.exe'\\\" | Select-Object -Property ProcessId, CommandLine | ConvertTo-Json -Compress\"";
    const raw = execSync(cmd, { encoding: 'utf8' }).trim();
    if (!raw) return null;
    let data = JSON.parse(raw);
    if (Array.isArray(data)) data = data[0];
    const cmdline = data.CommandLine || "";
    const tokenMatch = cmdline.match(/--csrf_token\s+([a-f0-9-]+)/i);
    const token = tokenMatch ? tokenMatch[1] : null;
    const pid = data.ProcessId;
    if (!pid || !token) return null;

    const netCmd = `powershell -NoProfile -Command \"Get-NetTCPConnection -OwningProcess ${pid} -State Listen | Select-Object -ExpandProperty LocalPort\"`;
    const ports = execSync(netCmd, { encoding: 'utf8' }).trim().split(/\r?\n/).map(p => parseInt(p.trim())).filter(Boolean);
    return { pid, token, ports };
  } catch (err) {
    return null;
  }
}

function probePort(port, token) {
  return new Promise((resolve) => {
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

async function getAntigravityEndpoint() {
  const now = Date.now();
  if (cachedEndpoint && (now - lastCheckTime < 30000)) {
    return cachedEndpoint;
  }

  const procInfo = queryAntigravityProcess();
  if (procInfo) {
    for (const port of procInfo.ports) {
      if (await probePort(port, procInfo.token)) {
        cachedEndpoint = { port, token: procInfo.token };
        lastCheckTime = now;
        return cachedEndpoint;
      }
    }
  }

  // Fallback to env or last known
  return cachedEndpoint || {
    port: Number(process.env.AGY_PORT) || 63119,
    token: process.env.AGY_CSRF || "2fda8345-9a47-4554-8598-1283bed14794"
  };
}

getAntigravityEndpoint().then(console.log);
