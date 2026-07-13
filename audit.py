import pandas as pd

df = pd.read_csv("full_match_data.csv")
df = df[df["patch"].str.startswith("16.12")]

raw_counts = df.groupby(["champion", "role"]).size().reset_index(name="total_raw_games")

matchup_stats = pd.read_csv("matchup_stats.csv")
matchup_counts = matchup_stats.groupby(["champion", "role"]).size().reset_index(name="reliable_matchups")

summary = pd.read_csv("blind_pick_summary.csv")
final_cut_set = set(zip(summary["champion"], summary["role"]))

audit = raw_counts.merge(matchup_counts, on=["champion", "role"], how="left")
audit["reliable_matchups"] = audit["reliable_matchups"].fillna(0).astype(int)
audit["made_final_cut"] = audit.apply(lambda r: (r["champion"], r["role"]) in final_cut_set, axis=1)

audit = audit.sort_values("total_raw_games", ascending=False)
audit.to_csv("data_audit.csv", index=False)

print("Total champion/role combos found in raw data:", len(audit))
print("Made it into final summary:", audit["made_final_cut"].sum())
print("Did NOT make final cut:", (~audit["made_final_cut"]).sum())
print()
print("Sample of ones that did NOT make the cut, sorted by raw games (most data, still excluded):")
not_cut = audit[audit["made_final_cut"] == False]
print(not_cut.head(20).to_string())
