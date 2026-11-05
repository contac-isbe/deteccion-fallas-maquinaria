"""Contenido de documentación y código del portal alternativo local."""

import json

SOURCE_FILES = [
    "README.md", "requirements.txt", "data/README.md",
    "notebooks/01_analisis_preparacion.ipynb", "notebooks/02_entrenamiento_comparacion.ipynb",
    "notebooks/03_comprobacion_prueba.ipynb", "src/preparation.py", "src/training.py",
    "src/evaluation.py", "src/simulation.py", "src/simulation_server.py", "src/portal.py",
    "scripts/run_simulation.py", "scripts/verify_simulation.py", "scripts/verify_portal.py",
    "web/index.html", "web/portal.css", "web/app.js", "web/portal.js", "web/monitor.js", "web/monitor.css", "web/theme.js", "web/theme.css",
]
DOWNLOAD_FILES = SOURCE_FILES + [
    "docs/Informe - Proyecto de IA.docx", "data/raw/ai4i2020.csv",
    "reports/test_evaluation.json", "reports/simulation_checks.json",
    "reports/simulation_review.md", "reports/model_comparison.csv",
    "reports/portal_review.md", "reports/portal_checks.json", "docs/71_preparacion_local.md",
]


def metadata(root):
    def read(name):
        return json.loads((root / name).read_text(encoding="utf-8"))
    result = read("reports/test_evaluation.json")
    checks = read("reports/simulation_checks.json")
    return {
        "title": "Detección de fallas en maquinaria",
        "repository": "https://github.com/contac-isbe/deteccion-fallas-maquinaria/tree/feature/monitor-interactivo",
        "base_revision": "4406aae",
        "publication": "Versión alternativa; despliegue pendiente",
        "dataset": {"name": "AI4I 2020", "rows": 10000, "development_rows": 8000,
                    "test_rows": result["test_rows"], "test_failures": result["test_failure_count"],
                    "synthetic": True, "license": "CC BY 4.0", "label_disagreements": 27},
        "model": result["selected_model"], "metrics": result["metrics"],
        "model_sha256": result["model_sha256"],
        "verification": {"checks": len(checks["checks"]), "all_passed": checks["all_checks_passed"],
                         "generated_at_utc": checks["generated_at_utc"]},
        "source_files": [name for name in SOURCE_FILES if (root / name).is_file()],
    }


def source_content(root, name):
    if name not in SOURCE_FILES or not (root / name).is_file():
        raise ValueError("Archivo de código no disponible.")
    text = (root / name).read_text(encoding="utf-8")
    if name.endswith(".ipynb"):
        notebook = json.loads(text)
        blocks = []
        for i, cell in enumerate(notebook["cells"], start=1):
            body = "".join(cell.get("source", []))
            label = "Código" if cell["cell_type"] == "code" else "Explicación"
            blocks.append(f"# Celda {i} · {label}\n{body}")
        text = "\n\n".join(blocks)
    return {"path": name, "content": text, "notebook": name.endswith(".ipynb")}
