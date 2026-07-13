import requests
import csv
import time
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("RIOT_API_KEY")
headers = {"X-Riot-Token": api_key}

start_time = 1780963200
end_time = 1782259199

players = []
with open("masterplus_full_list.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["tier"] == "MASTER":
            players.append(row)

print(f"Loaded {len(players)} total Master players")

completed_puuids = set()
if os.path.exists("completed_players.txt"):
    with open("completed_players.txt", "r", encoding="utf-8") as f:
        completed_puuids = set(line.strip() for line in f)
print(f"Already completed: {len(completed_puuids)} players")

all_match_data = []
seen_match_ids = set()
if os.path.exists("master_match_data.csv"):
    with open("master_match_data.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_match_data.append(row)
            seen_match_ids.add(row["match_id"])
print(f"Existing rows loaded: {len(all_match_data)}")

remaining_players = [p for p in players if p["puuid"] not in completed_puuids]
print(f"Remaining to process: {len(remaining_players)}")

completed_file = open("completed_players.txt", "a", encoding="utf-8")

for i, player in enumerate(remaining_players):
    puuid = player["puuid"]
    match_ids_url = f"https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params = {"startTime": start_time, "endTime": end_time, "queue": 420, "count": 100}
    resp = requests.get(match_ids_url, headers=headers, params=params)

    if resp.status_code != 200:
        print(f"ERROR status {resp.status_code} on player {i+1} - likely expired key. Stopping.")
        print("Raw response:", resp.text[:200])
        break

    match_ids = resp.json()
    time.sleep(1.2)

    new_ids = [m for m in match_ids if m not in seen_match_ids]
    print(f"[{i+1}/{len(remaining_players)}] {len(match_ids)} matches found, {len(new_ids)} new")

    for match_id in new_ids:
        seen_match_ids.add(match_id)
        match_url = f"https://americas.api.riotgames.com/lol/match/v5/matches/{match_id}"
        match_resp = requests.get(match_url, headers=headers)

        if match_resp.status_code != 200:
            print(f"  Match pull failed, status {match_resp.status_code} - stopping.")
            break

        match_json = match_resp.json()
        patch = match_json["info"]["gameVersion"]

        for p in match_json["info"]["participants"]:
            all_match_data.append({
                "match_id": match_id,
                "patch": patch,
                "champion": p["championName"],
                "role": p["teamPosition"],
                "win": p["win"],
                "puuid": p["puuid"]
            })

        time.sleep(1.2)

    completed_file.write(puuid + "\n")
    completed_file.flush()

    if (i + 1) % 25 == 0:
        with open("master_match_data.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_match_data[0].keys())
            writer.writeheader()
            writer.writerows(all_match_data)
        print(f"  --- Progress saved: {len(all_match_data)} total rows ---")

completed_file.close()

if all_match_data:
    with open("master_match_data.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_match_data[0].keys())
        writer.writeheader()
        writer.writerows(all_match_data)

print(f"Stopped/finished. Total rows: {len(all_match_data)}")
