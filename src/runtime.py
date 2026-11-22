"""Carga verificada de todo lo que la aplicación necesita: modelo, prueba, autoencoder y referencia."""
from src.autoencoder import load_autoencoder
from src.evaluation import load_frozen_experiment
from src.features import load_physical_model


def load_runtime(root):
    """Devuelve (modelo, prueba, huellas, autoencoder, referencia).

    Usa el árbol v2 con variables físicas si el experimento lo incluye; si no, el árbol v1 congelado.
    """
    model, test, _selection, hashes = load_frozen_experiment(root)
    hashes, reference = dict(hashes), None
    physical = load_physical_model(root)
    if physical is not None:
        model, info = physical
        hashes["model_sha256"] = info["model_sha256"]
        reference = info["evaluation"]["v2_test"]
    ae = load_autoencoder(root)
    if ae is not None:
        import json
        ae["info"]["evaluation"] = json.loads((root / "reports/autoencoder_evaluation.json").read_text(encoding="utf-8"))
    return model, test, hashes, ae, reference
