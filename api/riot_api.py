import requests
from dotenv import load_dotenv
import os
import json
import time
import datetime
from pathlib import Path
import pandas as pd
from collections import deque

load_dotenv()

RIOT_API_KEY = os.getenv("RIOT_API_KEY")
REGION_ROUTING = os.getenv("REGION_ROUTING")
MATCH_REGION_ROUTING = os.getenv("MATCH_REGION_ROUTING")
PLATFORM_ROUTING = os.getenv("PLATFORM_ROUTING")

def get_puuid(game_name, tag_line):
    url = f"https://{REGION_ROUTING}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    r = requests.get(url, params={"api_key" : RIOT_API_KEY})
    return r.json()["puuid"]

#LEAGUE-V4
def get_ranked_stats(puuid):
    url = f"https://{PLATFORM_ROUTING}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    r = requests.get(url, params={"api_key" : RIOT_API_KEY})
    return r.json()

#match-v5
def get_match_ids(puuid):
    all_matches = []
    start = 0
    url = f"https://{MATCH_REGION_ROUTING}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"

    while True:
        params = {
            "api_key" : RIOT_API_KEY,
            "startTime": get_start_time(),
            "start": start,
            "count": 100  # max per request
        }
        r = requests.get(url, params=params)
        match_ids = r.json()
    
        if not match_ids:  # no more matches
            break

        all_matches.extend(match_ids)
        start += 100  # move to next "page"
        
    return all_matches

def get_match(match_id):
    wait_for_rate_limit(MATCH_REGION_ROUTING)
    url = f"https://{MATCH_REGION_ROUTING}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    r = requests.get(url, params={"api_key": RIOT_API_KEY})
    
    if r.status_code == 429:
        retry = int(r.headers.get("Retry-After", 120))
        print(f"Rate limit hit, retrying in {retry}s...")
        time.sleep(retry)
        return get_match(match_id)
    r.raise_for_status()
    return r.json()

#champion-mastery-v4
def get_champion_masteries(puuid):
    url = f"https://{PLATFORM_ROUTING}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}"
    r = requests.get(url, params={"api_key" : RIOT_API_KEY})
    return r.json()

# utils
def get_start_time():
    return int((datetime.datetime.now() - datetime.timedelta(days=30*8)).timestamp())

def save_to_json(file_name, data):
    with open(file_name, "w") as file:
        json.dump(data, file, indent=4)
    print(f"{file_name} saved successfully")

# --- Rate Limit Settings ---
SHORT_LIMIT = 20
SHORT_WINDOW = 1
LONG_LIMIT = 100
LONG_WINDOW = 120

# Track request timestamps per region
request_log = {MATCH_REGION_ROUTING: deque()}

def wait_for_rate_limit(region):
    now = time.time()
    log = request_log[region]

    # remove old timestamps outside long window
    while log and now - log[0] > LONG_WINDOW:
        log.popleft()
    
    # short-term check
    recent_short = [t for t in log if now - t <= SHORT_WINDOW]
    if len(recent_short) >= SHORT_LIMIT:
        sleep_time = SHORT_WINDOW - (now - recent_short[0])
        time.sleep(max(sleep_time, 0))

    # long-term check
    if len(log) >= LONG_LIMIT:
        sleep_time = LONG_WINDOW - (now - log[0])
        time.sleep(max(sleep_time, 0))

    # record this request
    log.append(time.time())

def filter_match_data(match, info, p):
    filtered_match = pd.DataFrame([{
                "gameId": info.get("gameId", -1),
                "gameStartTimestamp": info.get("gameStartTimestamp", 0),
                "gameDuration": info.get("gameDuration", 0),
                "gameMode": info.get("gameMode", "NA"),
                "gameType": info.get("gameType", "NA"),
                "gameVersion": info.get("gameVersion", "NA"),
                "mapId": info.get("mapId", 0),
                "teamId": p.get("teamId", None),
                "win": p.get("win", None),
                "timePlayed": p.get("timePlayed", 0),

                # 👤 --- Player Info ---
                "championName": p.get("championName", "NA"),
                "champExperience": p.get("champExperience", 0),
                "champLevel": p.get("champLevel", 0),

                # 🪓 --- Combat ---
                "kills": p.get("kills", 0),
                "deaths": p.get("deaths", 0),
                "assists": p.get("assists", 0),
                "kda": p.get("kda", 0),
                "doubleKills": p.get("doubleKills", 0),
                "tripleKills": p.get("tripleKills", 0),
                "quadraKills": p.get("quadraKills", 0),
                "pentaKills": p.get("pentaKills", 0),
                "largestKillingSpree": p.get("largestKillingSpree", 0),
                "largestMultiKill": p.get("largestMultiKill", 0),

                # 💥 --- Damage ---
                "totalDamageDealt": p.get("totalDamageDealt", 0),
                "totalDamageDealtToChampions": p.get("totalDamageDealtToChampions", 0),
                "damageSelfMitigated": p.get("damageSelfMitigated", 0),
                "totalDamageTaken": p.get("totalDamageTaken", 0),
                "physicalDamageDealtToChampions": p.get("physicalDamageDealtToChampions", 0),
                "magicDamageDealtToChampions": p.get("magicDamageDealtToChampions", 0),
                "trueDamageDealtToChampions": p.get("trueDamageDealtToChampions", 0),
                "teamDamagePercentage": p.get("challenges", {}).get("teamDamagePercentage", 0),

                # 💰 --- Economy ---
                "goldEarned": p.get("goldEarned", 0),
                "goldSpent": p.get("goldSpent", 0),
                "goldPerMinute": p.get("challenges", {}).get("goldPerMinute", 0),

                # 👁️ --- Vision / Utility ---
                "visionScore": p.get("visionScore", 0),
                "wardsPlaced": p.get("wardsPlaced", 0),
                "wardsKilled": p.get("wardsKilled", 0),
                "wardTakedowns": p.get("challenges", {}).get("wardTakedowns", 0),
                "controlWardsPlaced": p.get("challenges", {}).get("controlWardsPlaced", 0),

                # 🎯 --- Objectives ---
                "turretKills": p.get("turretKills", 0),
                "inhibitorKills": p.get("inhibitorKills", 0),
                "dragonKills": p.get("dragonKills", 0),
                "baronKills": p.get("baronKills", 0),

                # 🏃 --- Mobility / Survivability ---
                "timeCCingOthers": p.get("timeCCingOthers", 0),
                "totalTimeCCDealt": p.get("totalTimeCCDealt", 0),
                "totalHeal": p.get("totalHeal", 0),
                "tookLargeDamageSurvived": p.get("challenges", {}).get("tookLargeDamageSurvived", 0),

                # 🗺️ --- Positioning / Strategy ---
                "lane": p.get("lane", "NA"),
                "role": p.get("role", "NA"),
            }])
    
    return pd.concat([match.reset_index(drop=True), filtered_match.reset_index(drop=True)], axis=1)

def save_match_data(match_ids, puuid, csv_file):
    for i, match_id in enumerate(match_ids):
        print(f"getting {i+1}/{len(match_ids)} match data for {puuid}")
        match_data = get_match(match_id)
        info = match_data.get("info", {})

        # check if it is a full length game
        if info.get("gameDuration", 0) < 1000:
            print(f"skipping match id ({match_id}): game time too short ({info.get('gameDuration')})")
            continue

        p = next((x for x in info.get("participants", []) if x.get("puuid") == puuid), None)

        if p:
            match = pd.DataFrame([{
                # 🧠 --- Match Context ---
                "matchId": match_id,
                "puuid": puuid,
            }])

            filtered_match = filter_match_data(match, info, p)

            # Append to CSV
            filtered_match.to_csv(csv_file, mode='a', index=False,
                    header=not os.path.exists(csv_file))  # write header only once
            
# main
def main():
    # create data folders
    cm_folder = Path(os.getenv("CM_FOLDER"))
    cm_folder.mkdir(parents=True, exist_ok=True)

    ranked_stats_folder = Path(os.getenv("RANKED_STATS_FOLDER"))
    ranked_stats_folder.mkdir(parents=True, exist_ok=True)

    csv_file = "matches.csv"

    for i in range(1, 6):
        game_name = os.getenv(f"GAME_NAME_{i}")
        tag_line = os.getenv(f"TAG_LINE_{i}")
        puuid = get_puuid(game_name, tag_line)
        print(f"\ngetting data for {puuid}\n")

        # save ranked stats data as json
        ranked = get_ranked_stats(puuid)
        ranked_file_name = ranked_stats_folder / f"{puuid}.json"
        save_to_json(ranked_file_name, ranked)

        # save champ masteries data as json
        cm = get_champion_masteries(puuid)
        cm_file_name = cm_folder / f"{puuid}.json"
        save_to_json(cm_file_name, cm)

        # save matches data as json
        match_ids = get_match_ids(puuid)
        save_match_data(match_ids, puuid, csv_file)


if __name__ == "__main__":
    main()