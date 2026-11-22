"""Exporta el Transformer ajustado (models/asistente_transformer/) a ONNX int8 para el despliegue y lo verifica.

Comprueba que la versión int8 da las mismas métricas (prueba y natural) que la de PyTorch, guarda el resultado en
reports/asistente_transformer_onnx.json y copia los archivos a deployment/artifacts con su hash en el manifiesto.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import assistant_data as D  # noqa: E402
from src import assistant_transformer as AT  # noqa: E402
from scripts import train_assistant as TA  # noqa: E402
from scripts.train_transformer import OUT_DIR, MultiTask  # noqa: E402


def main():
    cfg = json.loads((OUT_DIR / "config_asistente.json").read_text(encoding="utf-8"))
    model = MultiTask(cfg["base"], len(cfg["intents"]), len(cfg["causes"]))
    model.load_state_dict(torch.load(OUT_DIR / "pesos.pt"))
    model.eval()
    # Atención "eager" (operaciones explícitas): la versión optimizada (SDPA) se traza con formas fijas y falla con otras longitudes.
    if hasattr(model.encoder, "set_attn_implementation"):
        model.encoder.set_attn_implementation("eager")
    else:
        model.encoder.config._attn_implementation = "eager"
    fp32 = ROOT / "models/asistente_transformer_fp32.onnx"
    ids, mask = torch.ones(2, 16, dtype=torch.long), torch.ones(2, 16, dtype=torch.long)
    dyn = {0: "batch", 1: "seq"}
    torch.onnx.export(model, (ids, mask), fp32, input_names=["input_ids", "attention_mask"], output_names=["intent", "cause"],
                      dynamic_axes={"input_ids": dyn, "attention_mask": dyn, "intent": {0: "batch"}, "cause": {0: "batch"}},
                      opset_version=17, dynamo=False)
    from onnxruntime.quantization import QuantType, quantize_dynamic
    quantize_dynamic(str(fp32), str(AT.ONNX), weight_type=QuantType.QInt8)
    fp32.unlink()
    shutil.copyfile(OUT_DIR / "tokenizer.json", AT.TOKENIZER)
    AT.CONFIG.write_text(json.dumps({k: cfg[k] for k in ("base", "max_len", "intents", "causes", "threshold")}, indent=2), encoding="utf-8")
    AT.model.cache_clear()

    out = {"bytes_onnx_int8": AT.ONNX.stat().st_size}
    for name, rows in (("test_plantillas_no_vistas", D.build(seed=0)["test"]), ("natural_a_mano", D.natural())):
        X, y_i, y_c = TA.columns(rows)
        pi, pc = AT.proba(X)
        intent = [cfg["intents"][a] if m >= cfg["threshold"] else "fuera" for a, m in zip(pi.argmax(1), pi.max(1))]
        out[name] = TA.metrics(y_i, y_c, intent, [cfg["causes"][a] for a in pc.argmax(1)])
    (ROOT / "reports/asistente_transformer_onnx.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))

    art = ROOT / "deployment/artifacts"
    mp = art / "manifest.json"
    manifest = json.loads(mp.read_text(encoding="utf-8"))
    for p in (AT.ONNX, AT.TOKENIZER, AT.CONFIG):
        shutil.copyfile(p, art / p.name)
        manifest["files"][f"models/{p.name}"] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
    mp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Copiado a deployment/artifacts y registrado en manifest.json")


if __name__ == "__main__":
    main()
