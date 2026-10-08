import sys
import os
import asyncio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.server import spectator_capture

if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173"
    profile = sys.argv[2] if len(sys.argv) > 2 else "jikkeiSama"
    out_file = sys.argv[3] if len(sys.argv) > 3 else "d:/BotTest/remoteSpectator/.spectator/last_capture.png"
    
    result = asyncio.run(spectator_capture(
        url=target_url,
        profile=profile,
        output_filename=out_file
    ))
    print(result)
