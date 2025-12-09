import http.server
import socketserver
import os

PORT = 8081
XML_FILE = "tests/fixtures/valid_sample.xml"


class XMLRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/events":
            if os.path.exists(XML_FILE):
                self.send_response(200)
                self.send_header("Content-type", "application/xml")
                self.end_headers()
                with open(XML_FILE, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File not found")
        else:
            self.send_error(404, "Not found")


with socketserver.TCPServer(("", PORT), XMLRequestHandler) as httpd:
    print(f"Serving mock provider at http://localhost:{PORT}/api/events")
    httpd.serve_forever()
