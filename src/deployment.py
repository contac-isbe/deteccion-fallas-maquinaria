"""Aplicación WSGI de demostración con sesiones aisladas y modelo congelado."""
import atexit
import os
import secrets
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from werkzeug.exceptions import HTTPException

from src.evaluation import load_frozen_experiment
from src.portal import DOWNLOAD_FILES, metadata, source_content
from src.simulation import Simulator

ROOT = Path(__file__).resolve().parents[1]


class SessionStore:
    def __init__(self, model, test, hashes, *, limit=12, ttl=900, clock=time.monotonic):
        self.model, self.test, self.hashes = model, test, hashes
        self.limit, self.ttl, self.clock = limit, ttl, clock
        self.lock = threading.RLock()
        self.items = {}

    def get(self, token):
        with self.lock:
            now = self.clock()
            for key, (sim, touched) in list(self.items.items()):
                if now - touched >= self.ttl:
                    sim.close()
                    del self.items[key]
            if token not in self.items:
                if len(self.items) >= self.limit:
                    raise OverflowError("La demostración está ocupada. Intenta de nuevo en unos minutos.")
                token = secrets.token_urlsafe(32)
                sim = Simulator(self.model, self.test, self.hashes)
                sim.start_worker()
            else:
                sim = self.items[token][0]
            self.items[token] = (sim, now)
            return token, sim

    def close(self):
        with self.lock:
            for sim, _ in self.items.values():
                sim.close()
            self.items.clear()


def create_app(*, root=ROOT, secure_cookie=None, public_origin=None, session_limit=12, session_ttl=900):
    root = Path(root)
    model, test, _selection, hashes = load_frozen_experiment(root)
    store = SessionStore(model, test, hashes, limit=session_limit, ttl=session_ttl)
    app = Flask(__name__, static_folder=None)
    app.config['MAX_CONTENT_LENGTH'] = 2_000_000
    app.json.ensure_ascii = False
    secure = bool(os.environ.get('RENDER')) if secure_cookie is None else secure_cookie
    origin = (public_origin or os.environ.get('RENDER_EXTERNAL_URL', '')).rstrip('/')
    app.extensions['simulation_store'] = store
    atexit.register(store.close)

    @app.after_request
    def response_headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error='Solicitud no válida.'), error.code

    @app.get('/health')
    def health():
        return jsonify(status='ok', model_sha256=hashes['model_sha256'])

    @app.get('/api/project')
    def project():
        info = metadata(root)
        info['runtime'] = {'mode': 'web', 'session_ttl_minutes': store.ttl // 60,
                           'session_scope': 'browser', 'session_limit': store.limit}
        return jsonify(info)

    @app.get('/api/source')
    def source():
        try:
            return jsonify(source_content(root, request.args.get('file', '')))
        except ValueError as error:
            return jsonify(error=str(error)), 404

    @app.get('/project/file')
    def download():
        name = request.args.get('file', '')
        if name not in DOWNLOAD_FILES or not (root / name).is_file():
            return jsonify(error='Archivo no disponible.'), 404
        return send_file(root / name, as_attachment=True, download_name=Path(name).name)

    @app.route('/api/<action>', methods=['GET', 'POST'])
    def simulation(action):
        if (request.method, action) not in {('GET', 'state'), ('GET', 'export'),
                ('POST', 'start'), ('POST', 'pause'), ('POST', 'reset'), ('POST', 'step'), ('POST', 'load')}:
            return jsonify(error='Acción no disponible.'), 404
        if request.method == 'POST':
            allowed = {origin} if origin else {'http://127.0.0.1:8772', 'http://localhost:8772'}
            if request.headers.get('Sec-Fetch-Site') == 'cross-site' or (
                    request.headers.get('Origin') and request.headers['Origin'].rstrip('/') not in allowed):
                return jsonify(error='Utiliza los controles de esta misma página.'), 403
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                return jsonify(error='La solicitud debe ser un objeto JSON.'), 400
        try:
            token, sim = store.get(request.cookies.get('ai4i_session'))
            if action == 'state':
                result = jsonify(sim.snapshot())
            elif action == 'export':
                result = app.response_class('\ufeff' + sim.export_csv(), mimetype='text/csv')
                result.headers['Content-Disposition'] = 'attachment; filename="simulacion_ai4i.csv"'
            else:
                if action == 'start':
                    value = sim.start(data.get('interval', .5))
                elif action == 'load':
                    if not isinstance(data.get('csv'), str):
                        raise ValueError('Selecciona un archivo CSV de prueba válido.')
                    value = sim.load_csv(data['csv'])
                else:
                    value = getattr(sim, action)()
                result = jsonify(value)
            result.set_cookie('ai4i_session', token, httponly=True, secure=secure, samesite='Lax')
            return result
        except OverflowError as error:
            return jsonify(error=str(error)), 429
        except ValueError as error:
            return jsonify(error=str(error)), 400

    assets = {'/', '/app.js', '/style.css', '/portal.js', '/portal.css', '/monitor.js',
              '/monitor.css', '/theme.js', '/theme.css', '/manual.js', '/manual.css',
              '/fonts/Inter.ttf', '/fonts/SpaceGrotesk.ttf'}

    @app.get('/')
    @app.get('/<path:name>')
    def asset(name='index.html'):
        path = '/' if name == 'index.html' else '/' + name
        if path not in assets:
            return jsonify(error='Ruta no disponible.'), 404
        return send_file(root / 'web' / name)

    return app
