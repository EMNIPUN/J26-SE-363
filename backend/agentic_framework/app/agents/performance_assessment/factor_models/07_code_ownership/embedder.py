"""A frozen pretrained code-text encoder that turns text into a vector (proposal 3.1.8: "a frozen pretrained code-text encoder ... with a lightweight regression head").

Nothing is trained here. The encoder is loaded lazily, so importing this module costs nothing and the agent can run without torch installed: ``Encoder.load()`` then
raises ``ModelUnavailable`` and the factor reports "not available" instead of a made-up score.

Mean pooling of the last hidden layer over non-padding tokens (the pooling UniXcoder and CodeBERT use for text/code embeddings), L2-normalised.
"""

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMES = {"unixcoder": "microsoft/unixcoder-base", "codebert": "microsoft/codebert-base", "mpnet": "sentence-transformers/all-mpnet-base-v2"}


class ModelUnavailable(RuntimeError):
    """Raised when the encoder or its libraries cannot be loaded; the agent turns it into 'factor not available'."""


class Encoder:
    def __init__(self, key="unixcoder", max_tokens=512, threads=None):
        if key not in NAMES:
            raise ValueError(f"unknown encoder {key!r}; choose from {sorted(NAMES)}")
        self.key, self.max_tokens, self.threads = key, max_tokens, threads
        self.name = self._local(key) or NAMES[key]
        self._tok = self._model = self._torch = None

    @staticmethod
    def _local(key):
        """A folder with the encoder's files, used instead of the hub when present: $KO_ENCODER_DIR/<key>, or training/dataset/cache/models/<hub name>."""
        for base in (os.environ.get("KO_ENCODER_DIR"), HERE / "training" / "dataset" / "cache" / "models"):
            if base:
                for cand in (Path(base) / key, Path(base) / NAMES[key].split("/")[-1]):
                    if (cand / "config.json").exists() and any(cand.glob("*.bin")) | any(cand.glob("*.safetensors")):
                        return str(cand)
        return None

    def load(self):
        if self._model is not None:
            return self
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as e:
            raise ModelUnavailable(f"torch/transformers are not installed: {e}") from e
        try:
            self._tok = AutoTokenizer.from_pretrained(self.name)
            self._model = AutoModel.from_pretrained(self.name).eval()
        except Exception as e:  # offline and not cached, or a damaged cache
            raise ModelUnavailable(f"encoder {self.name} could not be loaded: {e}") from e
        if self.threads:
            torch.set_num_threads(self.threads)
        self._torch = torch
        return self

    def embed(self, texts, batch_size=16):
        """(n, dim) float32 array, one L2-normalised vector per text."""
        import numpy as np
        self.load()
        torch, out = self._torch, []
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                chunk = [t if t.strip() else " " for t in texts[i:i + batch_size]]
                enc = self._tok(chunk, padding=True, truncation=True, max_length=self.max_tokens, return_tensors="pt")
                hidden = self._model(**enc).last_hidden_state
                mask = enc["attention_mask"].unsqueeze(-1).to(hidden.dtype)
                pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1)
                pooled = torch.nn.functional.normalize(pooled, dim=-1)
                out.append(pooled.cpu().numpy())
        return np.vstack(out).astype("float32")
