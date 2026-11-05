"""Servidor local para la demostración; solo escucha en 127.0.0.1."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

from src.portal import DOWNLOAD_FILES, metadata, source_content


def create_server(simulator, web_root, port=8765):
    assets = {"/": ("index.html", "text/html; charset=utf-8"),
              "/app.js": ("app.js", "text/javascript; charset=utf-8"),
              "/style.css": ("style.css", "text/css; charset=utf-8"),
              "/portal.js": ("portal.js", "text/javascript; charset=utf-8")}
    assets["/portal.css"] = ("portal.css", "text/css; charset=utf-8")
    assets["/monitor.css"] = ("monitor.css", "text/css; charset=utf-8")
    assets["/monitor.js"] = ("monitor.js", "text/javascript; charset=utf-8")
    assets["/theme.js"] = ("theme.js", "text/javascript; charset=utf-8")
    assets["/theme.css"] = ("theme.css", "text/css; charset=utf-8")
    assets["/manual.js"] = ("manual.js", "text/javascript; charset=utf-8")
    assets["/manual.css"] = ("manual.css", "text/css; charset=utf-8")
    for font in ("SpaceGrotesk", "Inter"):
        assets[f"/fonts/{font}.ttf"] = (f"fonts/{font}.ttf", "font/ttf")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def respond(self, status, body, content_type="application/json; charset=utf-8", download=None):
            if isinstance(body, dict):
                body = json.dumps(body, ensure_ascii=False, allow_nan=False)
            if isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if download:
                self.send_header("Content-Disposition", f'attachment; filename="{download}"')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlsplit(self.path).path
            root = web_root.parent
            query = parse_qs(urlsplit(self.path).query)
            if path == "/api/project":
                self.respond(200, metadata(root))
            elif path == "/api/source":
                try:
                    self.respond(200, source_content(root, query.get("file", [""])[0]))
                except ValueError as exc:
                    self.respond(404, {"error": str(exc)})
            elif path == "/project/file":
                name = query.get("file", [""])[0]
                if name not in DOWNLOAD_FILES or not (root / name).is_file():
                    self.respond(404, {"error": "Archivo no disponible."})
                    return
                mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if name.endswith(".docx") else "application/octet-stream"
                self.respond(200, (root / name).read_bytes(), mime, (root / name).name)
            elif path in assets:
                filename, mime = assets[path]
                self.respond(200, (web_root / filename).read_bytes(), mime)
            elif path == "/api/state":
                self.respond(200, simulator.snapshot())
            elif path == "/api/export":
                self.respond(200, "\ufeff" + simulator.export_csv(), "text/csv; charset=utf-8", "simulacion_ai4i.csv")
            else:
                self.respond(404, {"error": "Ruta no disponible."})

        def do_POST(self):
            origin = self.headers.get("Origin")
            if origin and origin not in {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}:
                self.respond(403, {"error": "La simulación solo acepta acciones desde su interfaz local."})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 2_000_000:
                    raise ValueError("La solicitud está vacía o supera 2 MB.")
                data = json.loads(self.rfile.read(size).decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("La solicitud debe ser un objeto JSON.")
                path = urlsplit(self.path).path
                if path == "/api/start":
                    result = simulator.start(data.get("interval", 0.5))
                elif path == "/api/pause":
                    result = simulator.pause()
                elif path == "/api/reset":
                    result = simulator.reset()
                elif path == "/api/step":
                    result = simulator.step()
                elif path == "/api/load":
                    if not isinstance(data.get("csv"), str):
                        raise ValueError("Selecciona un archivo CSV de prueba válido.")
                    result = simulator.load_csv(data["csv"])
                else:
                    self.respond(404, {"error": "Acción no disponible."})
                    return
                self.respond(200, result)
            except (ValueError, UnicodeError) as exc:
                self.respond(400, {"error": str(exc)})
            except Exception:
                self.respond(500, {"error": "No se pudo completar la operación. Revisa los archivos locales del experimento."})

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
