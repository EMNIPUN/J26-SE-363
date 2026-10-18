"""Run the validation phase of the clean-data retrain for one or more factors.

    python run_validation.py consistency task_complexity effort
Writes, per factor, training/results/{baseline_predictions,tuning_predictions}.csv and settings.json under <factor>/clean/.
"""
import sys

import retrain
from retrain_configs import CONFIGS

if __name__ == "__main__":
    for name in sys.argv[1:]:
        cfg = CONFIGS[name]()
        results = cfg.factor().results
        print(f"== {name}: baselines", flush=True)
        retrain.run_baselines(cfg, results)
        print(f"== {name}: tuning", flush=True)
        retrain.run_validation(name, results)
        print(f"== {name}: done", flush=True)
