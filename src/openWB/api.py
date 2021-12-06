from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from .OpenWBCore import OpenWBCore
from threading import Thread
import logging

class OpenWBAPI(Thread):
   PORT = 8080

   def __init__(self, core: OpenWBCore):
      super().__init__(daemon=True)
      self.server = ThreadingHTTPServer(("", self.PORT), DataHandler)
      self.server.core = core
      self.server.logger = logging.getLogger()

   def run(self):
      self.server.serve_forever()


class DataHandler(SimpleHTTPRequestHandler):
   def do_GET(self):
      self.server.logger.info(f"Getting {self.path}")
      def send_data(s, data):
         s.send_response(200)
         s.send_header("Content-type", "text/plain")
         s.end_headers()
         s.wfile.write((data + "\n").encode())

      if self.path.startswith('/data/'):
         key = self.path[6:]
         self.server.logger.info(f"- data {key}")
         send_data(self, self.server.core.data.get(key, ""))
      elif self.path.startswith('/config/'):
         key = self.path[8:]
         self.server.logger.info(f"- config {key}")
         send_data(self, self.server.core.config.get(key, ""))
      else:
         self.send_error(404, "Invalid request")
