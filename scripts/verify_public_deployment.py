"""Pruebas HTTP del servicio publicado, con dos cookies independientes."""
import argparse
import csv
import io
import json
import sys
import subprocess
import os
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import HTTPCookieProcessor, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    args = parser.parse_args()
    url = args.url.rstrip('/')
    assert url.startswith('https://')
    a, b = build_opener(HTTPCookieProcessor(CookieJar())), build_opener(HTTPCookieProcessor(CookieJar()))
    checks = []

    def call(client, path, data=None, origin=None):
        headers = {'Content-Type': 'application/json'}
        if origin: headers['Origin'] = origin
        request = Request(url+path, data=None if data is None else json.dumps(data).encode(), headers=headers)
        with client.open(request, timeout=45) as response:
            body = response.read()
            return body, response.headers

    def state(client, path='/api/state', data=None):
        return json.loads(call(client, path, data, url if data is not None else None)[0])

    def check(name, condition):
        assert condition, name
        checks.append({'test': name, 'status': 'passed'})

    health = state(a, '/health')
    expected = json.loads((ROOT/'reports/model_selection.json').read_text('utf-8'))
    check('HTTPS y modelo congelado', health['status'] == 'ok' and health['model_sha256'] == expected['model_sha256'])
    info = state(a, '/api/project')
    check('Métricas históricas y sesiones web', info['runtime']['mode'] == 'web'
          and info['metrics'] == json.loads((ROOT/'reports/test_evaluation.json').read_text('utf-8'))['metrics'])
    body, headers = call(a, '/api/state')
    check('Cookie segura emitida', all(x in headers.get('Set-Cookie', '') for x in ['Secure', 'HttpOnly', 'SameSite=Lax']))
    check('Segundo cliente independiente', state(b)['processed'] == 0)
    for _ in range(22): current = state(a, '/api/step', {})
    check('Predicción y alerta UDI 1392', current['processed'] == 22 and current['last']['UDI'] == 1392 and current['last']['alert'])
    check('Comparaciones históricas del prefijo', current['counts'] == {'TN': 20, 'FP': 0, 'FN': 1, 'TP': 1})
    state(b, '/api/reset', {})
    check('Reinicio y avance aislados', state(a)['processed'] == 22 and state(b)['processed'] == 0)
    exported = list(csv.DictReader(io.StringIO(call(a, '/api/export')[0].decode('utf-8-sig'))))
    check('CSV completo de la sesión', len(exported) == 22 and int(exported[-1]['UDI']) == 1392)
    state(a, '/api/start', {'interval': .2})
    paused = state(a, '/api/pause', {})
    check('Inicio y pausa remotos', paused['status'] == 'paused' and state(a)['processed'] == paused['processed'])
    try: call(a, '/api/reset', {}, 'https://ajeno.example')
    except HTTPError as error: check('Origen ajeno rechazado', error.code == 403)
    else: raise AssertionError('Se aceptó un origen ajeno.')
    for name in ['docs/MANUAL_USUARIO.md', 'docs/Informe - Proyecto de IA.docx']:
        git = os.environ.get('GIT_EXECUTABLE', 'git')
        # El servidor usa los bytes de Git; Windows puede convertir el Markdown a CRLF.
        expected_bytes = subprocess.check_output([git, 'show', 'HEAD:'+name], cwd=ROOT)
        check('Descarga íntegra de Git: '+name, call(a, '/project/file?file='+quote(name, safe=''))[0] == expected_bytes)
    check('Recursos de interfaz disponibles', all(len(call(a, '/'+name)[0]) > 100 for name in ['portal.js', 'manual.js', 'theme.css']))
    check('Reinicio remoto', state(a, '/api/reset', {})['processed'] == 0)
    report = {'generated_at_utc': datetime.now(timezone.utc).isoformat(), 'url': url,
              'all_checks_passed': True, 'model_sha256': health['model_sha256'], 'checks': checks,
              'scope': 'Pruebas HTTP con dos clientes independientes y prefijo de 22 registros; sin reentrenamiento ni nueva evaluación independiente.'}
    (ROOT/'reports/public_deployment_checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    print(f'Servicio público: {len(checks)} comprobaciones superadas en {url}')

if __name__ == '__main__': main()
