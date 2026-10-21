"""A column-block transformer for the Code Ownership heads.

A feature matrix is "embedding columns | hand-built columns". Appending 12 hand-built columns to 768 embedding columns lets the embedding noise drown them in a ridge or
kernel head, so the two blocks are treated separately: the embedding block can be compressed (PCA) and the hand-built block is multiplied by a weight ``hw`` (chosen by the
inner folds, like every other setting). Defined in its own module so that a trained head saved with joblib can be loaded by the agent (score.py registers this module
under the name ``ko_blocks`` before loading).
"""
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.decomposition import PCA


class Blocks(BaseEstimator, TransformerMixin):
    def __init__(self, n_hand=0, pca=None, hw=1.0, seed=0):
        self.n_hand, self.pca, self.hw, self.seed = n_hand, pca, hw, seed

    def _split(self, X):
        k = X.shape[1] - self.n_hand
        return X[:, :k], X[:, k:]

    def fit(self, X, y=None):
        emb, _ = self._split(np.asarray(X, float))
        self.pca_ = PCA(n_components=min(self.pca, emb.shape[1], emb.shape[0] - 1), random_state=self.seed).fit(emb) if self.pca and emb.shape[1] else None
        return self

    def transform(self, X):
        emb, hand = self._split(np.asarray(X, float))
        if self.pca_ is not None:
            emb = self.pca_.transform(emb)
        return np.hstack([emb, hand * self.hw])
