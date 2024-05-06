from http.server import BaseHTTPRequestHandler, HTTPServer
import cgi

def save_blob_as_wav(blob, filename):
    with open(filename, 'wb') as wav_file:
        wav_file.write(blob)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/history":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            message = "Histories"
            self.wfile.write(bytes(message, "utf8"))
        else:
            try:
                with open("index.html", "rb") as index_file:
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(index_file.read())
            except FileNotFoundError:
                self.send_error(404, "Index File Not Found")

    def do_POST(self):
        form = cgi.FieldStorage(
            fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"}
        )
        content = form.getvalue("content")
        audio = form.getvalue("audio")
        print(content, audio)
        
        save_blob_as_wav(audio, "input.wav")

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        message = "Hello, World! Here is a POST response"
        self.wfile.write(bytes(message, "utf8"))


PORT = 8080
with HTTPServer(("", PORT), handler) as server:
    print(f"Server listening on port {PORT}")
    server.serve_forever()
