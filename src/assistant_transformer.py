"""Transformer ajustado del asistente, servido con ONNX Runtime (int8, sin PyTorch) para que quepa en Render gratuito.

Archivos (creados por scripts/export_transformer_onnx.py): models/asistente_transformer.onnx,
models/asistente_tokenizer.json y models/asistente_transformer.json. Si falta algo, model() devuelve None y el asistente
usa el TF-IDF de respaldo.
"""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ONNX, TOKENIZER, CONFIG = (ROOT / "models/asistente_transformer.onnx", ROOT / "models/asistente_tokenizer.json",
                           ROOT / "models/asistente_transformer.json")


@lru_cache(maxsize=1)
def model():
    if not (ONNX.is_file() and TOKENIZER.is_file() and CONFIG.is_file()):
        return None
    try:
        import onnxruntime as ort
        from tokenizers import Tokenizer
    except ImportError:
        return None
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    opts = ort.SessionOptions()
    opts.intra_op_num_threads, opts.inter_op_num_threads = 1, 1
    sess = ort.InferenceSession(str(ONNX), opts, providers=["CPUExecutionProvider"])
    tok = Tokenizer.from_file(str(TOKENIZER))
    tok.enable_truncation(cfg["max_len"])
    tok.no_padding()  # tokenizer.json puede traer relleno activado; aquí se procesa un texto a la vez
    return sess, tok, cfg


def proba(texts, bundle=None):
    """Probabilidades (intención, falla) para una lista de textos."""
    sess, tok, _ = bundle or model()
    # Un texto por llamada y sin relleno: la exportación ONNX no maneja bien el relleno dentro de un lote.
    outs = [sess.run(None, {"input_ids": np.array([e.ids], dtype=np.int64), "attention_mask": np.ones((1, len(e.ids)), dtype=np.int64)})
            for e in tok.encode_batch(list(texts))]
    li, lc = np.concatenate([o[0] for o in outs]), np.concatenate([o[1] for o in outs])
    soft = lambda x: (e := np.exp(x - x.max(1, keepdims=True))) / e.sum(1, keepdims=True)
    return soft(li), soft(lc)


def understand(question):
    """(intención, falla, confianza) o None si el Transformer no está disponible."""
    bundle = model()
    if bundle is None:
        return None
    cfg = bundle[2]
    pi, pc = proba([question], bundle)
    pi, pc = pi[0], pc[0]
    intent, cause = cfg["intents"][pi.argmax()], cfg["causes"][pc.argmax()]
    if pi.max() < cfg["threshold"] or intent == "fuera":
        return None, None, float(pi.max())
    return intent, (None if cause == "ninguna" else cause), float(pi.max())
