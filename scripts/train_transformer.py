"""Fine-tuning de un Transformer pequeño en español para el asistente (intención + falla mencionada).

Mismo protocolo que scripts/train_assistant.py: mismos datos (assistant_data.build(seed=0)) y mismas particiones.
Se entrena con 'train'; se elige la mejor época y el umbral de rechazo con 'val'; se evalúa una vez con 'test' y con el
conjunto NATURAL escrito a mano, comparando con el TF-IDF + regresión logística y con la línea base sin entrenamiento.

Arquitectura: un solo encoder Transformer preentrenado (DistilBERT en español, 6 capas) compartido por dos cabezas
lineales (multitarea): una predice la intención y otra la falla, ambas a partir del vector del token [CLS].

Uso (CPU, ~10-20 min):  .venv\\Scripts\\python scripts\\train_transformer.py --epochs 4
"""
import argparse
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import torch
from sklearn.metrics import f1_score
from torch import nn
from transformers import AutoModel, AutoTokenizer, get_linear_schedule_with_warmup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import assistant_data as D  # noqa: E402
from scripts import train_assistant as TA  # noqa: E402  (reutiliza columns, predict, metrics y baseline)

SEED = 0
MODEL_NAME = "dccuchile/distilbert-base-spanish-uncased"
OUT_DIR = ROOT / "models/asistente_transformer"
REPORT = ROOT / "reports/asistente_transformer_evaluation.json"


class MultiTask(nn.Module):
    """Encoder Transformer + dos cabezas de clasificación sobre el vector [CLS]."""

    def __init__(self, name, n_intent, n_cause):
        super().__init__()
        self.encoder = AutoModel.from_pretrained(name)
        h = self.encoder.config.hidden_size
        self.drop = nn.Dropout(0.1)
        self.intent_head, self.cause_head = nn.Linear(h, n_intent), nn.Linear(h, n_cause)

    def forward(self, input_ids, attention_mask):
        cls = self.drop(self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state[:, 0])
        return self.intent_head(cls), self.cause_head(cls)


def _weights(y, n):
    """Pesos 'balanced' como en el TF-IDF (class_weight='balanced')."""
    counts = np.bincount(y, minlength=n).astype(float)
    return torch.tensor(len(y) / (n * np.maximum(counts, 1)), dtype=torch.float)


def _batches(enc, yi, yc, size, shuffle, rng=None):
    idx = rng.permutation(len(yi)) if shuffle else np.arange(len(yi))
    for s in range(0, len(idx), size):
        b = idx[s:s + size]
        yield enc["input_ids"][b], enc["attention_mask"][b], torch.tensor(yi[b]), torch.tensor(yc[b])


@torch.no_grad()
def _proba(model, tok, texts, max_len, size=128):
    model.eval()
    pi, pc = [], []
    for s in range(0, len(texts), size):
        enc = tok(texts[s:s + size], padding=True, truncation=True, max_length=max_len, return_tensors="pt")
        li, lc = model(enc["input_ids"], enc["attention_mask"])
        pi.append(li.softmax(-1).numpy()); pc.append(lc.softmax(-1).numpy())
    return np.concatenate(pi), np.concatenate(pc)


class Bundle:
    """Envuelve el Transformer con la misma interfaz que el bundle TF-IDF (predict_proba / classes_)."""

    def __init__(self, model, tok, max_len, intents, causes, threshold=0.0):
        self.model, self.tok, self.max_len, self.threshold = model, tok, max_len, threshold
        self.intents, self.causes = np.array(intents, dtype=object), np.array(causes, dtype=object)

    def predict(self, texts):
        pi, pc = _proba(self.model, self.tok, list(texts), self.max_len)
        intent = self.intents[pi.argmax(1)].copy()
        intent[pi.max(1) < self.threshold] = "fuera"
        return intent, self.causes[pc.argmax(1)]


def run(model_name=MODEL_NAME, epochs=4, batch=32, lr=5e-5, max_len=40, log=print, save=True):
    torch.manual_seed(SEED); np.random.seed(SEED)
    data, nat = D.build(seed=SEED), D.natural()
    intents, causes = list(D.INTENTS), list(D.CAUSES)
    ii, ci = {k: i for i, k in enumerate(intents)}, {k: i for i, k in enumerate(causes)}
    Xtr, ytr_i, ytr_c = TA.columns(data["train"])
    Xva, yva_i, yva_c = TA.columns(data["val"])
    ytr_i, ytr_c = np.array([ii[y] for y in ytr_i]), np.array([ci[y] for y in ytr_c])
    vi, vc = np.array([ii[y] for y in yva_i]), np.array([ci[y] for y in yva_c])

    tok = AutoTokenizer.from_pretrained(model_name)
    model = MultiTask(model_name, len(intents), len(causes))
    n_params = sum(p.numel() for p in model.parameters())
    log(f"Modelo: {model_name} | parámetros: {n_params / 1e6:.1f} M | hilos CPU: {torch.get_num_threads()}")
    enc_tr = tok(Xtr, padding="max_length", truncation=True, max_length=max_len, return_tensors="pt")
    enc_va = tok(Xva, padding="max_length", truncation=True, max_length=max_len, return_tensors="pt")
    loss_i, loss_c = nn.CrossEntropyLoss(weight=_weights(ytr_i, len(intents))), nn.CrossEntropyLoss(weight=_weights(ytr_c, len(causes)))
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    steps = epochs * int(np.ceil(len(Xtr) / batch))
    sched = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)
    rng = np.random.RandomState(SEED)

    history, best, t0 = [], None, time.time()
    for ep in range(1, epochs + 1):
        model.train(); tot, n = 0.0, 0
        for step, (ids, am, yi, yc) in enumerate(_batches(enc_tr, ytr_i, ytr_c, batch, True, rng), 1):
            li, lc = model(ids, am)
            loss = loss_i(li, yi) + loss_c(lc, yc)
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step()
            tot += loss.item() * len(yi); n += len(yi)
            if step % 40 == 0:
                log(f"  época {ep} paso {step}: pérdida {tot / n:.3f} ({time.time() - t0:.0f} s)")
        model.eval(); vtot = 0.0
        with torch.no_grad():
            for ids, am, yi, yc in _batches(enc_va, vi, vc, 128, False):
                li, lc = model(ids, am)
                vtot += (loss_i(li, yi) + loss_c(lc, yc)).item() * len(yi)
        pi, pc = _proba(model, tok, Xva, max_len)
        fi, fc = f1_score(vi, pi.argmax(1), average="macro"), f1_score(vc, pc.argmax(1), average="macro")
        row = {"epoch": ep, "train_loss": tot / n, "val_loss": vtot / len(vi), "val_intent_macro_f1": float(fi),
               "val_cause_macro_f1": float(fc), "seconds": round(time.time() - t0)}
        history.append(row); log(row)
        if best is None or (fi + fc) / 2 > best[0] + 1e-9:
            best = ((fi + fc) / 2, ep, {k: v.detach().clone() for k, v in model.state_dict().items()})
    model.load_state_dict(best[2])
    log(f"Mejor época según validación: {best[1]}")

    bundle = Bundle(model, tok, max_len, intents, causes)
    cands = []
    for t in (0.0, 0.3, 0.4, 0.5, 0.6):
        bundle.threshold = t
        cands.append((float(f1_score(yva_i, bundle.predict(Xva)[0], average="macro")), -t, t))
    bundle.threshold = max(cands)[2]
    log(f"Umbral de rechazo (validación): {bundle.threshold}")

    tfidf = joblib.load(ROOT / "models/asistente_lenguaje.joblib")
    out = {"model": model_name, "parameters_millions": round(n_params / 1e6, 1), "epochs": epochs, "batch": batch, "lr": lr,
           "max_len": max_len, "best_epoch": best[1], "reject_threshold": bundle.threshold, "history": history,
           "train_seconds": round(time.time() - t0)}
    for name, rows in (("test_plantillas_no_vistas", data["test"]), ("natural_a_mano", nat)):
        X, y_i, y_c = TA.columns(rows)
        ti, tc = bundle.predict(X)
        fi_, fc_, _, _ = TA.predict(tfidf, X)
        bi, bc = TA.baseline(rows)
        out[name] = {"transformer": TA.metrics(y_i, y_c, ti, tc), "tfidf_logistica": TA.metrics(y_i, y_c, fi_, fc_),
                     "linea_base_similitud": TA.metrics(y_i, y_c, bi, bc)}
        if name == "natural_a_mano":
            out[name]["errores_transformer"] = [{"texto": t, "esperado": [a, b], "predicho": [str(p), str(q)]}
                                                for (t, a, b), p, q in zip(rows, ti, tc) if (p, q) != (a, b)]
    if save:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), OUT_DIR / "pesos.pt")
        tok.save_pretrained(OUT_DIR)
        (OUT_DIR / "config_asistente.json").write_text(json.dumps({"base": model_name, "max_len": max_len, "intents": intents, "causes": causes,
                                                                    "threshold": bundle.threshold}, indent=2), encoding="utf-8")
        REPORT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        log(f"Guardado: {OUT_DIR.relative_to(ROOT)} y {REPORT.relative_to(ROOT)}")
    return out, bundle


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODEL_NAME)
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=5e-5)
    a = ap.parse_args()
    out, _ = run(a.model, a.epochs, a.batch, a.lr)
    for k in ("test_plantillas_no_vistas", "natural_a_mano"):
        print(k, json.dumps({m: out[k][m] for m in ("transformer", "tfidf_logistica", "linea_base_similitud")}, indent=1))


if __name__ == "__main__":
    main()
