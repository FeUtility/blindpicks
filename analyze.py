import pandas as pd

df = pd.read_csv("full_match_data.csv")
df = df[df["patch"].str.startswith("16.12")]

print("Rows after filtering to correct patch:", len(df))

merged = df.merge(df, on=["match_id", "role"], suffixes=("", "_opp"))
merged = merged[merged["puuid"] != merged["puuid_opp"]]
matchups = merged[["champion", "role", "champion_opp", "win"]]

matchup_stats = matchups.groupby(["champion", "role", "champion_opp"])["win"].agg(["mean", "count"])
matchup_stats = matchup_stats.rename(columns={"mean": "winrate", "count": "games"})
matchup_stats = matchup_stats[matchup_stats["games"] >= 20]
matchup_stats = matchup_stats.reset_index()
matchup_stats.to_csv("matchup_stats.csv", index=False)
print("Saved raw matchup stats to matchup_stats.csv")
print("Total reliable matchups found:", len(matchup_stats))

def weighted_stats(group):
    total_games = group["games"].sum()
    weighted_avg = (group["winrate"] * group["games"]).sum() / total_games
    weighted_variance = ((group["winrate"] - weighted_avg) ** 2 * group["games"]).sum() / total_games
    return pd.Series({
        "weighted_winrate": weighted_avg,
        "weighted_variance": weighted_variance,
        "total_games": total_games,
        "num_matchups": len(group)
    })

summary = matchup_stats.groupby(["champion", "role"]).apply(weighted_stats).reset_index()

def confidence_tier(n):
    if n >= 25:
        return "High Confidence"
    elif n >= 10:
        return "Moderate Confidence"
    else:
        return "Low Confidence / Limited Data"

summary["confidence_tier"] = summary["num_matchups"].apply(confidence_tier)

summary = summary.sort_values(["confidence_tier", "weighted_variance"])
summary.to_csv("blind_pick_summary.csv", index=False)

print("Saved final tiered summary to blind_pick_summary.csv")
print()
print("Counts per tier:")
print(summary["confidence_tier"].value_counts())
print()
print("Sample of High Confidence tier, sorted by lowest variance:")
print(summary[summary["confidence_tier"] == "High Confidence"].head(15).to_string())
