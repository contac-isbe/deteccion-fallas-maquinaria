"""Ejecutar desde la raíz: python scripts/run_simulation.py."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation import load_frozen_experiment
from src.simulation import Simulator
from src.simulation_server import create_server


def main():
    parser = argparse.ArgumentParser(description="Simulación local de detección de fallas AI4I.")
    parser.add_argument("--port", type=int, default=8771)
    args = parser.parse_args()
    try:
        model, test, _selection, fingerprints = load_frozen_experiment(ROOT)
        simulator = Simulator(model, test, fingerprints)
        server = create_server(simulator, ROOT / "web", args.port)
    except (OSError, ValueError, AssertionError) as exc:
        print(f"No se pudo iniciar: {exc}", file=sys.stderr)
        print("Ejecuta primero los notebooks 01 y 02 con las dependencias de requirements.txt.", file=sys.stderr)
        return 1
    simulator.start_worker()
    print(f"Portal alternativo local: http://127.0.0.1:{server.server_port}", flush=True)
    print("Ctrl+C para detener. El modelo no se entrena ni se modifica.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        simulator.close()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
