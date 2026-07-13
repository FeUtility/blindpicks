import pandas as pd

matchup_stats = pd.read_csv("matchup_stats.csv")

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

for cutoff in [8, 15, 20, 25, 30]:
    survived = (summary["num_matchups"] >= cutoff).sum()
    print(f"Minimum {cutoff} matchups: {survived} champion/role combos survive")