import sys
import os
import json
import base64

def generate_preview_html(image_path: str, url: str, output_html_path: str):
    """Generates a single snapshot preview widget."""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
        
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
</head>
<body class="bg-transparent text-[var(--foreground)] antialiased p-2">
  <div class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-xl overflow-hidden shadow-lg">
    <div class="flex items-center justify-between px-4 py-2 border-b border-[var(--border)] bg-[var(--sidebar)]">
      <div class="flex items-center space-x-2">
        <span class="inline-block w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
        <span class="text-xs font-semibold tracking-wide uppercase text-[var(--muted-foreground)]">Remote Spectator Live Preview</span>
      </div>
      <span class="text-xs text-[var(--muted-foreground)] font-mono">{url}</span>
    </div>
    <div class="p-2 bg-black/10 flex justify-center">
      <img src="data:image/png;base64,{b64}" alt="Remote Spectator Preview" class="rounded-lg border border-[var(--border)] max-h-[380px] object-contain shadow-sm" />
    </div>
  </div>
</body>
</html>"""
    
    os.makedirs(os.path.dirname(os.path.abspath(output_html_path)), exist_ok=True)
    with open(output_html_path, "w", encoding="utf-8") as out:
        out.write(html)
    print(f"Generated Single Preview: {output_html_path}")

def generate_video_preview_html(video_path: str, url: str, output_html_path: str):
    """Generates an inline video player widget with autoplay and looping."""
    with open(video_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
        
    ext = video_path.split(".")[-1].lower()
    mime = "video/mp4" if ext == "mp4" else ("video/webm" if ext == "webm" else "image/gif")
    
    if ext == "gif":
        media_tag = f'<img src="data:image/gif;base64,{b64}" alt="Recording Clip" class="rounded-lg border border-[var(--border)] max-h-[380px] object-contain shadow-sm" />'
    else:
        media_tag = f'<video src="data:{mime};base64,{b64}" autoplay loop muted playsinline controls class="rounded-lg border border-[var(--border)] max-h-[380px] object-contain shadow-sm"></video>'

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
</head>
<body class="bg-transparent text-[var(--foreground)] antialiased p-2">
  <div class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-xl overflow-hidden shadow-lg">
    <div class="flex items-center justify-between px-4 py-2 border-b border-[var(--border)] bg-[var(--sidebar)]">
      <div class="flex items-center space-x-2">
        <span class="inline-block w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse"></span>
        <span class="text-xs font-semibold tracking-wide uppercase text-[var(--muted-foreground)]">Interaction Clip ({ext.upper()})</span>
      </div>
      <span class="text-xs text-[var(--muted-foreground)] font-mono">{url}</span>
    </div>
    <div class="p-2 bg-black/15 flex justify-center">
      {media_tag}
    </div>
  </div>
</body>
</html>"""

    os.makedirs(os.path.dirname(os.path.abspath(output_html_path)), exist_ok=True)
    with open(output_html_path, "w", encoding="utf-8") as out:
        out.write(html)
    print(f"Generated Video Preview: {output_html_path}")


def generate_compare_preview_html(session_id: str, output_html_path: str):
    """Generates an interactive multi-variant comparison widget from session manifest."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    session_file = os.path.join(base_dir, ".spectator", "sessions", f"{session_id}.json")
    
    if not os.path.exists(session_file):
        print(f"Error: session file not found: {session_file}", file=sys.stderr)
        return
        
    with open(session_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    variants = data.get("variants", [])
    if not variants:
        return
        
    # Pre-encode images to base64
    cards_html = []
    pills_html = []
    
    for idx, v in enumerate(variants):
        if not os.path.exists(v["image_path"]):
            continue
        with open(v["image_path"], "rb") as img_f:
            b64 = base64.b64encode(img_f.read()).decode("utf-8")
            
        display_class = "block" if idx == len(variants) - 1 else "hidden"
        label = v.get("label", f"Step {idx+1}")
        step = v.get("step", idx+1)
        
        cards_html.append(f"""
        <div id="variant-panel-{idx}" class="variant-panel {display_class}">
          <div class="flex items-center justify-between text-xs text-[var(--muted-foreground)] mb-1 px-1">
            <span class="font-medium">Step {step}: <strong class="text-[var(--foreground)]">{label}</strong></span>
            <span class="font-mono text-[11px]">{v.get('timestamp', '')}</span>
          </div>
          <div class="bg-black/15 rounded-lg p-1.5 flex justify-center border border-[var(--border)]">
            <img src="data:image/png;base64,{b64}" alt="{label}" class="rounded border border-[var(--border)] max-h-[340px] object-contain shadow-sm" />
          </div>
        </div>
        """)
        
        btn_active = "bg-primary text-primary-foreground font-semibold" if idx == len(variants) - 1 else "bg-[var(--sidebar)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
        pills_html.append(f"""
        <button onclick="showVariant({idx})" id="pill-{idx}" class="variant-pill px-3 py-1 rounded-full text-xs transition border border-[var(--border)] {btn_active}">
          {step}. {label}
        </button>
        """)
        
    pills_str = "\n".join(pills_html)
    cards_str = "\n".join(cards_html)
    
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
</head>
<body class="bg-transparent text-[var(--foreground)] antialiased p-2">
  <div class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-xl overflow-hidden shadow-lg">
    <div class="flex items-center justify-between px-4 py-2 border-b border-[var(--border)] bg-[var(--sidebar)]">
      <div class="flex items-center space-x-2">
        <span class="inline-block w-2.5 h-2.5 rounded-full bg-indigo-500"></span>
        <span class="text-xs font-semibold tracking-wide uppercase text-[var(--muted-foreground)]">Comparison Timeline ({len(variants)} Steps)</span>
      </div>
      <span class="text-xs text-[var(--muted-foreground)] font-mono">Session: {session_id}</span>
    </div>
    
    <!-- Variant selector pills -->
    <div class="px-3 py-2 bg-[var(--content)]/40 border-b border-[var(--border)] flex flex-wrap gap-1.5 items-center">
      <span class="text-[11px] text-[var(--muted-foreground)] mr-1">Switch:</span>
      {pills_str}
    </div>
    
    <!-- Active variant view -->
    <div class="p-3">
      {cards_str}
    </div>
  </div>

  <script>
    function showVariant(targetIdx) {{
      document.querySelectorAll('.variant-panel').forEach((el, idx) => {{
        el.classList.toggle('hidden', idx !== targetIdx);
        el.classList.toggle('block', idx === targetIdx);
      }});
      document.querySelectorAll('.variant-pill').forEach((btn, idx) => {{
        if (idx === targetIdx) {{
          btn.className = "variant-pill px-3 py-1 rounded-full text-xs transition border border-[var(--border)] bg-primary text-primary-foreground font-semibold shadow-xs";
        }} else {{
          btn.className = "variant-pill px-3 py-1 rounded-full text-xs transition border border-[var(--border)] bg-[var(--sidebar)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]";
        }}
      }});
    }}
  </script>
</body>
</html>"""

    os.makedirs(os.path.dirname(os.path.abspath(output_html_path)), exist_ok=True)
    with open(output_html_path, "w", encoding="utf-8") as out:
        out.write(html)
    print(f"Generated Comparison Timeline Preview: {output_html_path}")

if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--session":
        generate_compare_preview_html(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 5 and sys.argv[1] == "--video":
        generate_video_preview_html(sys.argv[2], sys.argv[3], sys.argv[4])
    elif len(sys.argv) == 4:
        generate_preview_html(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Usage:")
        print("  python generate_preview.py <img_path> <url> <out_html>")
        print("  python generate_preview.py --video <video_path> <url> <out_html>")
        print("  python generate_preview.py --session <session_id> <out_html>")

