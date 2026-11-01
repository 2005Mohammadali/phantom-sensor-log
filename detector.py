import numpy as np
from config import BASELINE_SAMPLES, USE_TABPFN, WHISPER, POLTERGEIST, BANSHEE

F = ["cpu", "ram", "procs", "spawns", "net_kb"]
LABEL = {"cpu": "CPU load %", "ram": "memory use %", "procs": "running processes",
         "spawns": "new processes just spawned", "net_kb": "outbound network KB/s"}
FLOOR = np.array([3, 1, 5, 1, 20])   # smallest "normal wobble" per sensor

class Detector:
    def __init__(self):
        self.rows, self.med, self.tp = [], None, []

    @property
    def ready(self):
        return len(self.rows) >= BASELINE_SAMPLES

    def add_baseline(self, row):
        self.rows.append([row[f] for f in F])

    def fit(self):
        X = np.array(self.rows, dtype=float)
        self.med = np.median(X, 0)
        self.mad = np.maximum(np.median(np.abs(X - self.med), 0) * 1.4826, FLOOR)
        if USE_TABPFN:
            try:
                from tabpfn import TabPFNRegressor
                for j in (0, 4):   # learn what CPU and network "should" be given the other sensors
                    others = [k for k in range(len(F)) if k != j]
                    m = TabPFNRegressor()
                    m.fit(X[:, others], X[:, j])
                    res = X[:, j] - m.predict(X[:, others])
                    self.tp.append((j, others, m, max(res.std(), self.mad[j])))
                print("TabPFN loaded.")
            except Exception as e:
                print("TabPFN unavailable, using robust z-score only:", e)
                self.tp = []

    def score(self, row):
        x = np.array([row[f] for f in F], dtype=float)
        z = np.abs(x - self.med) / self.mad
        for j, others, m, sd in self.tp:
            pred = m.predict(x[others].reshape(1, -1))[0]
            z[j] = max(z[j], abs(x[j] - pred) / sd)
        notes = [f"{LABEL[F[i]]}: {x[i]:.0f} (usually {self.med[i]:.0f})"
                 for i in range(len(F)) if z[i] >= 3]
        return float(z.max()), "; ".join(notes) or "faint unrest across several sensors"

    @staticmethod
    def tier(s):
        return "Banshee" if s >= BANSHEE else "Poltergeist" if s >= POLTERGEIST else "Whisper"