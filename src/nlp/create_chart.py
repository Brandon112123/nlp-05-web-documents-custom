"""Create a chart comparing military conflict durations."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_csv("data/processed/military_conflicts.csv")

df.plot.bar(
    x="conflict",
    y="duration_years",
    color="steelblue",
    legend=False,
)

plt.title("Military Conflict Duration")
plt.ylabel("Years")
plt.xlabel("")
plt.xticks(rotation=0)
plt.tight_layout()

Path("docs/images").mkdir(parents=True, exist_ok=True)
plt.savefig("docs/images/military_conflicts_chart.png")
plt.close()

print("Chart created successfully!")
