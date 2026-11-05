"""Verificar aislamiento y respuestas WSGI; no entrena ni modifica la evaluación."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.deployment import create_app
from src.evaluation import file_sha256


def main():
    protected = ['models/modelo_seleccionado.joblib', 'data/processed/test.csv',
                 'reports/test_evaluation.json', 'docs/Informe - Proyecto de IA.docx']
    before = {name: file_sha256(ROOT / name) for name in protected}
    app = create_app(session_limit=2, session_ttl=900, secure_cookie=True,
                     public_origin='https://example.onrender.com')
    a, b, c = app.test_client(), app.test_client(), app.test_client()
    checks = []

    def check(name, condition):
        assert condition, name
        checks.append({'test': name, 'status': 'passed'})

    try:
        check('Estado saludable sin crear sesiones', a.get('/health').json['status'] == 'ok'
              and len(app.extensions['simulation_store'].items) == 0)
        response = a.get('/api/state')
        check('Cookie privada para HTTPS', response.json['processed'] == 0
              and all(word in response.headers['Set-Cookie'] for word in ['HttpOnly', 'Secure', 'SameSite=Lax']))
        check('Segundo navegador inicia en cero', b.get('/api/state').json['processed'] == 0)
        for _ in range(22):
            response = a.post('/api/step', json={})
        check('Alerta histórica reproducida', response.json['last']['UDI'] == 1392 and response.json['last']['alert'])
        check('Avance aislado', b.get('/api/state').json['processed'] == 0)
        check('Exportación aislada', len(a.get('/api/export').data.decode('utf-8-sig').splitlines()) == 23
              and len(b.get('/api/export').data.decode('utf-8-sig').splitlines()) == 1)
        b.post('/api/reset', json={})
        check('Reiniciar otro navegador conserva el avance', a.get('/api/state').json['processed'] == 22)
        check('Origen ajeno rechazado', a.post('/api/reset', json={}, headers={'Origin': 'https://ajeno.example'}).status_code == 403)
        check('Origen publicado aceptado', a.post('/api/pause', json={}, headers={'Origin': 'https://example.onrender.com'}).status_code == 200)
        check('JSON y carga excesiva rechazados', a.post('/api/reset', data='invalid').status_code == 400
              and a.post('/api/load', json={'csv': 'x' * 2_000_001}).status_code == 413)
        check('Carga incorrecta conserva sesión', a.post('/api/load', json={'csv': 'bad'}).status_code == 400
              and a.get('/api/state').json['processed'] == 22)
        check('Límite de sesiones responde sin afectar usuarios', c.get('/api/state').status_code == 429
              and a.get('/api/state').json['processed'] == 22)
        store = app.extensions['simulation_store']
        store.clock = lambda: max(touched for _, touched in store.items.values()) + 901
        check('Sesión expirada se reinicia', c.get('/api/state').json['processed'] == 0)
        check('Interfaz y manual disponibles', a.get('/').status_code == 200
              and a.get('/manual.js').status_code == 200
              and a.get('/project/file?file=docs/MANUAL_USUARIO.md').data == (ROOT/'docs/MANUAL_USUARIO.md').read_bytes())
        check('Rutas privadas bloqueadas', a.get('/project/file?file=.git/config').status_code == 404
              and a.get('/deployment/artifacts/modelo_seleccionado.joblib').status_code == 404)
        check('Metadatos de sesión web', a.get('/api/project').json['runtime']['session_scope'] == 'browser')
    finally:
        app.extensions['simulation_store'].close()
    after = {name: file_sha256(ROOT / name) for name in protected}
    check('Experimento e informe sin cambios', before == after)
    report = {'generated_at_utc': datetime.now(timezone.utc).isoformat(), 'all_checks_passed': True,
              'scope': 'Comprobaciones locales WSGI; no equivalen a verificación del alojamiento público.',
              'checks': checks, 'protected_before': before, 'protected_after': after}
    (ROOT/'reports/deployment_checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'Despliegue: {len(checks)} comprobaciones locales superadas.')

if __name__ == '__main__':
    main()
