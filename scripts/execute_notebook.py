"""Ejecuta el notebook desde un kernel limpio y conserva sus resultados."""

import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def main():
    root = Path(__file__).resolve().parents[1]
    notebook_path = root / "notebooks/01_analisis_preparacion.ipynb"
    for name, folder in {
        "JUPYTER_RUNTIME_DIR": "outputs/jupyter",
        "IPYTHONDIR": "outputs/ipython",
        "MPLCONFIGDIR": "outputs/matplotlib",
    }.items():
        path = root / folder
        path.mkdir(parents=True, exist_ok=True)
        os.environ[name] = str(path)
    notebook = nbformat.read(notebook_path, as_version=4)
    nbformat.validate(notebook)
    client = NotebookClient(
        notebook, timeout=180, kernel_name="python3",
        resources={"metadata": {"path": str(root)}},
        allow_errors=False, record_timing=False,
    )
    client.execute()
    nbformat.validate(notebook)
    nbformat.write(notebook, notebook_path)
    executed = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert all(cell.execution_count is not None for cell in executed)
    assert not any(output.output_type == "error" for cell in executed for output in cell.outputs)
    print(f"Notebook ejecutado sin errores: {len(executed)} celdas de código.")


if __name__ == "__main__":
    main()
