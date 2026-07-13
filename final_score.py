import pandas as pd
import numpy as np

df = pd.read_csv("full_match_data.csv")
df = df[df["patch"].str.startswith("16.12")]

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

print("Calculating lane variance...")
lane_merge = df.merge(df, on=["match_id", "role"], suffixes=("", "_opp"))
lane_merge = lane_merge[lane_merge["puuid"] != lane_merge["puuid_opp"]]
lane_var = weighted_var(lane_merge[["champion", "role", "champion_opp", "win"]].rename(columns={"champion_opp": "vs"}), ["champion", "role", "vs"])
lane_var = lane_var.rename(columns={"variance": "lane_variance", "num_pairs": "lane_pairs", "total_games": "lane_games"})

print("Calculating enemy team variance...")
enemy_merge = df.merge(df, on="match_id", suffixes=("", "_opp"))
enemy_merge = enemy_merge[enemy_merge["win"] != enemy_merge["win_opp"]]
enemy_var = weighted_var(enemy_merge[["champion", "role", "champion_opp", "win"]].rename(columns={"champion_opp": "vs"}), ["champion", "role", "vs"])
enemy_var = enemy_var.rename(columns={"variance": "enemy_variance", "num_pairs": "enemy_pairs", "total_games": "enemy_games"})

print("Calculating ally synergy variance...")
ally_merge = df.merge(df, on="match_id", suffixes=("", "_opp"))
ally_merge = ally_merge[(ally_merge["win"] == ally_merge["win_opp"]) & (ally_merge["puuid"] != ally_merge["puuid_opp"])]
ally_var = weighted_var(ally_merge[["champion", "role", "champion_opp", "win"]].rename(columns={"champion_opp": "vs"}), ["champion", "role", "vs"])
ally_var = ally_var.rename(columns={"variance": "ally_variance", "num_pairs": "ally_pairs", "total_games": "ally_games"})

overall = df.groupby(["champion", "role"]).agg(winrate=("win", "mean"), games=("win", "count")).reset_index()

combined = overall.merge(lane_var[["champion","role","lane_variance","lane_pairs"]], on=["champion","role"], how="inner")
combined = combined.merge(enemy_var[["champion","role","enemy_variance","enemy_pairs"]], on=["champion","role"], how="inner")
combined = combined.merge(ally_var[["champion","role","ally_variance","ally_pairs"]], on=["champion","role"], how="inner")

def normalize_consistency(col):
    return 100 * (1 - (col - col.min()) / (col.max() - col.min()))

combined["lane_consistency"] = normalize_consistency(combined["lane_variance"])
combined["enemy_consistency"] = normalize_consistency(combined["enemy_variance"])
combined["ally_consistency"] = normalize_consistency(combined["ally_variance"])

combined["consistency_score"] = (
    0.20 * combined["lane_consistency"] +
    0.40 * combined["enemy_consistency"] +
    0.40 * combined["ally_consistency"]
)

combined["winrate_score"] = ((combined["winrate"] - 0.40) / 0.20 * 100).clip(0, 100)

combined["blind_score"] = (0.5 * combined["winrate_score"] + 0.5 * combined["consistency_score"]).round(1)

def tier(n):
    if n >= 25:
        return "High"
    elif n >= 10:
        return "Moderate"
    else:
        return "Low"

combined["lane_tier"] = combined["lane_pairs"].apply(tier)
combined["enemy_tier"] = combined["enemy_pairs"].apply(tier)
combined["ally_tier"] = combined["ally_pairs"].apply(tier)

tier_rank = {"Low": 0, "Moderate": 1, "High": 2}
combined["confidence_tier"] = combined.apply(
    lambda r: min([r["lane_tier"], r["enemy_tier"], r["ally_tier"]], key=lambda t: tier_rank[t]), axis=1
)

final = combined[["champion","role","blind_score","winrate","games","lane_consistency","enemy_consistency","ally_consistency","confidence_tier"]]
tier_order = {"High": 0, "Moderate": 1, "Low": 2}
final["tier_sort"] = final["confidence_tier"].map(tier_order)
final = final.sort_values(["tier_sort", "blind_score"], ascending=[True, False])
final = final.drop(columns="tier_sort")
final.to_csv("final_blind_scores.csv", index=False)

print(f"Total champion/role combos scored: {len(final)}")
print()
print("Top 15 by Blind Score:")
print(final.head(15).to_string())
