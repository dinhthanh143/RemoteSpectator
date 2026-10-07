import os
import sys
import json
import urllib.parse
from http.server import SimpleHTTPRequestHandler, HTTPServer
import threading

PORT = 49152
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CAPTURES_DIR = os.path.join(BASE_DIR, ".spectator", "captures")

os.makedirs(CAPTURES_DIR, exist_ok=True)

class SpectatorUIHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.render_dashboard()
        elif parsed.path.startswith("/captures/"):
            filename = os.path.basename(parsed.path)
            filepath = os.path.join(CAPTURES_DIR, filename)
            if os.path.exists(filepath):
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                with open(filepath, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File Not Found")
        elif parsed.path == "/api/files":
            files = self.get_capture_files()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(files).encode("utf-8"))
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/delete":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body) if body else {}
            filename = os.path.basename(data.get("filename", ""))
            filepath = os.path.join(CAPTURES_DIR, filename)
            
            if filename and os.path.exists(filepath):
                os.remove(filepath)
                res = {"success": True, "message": f"Deleted {filename}"}
            else:
                res = {"success": False, "message": "File not found or invalid"}
                
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
        elif parsed.path == "/api/clear-all":
            count = 0
            for f in os.listdir(CAPTURES_DIR):
                if f.endswith(".png"):
                    try:
                        os.remove(os.path.join(CAPTURES_DIR, f))
                        count += 1
                    except Exception:
                        pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "deleted": count}).encode("utf-8"))
        else:
            self.send_error(404)

    def get_capture_files(self):
        items = []
        if os.path.exists(CAPTURES_DIR):
            for name in os.listdir(CAPTURES_DIR):
                if name.endswith(".png"):
                    path = os.path.join(CAPTURES_DIR, name)
                    stat = os.stat(path)
                    items.append({
                        "name": name,
                        "size_kb": round(stat.st_size / 1024, 1),
                        "mtime": stat.st_mtime
                    })
        items.sort(key=lambda x: x["mtime"], reverse=True)
        return items

    def render_dashboard(self):
        files = self.get_capture_files()
        total_kb = sum(f["size_kb"] for f in files)
        
        cards = []
        for f in files:
            name = f["name"]
            size = f["size_kb"]
            cards.append(f"""
            <div id="card-{name}" class="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden flex flex-col group shadow-md transition hover:border-zinc-700">
                <div class="h-44 bg-black/40 flex items-center justify-center p-2 relative overflow-hidden">
                    <img src="/captures/{name}" class="max-h-full max-w-full object-contain rounded" loading="lazy" />
                    <a href="/captures/{name}" target="_blank" class="absolute top-2 right-2 bg-black/70 hover:bg-black text-xs px-2 py-1 rounded text-zinc-300 opacity-0 group-hover:opacity-100 transition">View Full</a>
                </div>
                <div class="p-3 flex items-center justify-between border-t border-zinc-800 bg-zinc-900/80">
                    <div class="truncate mr-2">
                        <p class="text-xs font-mono font-medium text-zinc-200 truncate" title="{name}">{name}</p>
                        <p class="text-[11px] text-zinc-400">{size} KB</p>
                    </div>
                    <button onclick="deleteFile('{name}')" class="px-2.5 py-1 text-xs font-medium bg-red-950/40 text-red-400 hover:bg-red-900/60 hover:text-red-300 border border-red-900/50 rounded transition">
                        Delete
                    </button>
                </div>
            </div>
            """)

        cards_str = "\n".join(cards) if cards else """
        <div class="col-span-full py-16 text-center text-zinc-400">
            <p class="text-base font-medium">No capture assets yet</p>
            <p class="text-xs text-zinc-400 mt-1">Screenshots from /remote-spectate will appear here automatically.</p>
        </div>
        """

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Remote Spectator Asset Manager</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-zinc-950 text-zinc-100 min-h-screen font-sans antialiased p-6">
    <div class="max-w-6xl mx-auto space-y-6">
        <!-- Header -->
        <header class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800">
            <div>
                <div class="flex items-center space-x-2.5">
                    <span class="w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></span>
                    <h1 class="text-xl font-bold tracking-tight text-white">Remote Spectator UI</h1>
                    <span class="text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded font-mono">Port {PORT}</span>
                </div>
                <p class="text-xs text-zinc-400 mt-1">Local asset manager & capture library</p>
            </div>
            <div class="flex items-center space-x-3">
                <span class="text-xs text-zinc-400 font-mono"><strong id="item-count" class="text-zinc-200">{len(files)}</strong> items (<span id="total-size">{round(total_kb / 1024, 2)} MB</span>)</span>
                <button onclick="clearAll()" class="px-3 py-1.5 text-xs font-semibold bg-red-900/30 text-red-400 hover:bg-red-900/60 border border-red-800 rounded transition">
                    Clear All
                </button>
                <button onclick="location.reload()" class="px-3 py-1.5 text-xs font-semibold bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 rounded transition">
                    Refresh
                </button>
            </div>
        </header>

        <!-- Grid -->
        <main id="gallery" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {cards_str}
        </main>
    </div>

    <script>
        async function deleteFile(name) {{
            if (!confirm(`Delete asset: ${{name}}?`)) return;
            const res = await fetch('/api/delete', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{filename: name}})
            }});
            const data = await res.json();
            if (data.success) {{
                const el = document.getElementById(`card-${{name}}`);
                if (el) el.remove();
            }} else {{
                alert(data.message);
            }}
        }}

        async function clearAll() {{
            if (!confirm('Are you sure you want to delete ALL capture assets? This cannot be undone.')) return;
            const res = await fetch('/api/clear-all', {{ method: 'POST' }});
            const data = await res.json();
            if (data.success) {{
                location.reload();
            }}
        }}
    </script>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

def start_ui_server(port: int = PORT):
    try:
        server = HTTPServer(("127.0.0.1", port), SpectatorUIHandler)
        print(f"SPECTATOR_UI_READY: http://localhost:{port}")
        server.serve_forever()
    except OSError as e:
        # Port might already be open by an earlier spectator process
        print(f"SPECTATOR_UI_PORT_IN_USE: {e}")

if __name__ == "__main__":
    start_ui_server()
