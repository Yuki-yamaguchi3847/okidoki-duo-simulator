import http.server
import socketserver
import os
import sys

# --- Configuration ---
PORT = 8000
DIRECTORY = "static"
DEFAULT_SETTING = 1
SETTING_LEVEL = DEFAULT_SETTING

# --- Parse Command-Line Arguments ---
if len(sys.argv) > 1:
    try:
        level = int(sys.argv[1])
        # Simple validation, assumes SETTINGS dict will be in JS from 1-6
        if 1 <= level <= 6:
            SETTING_LEVEL = level
        else:
            print(f"Warning: Setting level '{level}' is out of range (1-6). Defaulting to {DEFAULT_SETTING}.")
    except ValueError:
        print(f"Warning: Invalid setting level '{sys.argv[1]}'. Defaulting to {DEFAULT_SETTING}.")

# --- Custom Handler ---
class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # If the request is for /config.js, generate it dynamically
        if self.path == '/config.js':
            try:
                self.send_response(200)
                self.send_header('Content-type', 'application/javascript')
                self.end_headers()
                # Write the config JS content to the response
                js_content = f"const SETTING_LEVEL = {SETTING_LEVEL};"
                self.wfile.write(js_content.encode('utf-8'))
            except Exception as e:
                print(f"Error generating config.js: {e}")
                self.send_error(500, "Internal Server Error")
        else:
            # For all other requests, serve files from the 'static' directory
            super().do_GET()

    def __init__(self, *args, **kwargs):
        # The directory argument is available in Python 3.7+
        # For older versions, you might need to os.chdir() into the directory first
        super().__init__(*args, directory=DIRECTORY, **kwargs)


# --- Server Startup ---
# Allow the port to be reused immediately after the server is stopped
socketserver.TCPServer.allow_reuse_address = True

with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
    # Change directory to the script's location to ensure relative paths work
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"Serving Oki Doki 2 UI with [Setting {SETTING_LEVEL}] at http://localhost:{PORT}")
    print("Press Ctrl+C to stop the server.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()
