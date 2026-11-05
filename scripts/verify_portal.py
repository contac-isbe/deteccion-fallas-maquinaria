"""Comprobaciones del portal alternativo local; no entrena ni publica cambios."""

import json
import sys
import threading
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.evaluation import file_sha256, load_frozen_experiment
from src.portal import SOURCE_FILES
from src.simulation import Simulator
from src.simulation_server import create_server


def main():
    cases = []
    protected = ["models/modelo_seleccionado.joblib", "data/processed/test.csv",
                 "data/raw/ai4i2020.csv", "reports/test_evaluation.json", "docs/Informe - Proyecto de IA.docx"]
    before = {name: file_sha256(ROOT / name) for name in protected}
    model, test, _selection, hashes = load_frozen_experiment(ROOT)
    sim = Simulator(model, test, hashes)
    server = create_server(sim, ROOT / "web", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    address = f"http://127.0.0.1:{server.server_port}"

    def get(path, data=None):
        body = None if data is None else json.dumps(data).encode()
        req = Request(address + path, data=body, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=15) as response:
            return response.read(), response.headers

    def passed(name, detail):
        cases.append({"test": name, "status": "passed", "evidence": detail})

    try:
        html = get("/")[0].decode()
        class Page(HTMLParser):
            def __init__(self):
                super().__init__(); self.ids=[]; self.tabs=[]; self.panels=[]
            def handle_starttag(self, tag, attrs):
                attr=dict(attrs)
                if "id" in attr:self.ids.append(attr["id"])
                if attr.get("role")=="tab":self.tabs.append(attr)
                if attr.get("role")=="tabpanel":self.panels.append(attr)
        page=Page();page.feed(html)
        assert len(page.ids)==len(set(page.ids))
        assert len(page.tabs)==len(page.panels)==3
        assert {x["aria-controls"] for x in page.tabs}=={x["id"] for x in page.panels}
        assert 'El despliegue del 7.2 sigue pendiente.' in html
        passed("Tres pestañas con paneles asociados", "Documentación, Código y Ejecución y pruebas; identificadores únicos y despliegue pendiente explícito.")
        for path in ["/app.js", "/portal.js", "/portal.css", "/monitor.js", "/monitor.css", "/theme.js", "/theme.css", "/manual.js", "/manual.css", "/fonts/Inter.ttf", "/fonts/SpaceGrotesk.ttf"]:
            assert len(get(path)[0]) > 100
        passed("Recursos de la interfaz", "HTML, scripts y estilos se sirven correctamente.")
        info = json.loads(get("/api/project")[0])
        final = json.loads((ROOT / "reports/test_evaluation.json").read_text(encoding="utf-8"))
        assert info["metrics"] == final["metrics"] and info["model_sha256"] == final["model_sha256"]
        assert info["publication"] == "Código publicado; despliegue pendiente"
        passed("Documentación basada en resultados guardados", "Métricas y huella del modelo iguales a la evaluación histórica; despliegue pendiente.")
        for path in info["source_files"]:
            assert path in SOURCE_FILES
            result=json.loads(get("/api/source?file=" + quote(path, safe=""))[0])
            assert result["path"]==path and result["content"]
        passed("Visor de código", f'{len(info["source_files"])} archivos locales consultados correctamente; los notebooks muestran celdas de texto y código.')
        for path in ["docs/Informe - Proyecto de IA.docx", "notebooks/01_analisis_preparacion.ipynb", "data/README.md", "reports/simulation_checks.json", "reports/monitor_simulation_checks.json", "docs/MANUAL_USUARIO.md"]:
            content,headers=get("/project/file?file="+quote(path,safe=""))
            assert content==(ROOT/path).read_bytes()
            assert "attachment" in headers["Content-Disposition"]
        passed("Descargas de documentación y código", "Word, notebook, procedencia de datos y evidencia descargables sin alterar sus bytes.")
        for path in ["/api/source?file=..%2F.git%2Fconfig", "/project/file?file=.git%2Fconfig", "/api/source?file=desconocido.py"]:
            try:get(path)
            except HTTPError as exc:assert exc.code==404
            else:raise AssertionError("Se sirvió un archivo ajeno a los contenidos del portal.")
        passed("Archivos limitados al contenido del proyecto", "Las rutas desconocidas y los archivos fuera de la lista permitida no se sirven.")
        for _ in range(22):state=json.loads(get("/api/step", {})[0])
        assert state["processed"]==22 and state["last"]["UDI"]==1392 and state["last"]["alert"]
        assert state["counts"]=={"TN":20,"FP":0,"FN":1,"TP":1}
        assert len(state["series"])==22 and state["series"][-1]["UDI"]==1392
        json.loads(get("/api/project")[0])
        get("/api/source?file=src%2Fpreparation.py")
        assert json.loads(get("/api/state")[0])["processed"]==22
        passed("Integración con la simulación", "UDI 1392 genera alerta; consultar documentación o código conserva la sesión y sus errores.")
    finally:
        sim.close();server.shutdown();server.server_close();thread.join(timeout=5)
    after={name:file_sha256(ROOT/name) for name in protected}
    assert before==after
    passed("Modelo, datos, evaluación e informe conservados", "Huellas iguales antes y después de las pruebas del portal.")
    report={"generated_at_utc":datetime.now(timezone.utc).isoformat(),"all_checks_passed":True,
            "base_revision":"4406aae","publication":"github_71","checks":cases,
            "protected_before":before,"protected_after":after,
            "scope":"Pruebas HTTP y de estructura; navegación, lectura y diseño se revisan también en el navegador."}
    (ROOT/"reports/portal_checks.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Portal: {len(cases)} comprobaciones correctas. reports/portal_checks.json")


if __name__=="__main__":main()
