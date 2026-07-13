import pandas as pd

gmchall = pd.read_csv("gmchall_match_data.csv")
master = pd.read_csv("master_match_data.csv")

combined = pd.concat([gmchall, master], ignore_index=True)

print("GM+Chall rows:", len(gmchall))
print("Master rows:", len(master))
print("Combined total rows:", len(combined))

before = len(combined)
combined = combined.drop_duplicates(subset=["match_id", "puuid"])
after = len(combined)
print(f"Removed {before - after} duplicate rows")

combined.to_csv("full_match_data.csv", index=False)
print("Saved deduplicated combined file to full_match_data.csv")