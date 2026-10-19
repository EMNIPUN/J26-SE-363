"""Downloads the public review-comment datasets into training/dataset/raw/ (not committed: GPL-3.0 and MIT data stay with their owners).

    python download_data.py
"""
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "dataset" / "raw"
OPENDEV = "https://raw.githubusercontent.com/WSU-SEAL/CR-usefulness-EMSE/main/Regression/usefulness_dataset.csv"
REVHELPER = "https://raw.githubusercontent.com/masud-technope/RevHelper-Replication-Package-MSR2017/master/{part}/{name}.txt"
FILES = {"opendev.csv": OPENDEV,
         "revhelper_train_corpus-useful.txt": REVHELPER.format(part="comparative-study", name="corpus-useful"),
         "revhelper_train_corpus-non-useful.txt": REVHELPER.format(part="comparative-study", name="corpus-non-useful"),
         "revhelper_val_corpus-useful.txt": REVHELPER.format(part="validation", name="corpus-useful"),
         "revhelper_val_corpus-non-useful.txt": REVHELPER.format(part="validation", name="corpus-non-useful")}

if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        target = RAW / name
        if not target.exists():
            urllib.request.urlretrieve(url, target)
        print(name, target.stat().st_size, "bytes")
