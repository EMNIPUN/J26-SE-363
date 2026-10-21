"""Nested, grouped tuning of every (encoder, feature set, head) of PROTOCOL.md on the development functions. Resumable: finished combinations are kept.

    python run_tuning.py unixcoder codebert mpnet        (from training/helpers/; results go to ../experiments/exp01_baseline_pipeline/results/)

Writes tuning_preds.pkl: {"<encoder>|<set>|<head>": {"pred": out-of-fold predictions for the development rows, "chosen": settings chosen per outer fold}}.
"""
import pickle
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ko_data as K  # noqa: E402
import ko_models as M  # noqa: E402

RESULTS = HERE.parent / "experiments" / "exp01_baseline_pipeline" / "results"
HEADS = ["ridge", "svr", "kernel_ridge", "forest", "boosting", "mlp"]


def run(encoders, workers=10):
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / "tuning_preds.pkl"
    done = pickle.load(open(path, "rb")) if path.exists() else {}
    d = K.load()
    dev = d[d.role == "dev"].reset_index(drop=True)
    y, groups, folds = dev.score.to_numpy(), dev.snippet_id.to_numpy(), dev.fold.to_numpy()
    H = K.hand_features(dev)
    for enc in encoders:
        E = K.embeddings(enc, dev)
        sets = K.feature_sets(E, H)
        for sname, X in sets.items():
            for head in HEADS:
                key = f"{enc}|{sname}|{head}"
                if key in done:
                    continue
                t = time.time()
                pred, chosen = M.nested(head, np.asarray(X, float), y, groups, folds, workers=workers, n_hand=(H.shape[1] if sname.endswith("+H") else 0))
                done[key] = {"pred": pred, "chosen": chosen}
                pickle.dump(done, open(path, "wb"))
                rmse = float(np.sqrt(np.mean((pred - y) ** 2)))
                print(f"{key:40s} RMSE {rmse:.3f}  {time.time() - t:5.1f}s", flush=True)
    return done


if __name__ == "__main__":
    run(sys.argv[1:] or ["mpnet"])
