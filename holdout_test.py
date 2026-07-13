import pandas as pd
import numpy as np

df = pd.read_csv("full_match_data.csv")
df = df[df["patch"].str.startswith("16.12")]

match_ids = df["match_id"].unique()
rng = np.random.default_rng(42)
shuffled = rng.permutation(match_ids)
half = len(shuffled) // 2
set_a = set(shuffled[:half])
set_b = set(shuffled[half:])

df_a = df[df["match_id"].isin(set_a)]
df_b = df[df["match_id"].isin(set_b)]

print(f"Total matches: {len(match_ids)}, Half A: {len(set_a)}, Half B: {len(set_b)}")

def weighted_var(group_df, key_cols):
    stats = group_df.groupby(key_cols)["win"].agg(["mean", "count"]).rename(columns={"mean": "winrate", "count": "games"})
    stats = stats[stats["games"] >= 20].reset_index()
    def combine(g):
        total = g["games"].sum()
        avg = (g["winrate"] * g["games"]).sum() / total
        var = ((g["winrate"] - avg) ** 2 * g["games"]).sum() / total
        return pd.Series({"variance": var, "total_games": total, "num_pairs": len(g)})
    out = stats.groupby(["champion", "role"]).apply(combine).reset_index()
    return out

print("Calculating lane variance (Half A)...")
lane_merge = df_a.merge(df_a, on=["match_id", "role"], suffixes=("", "_opp"))
lane_merge = lane_merge[lane_merge["puuid"] != lane_merge["puuid_opp"]]
lane_var = weighted_var(lane_merge[["champion", "role", "champion_opp", "win"]].rename(columns={"champion_opp": "vs"}), ["champion", "role", "vs"])
lane_var = lane_var.rename(columns={"variance": "lane_variance"})

print("Calculating enemy team variance (Half A)...")
enemy_merge = df_a.merge(df_a, on="match_id", suffixes=("", "_opp"))
enemy_merge = enemy_merge[enemy_merge["win"] != enemy_merge["win_opp"]]
enemy_var = weighted_var(enemy_merge[["champion", "role", "champion_opp", "win"]].rename(columns={"champion_opp": "vs"}), ["champion", "role", "vs"])
enemy_var = enemy_var.rename(columns={"variance": "enemy_variance"})

print("Calculating ally synergy variance (Half A)...")
ally_merge = df_a.merge(df_a, on="match_id", suffixes=("", "_opp"))
ally_merge = ally_merge[(ally_merge["win"] == ally_merge["win_opp"]) & (ally_merge["puuid"] != ally_merge["puuid_opp"])]
ally_var = weighted_var(ally_merge[["champion", "role", "champion_opp", "win"]].rename(columns={"champion_opp": "vs"}), ["champion", "role", "vs"])
ally_var = ally_var.rename(columns={"variance": "ally_variance"})

overall_wr = df.groupby(["champion", "role"])["win"].mean().reset_index().rename(columns={"win": "overall_winrate"})
b_wr = df_b.groupby(["champion", "role"]).agg(winrate_b=("win", "mean"), games_b=("win", "count")).reset_index()
b_wr = b_wr[b_wr["games_b"] >= 100]

combined = lane_var[["champion", "role", "lane_variance"]].merge(
    enemy_var[["champion", "role", "enemy_variance"]], on=["champion", "role"], how="inner"
).merge(
    ally_var[["champion", "role", "ally_variance"]], on=["champion", "role"], how="inner"
).merge(overall_wr, on=["champion", "role"], how="inner").merge(b_wr, on=["champion", "role"], how="inner")

combined["deviation"] = (combined["winrate_b"] - combined["overall_winrate"]).abs()

combined.to_csv("holdout_test_results.csv", index=False)

print()
print(f"Champion/role combos with enough data for all 3 metrics: {len(combined)}")
print()
print("Correlation between each variance type and real winrate instability (higher = more predictive):")
print("Lane variance:  ", round(combined["lane_variance"].corr(combined["deviation"]), 4))
print("Enemy variance: ", round(combined["enemy_variance"].corr(combined["deviation"]), 4))
print("Ally variance:  ", round(combined["ally_variance"].corr(combined["deviation"]), 4))
