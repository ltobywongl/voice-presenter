from http.server import BaseHTTPRequestHandler, HTTPServer
import cgi
import json
from urllib.parse import parse_qs, urlparse
from uuid import uuid4 as uuid
from io import BytesIO

from redis import Redis
import boto3

# AWS Setup
queue = Redis(
    host="default-redis-0001-001.7zh2ph.0001.use1.cache.amazonaws.com",
    port=6379,
    decode_responses=True,
)
session = boto3.Session(region_name="us-east-1")
s3 = session.client("s3")


def save_blob_as_wav(blob, filename):
    with open(filename, "wb") as wav_file:
        wav_file.write(blob)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/history"):
            url_parts = urlparse(self.path)
            query_params = parse_qs(url_parts.query)
            id = query_params.get("id")[0]
            
            if not id:
                # Bad requrest
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                message = "Bad Request"
                self.wfile.write(bytes(message, "utf8"))
                return

            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": "ai-presenter", "Key": f"results/{id}.wav"},
            )
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            message = {"success": True, "url": url}
            self.wfile.write(bytes(json.dumps(message), "utf8"))
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
        if self.path == "/generate":
            form = cgi.FieldStorage(
                fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"}
            )
            task_id = str(uuid())
            content = form.getvalue("content")
            audio = form.getvalue("audio")

            if not content or not audio:
                # Bad requrest
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                message = "Bad Request"
                self.wfile.write(bytes(message, "utf8"))
                return

            try:
                fileobj = BytesIO(audio)
                s3.upload_fileobj(
                    fileobj,
                    "ai-presenter",
                    f"tasks/{task_id}.wav",
                    ExtraArgs={"ContentType": "audio/wav"},
                )
            except Exception as error:
                print(error)
                self.send_response(500)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                message = "File Storage Error"
                self.wfile.write(bytes(message, "utf8"))
                return

            try:
                data = {"id": task_id, "text": content}
                message = json.dumps(data)
                queue.rpush("tasks", message.encode("utf-8"))

                # Sending success response
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                message = {"success": True, "task_id": task_id}
                self.wfile.write(bytes(json.dumps(message), "utf8"))
            except Exception as error:
                print(error)
                self.send_response(500)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                message = "Queue Error"
                self.wfile.write(bytes(message, "utf8"))
        else:
            self.send_error(404, "Index File Not Found")


PORT = 8080
with HTTPServer(("", PORT), handler) as server:
    print(f"Server listening on port {PORT}")
    server.serve_forever()
