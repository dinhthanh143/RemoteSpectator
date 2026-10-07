const fs = require('fs');
const https = require('https');
const readline = require('readline');
const path = require('path');

// 1. Load Discord Token & Channel
const envPath = 'D:/BotTest/gachaversal/.env';
if (!fs.existsSync(envPath)) {
  console.error('Error: .env not found at', envPath);
  process.exit(1);
}
const envContent = fs.readFileSync(envPath, 'utf8');
const tokenMatch = envContent.match(/DISCORD_TOKEN=(.+)/);
if (!tokenMatch) {
  console.error('Error: DISCORD_TOKEN missing in .env');
  process.exit(1);
}
const TOKEN = tokenMatch[1].trim();

// Target channel (#test)
const CHANNEL_ID = '1443065160997671073';

// 2. Active Antigravity Conversation Transcript Path
const CONVERSATION_ID = '63491d75-f037-436d-9859-d347c40dd7a1';
const TRANSCRIPT_PATH = `C:/Users/ADMIN/.gemini/antigravity/brain/${CONVERSATION_ID}/.system_generated/logs/transcript.jsonl`;

console.log(`[Bridge] Watching Antigravity conversation: ${CONVERSATION_ID}`);
console.log(`[Bridge] Target Discord channel: ${CHANNEL_ID}`);

function postToDiscord(text, attachments = []) {
  if (!text && attachments.length === 0) return;

  const boundary = '----SpectatorBoundary' + Date.now();
  let bodyBuffer;
  let contentType;

  if (attachments.length > 0) {
    contentType = `multipart/form-data; boundary=${boundary}`;
    const parts = [];

    // Payload JSON
    const payload = JSON.stringify({ content: text });
    parts.push(Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="payload_json"\r\nContent-Type: application/json\r\n\r\n${payload}\r\n`));

    // Files
    attachments.forEach((filePath, idx) => {
      if (fs.existsSync(filePath)) {
        const fileName = path.basename(filePath);
        const fileData = fs.readFileSync(filePath);
        parts.push(Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="files[${idx}]"; filename="${fileName}"\r\nContent-Type: image/png\r\n\r\n`));
        parts.push(fileData);
        parts.push(Buffer.from('\r\n'));
      }
    });

    parts.push(Buffer.from(`--${boundary}--\r\n`));
    bodyBuffer = Buffer.concat(parts);
  } else {
    contentType = 'application/json';
    bodyBuffer = Buffer.from(JSON.stringify({ content: text }));
  }

  const req = https.request({
    hostname: 'discord.com',
    path: `/api/v10/channels/${CHANNEL_ID}/messages`,
    method: 'POST',
    headers: {
      'Authorization': 'Bot ' + TOKEN,
      'Content-Type': contentType,
      'Content-Length': bodyBuffer.length
    }
  }, res => {
    if (res.statusCode >= 200 && res.statusCode < 300) {
      console.log(`[Bridge -> Discord] Successfully delivered update.`);
    } else {
      console.warn(`[Bridge -> Discord] HTTP ${res.statusCode}`);
    }
  });

  req.on('error', err => console.error('[Bridge Error]', err.message));
  req.write(bodyBuffer);
  req.end();
}

// 3. Track Transcript changes
let lastLineCount = 0;

function checkTranscript() {
  if (!fs.existsSync(TRANSCRIPT_PATH)) return;

  const content = fs.readFileSync(TRANSCRIPT_PATH, 'utf8');
  const lines = content.trim().split('\n').filter(Boolean);

  if (lastLineCount === 0) {
    lastLineCount = lines.length;
    console.log(`[Bridge] Initialized at step line ${lastLineCount}`);
    return;
  }

  if (lines.length > lastLineCount) {
    const newLines = lines.slice(lastLineCount);
    lastLineCount = lines.length;

    for (const rawLine of newLines) {
      try {
        const step = JSON.parse(rawLine);
        // Only mirror Model responses to avoid echoing
        if (step.source === 'MODEL' && step.type === 'PLANNER_RESPONSE' && step.content) {
          console.log(`[Bridge] New Antigravity response detected: step ${step.step_index}`);
          
          // Truncate to Discord 2000 limit if needed
          const msg = `🤖 **Antigravity Update:**\n\n${step.content.slice(0, 1900)}`;
          postToDiscord(msg);
        }
      } catch (e) {
        // partial line or parsing error
      }
    }
  }
}

// Initial read
checkTranscript();

// Watch for file updates
fs.watchFile(TRANSCRIPT_PATH, { interval: 1000 }, () => {
  checkTranscript();
});

console.log('[Bridge] Active and listening for Antigravity changes...');
