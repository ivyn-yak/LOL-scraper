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
            "count": 100,  # max per request
            "type": "ranked"
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
    return int((datetime.datetime.now() - datetime.timedelta(days=30*3)).timestamp())

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

def filter_match_data(match, info, participants):

    # flatten all 10 participants into column-wise structure
    flattened = {}
    for i, p in enumerate(participants, start=1):
        flattened.update({
            f"p{i}_teamId": p.get("teamId", None),
            f"p{i}_championName": p.get("championName", "NA"),
            f"p{i}_teamPosition": p.get("teamPosition", "NA"),
        })
    
    # base match info (shared across all players)
    match_info = {
        "gameId": info.get("gameId", -1),
        "gameStartTimestamp": info.get("gameStartTimestamp", 0),
        "gameDuration": info.get("gameDuration", 0),
        "gameMode": info.get("gameMode", "NA"),
        "gameType": info.get("gameType", "NA"),
        "gameVersion": info.get("gameVersion", "NA"),
        "teamId100Win": 1 if info.get("teams", [{}])[0].get("win", None) else 0
    }
    
    # combine both
    filtered_match = pd.DataFrame([{**match_info, **flattened}])
    
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

        participants = info.get("participants", [])
        
        if participants:
            match = pd.DataFrame([{
                # 🧠 --- Match Context ---
                "matchId": match_id,
                "puuid": puuid,
            }])

            filtered_match = filter_match_data(match, info, participants)

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