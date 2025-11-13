from collections import Counter
from typing import Counter as CounterType

c: CounterType[str] = Counter()
try:
    for line in open("ruff-remaining.txt", "r", encoding="utf-8"):
        parts = line.split()
        if parts:
            c[parts[0]] += 1
    print("Top 20 files with most remaining Ruff issues:")
    for f, n in c.most_common(20):
        print(n, f)
except FileNotFoundError:
    print("ruff-remaining.txt not found.")
