
# 🎮 League of Legends Data Collection & Analysis

This project collects **match**, **ranked**, and **champion mastery data** for players from the **Riot Games API**, and augments it with **meta statistics scraped from U.GG**.  
It is designed for **student esports teams** or data analysts who want to perform data-driven insights on player performance, champion choices, and win rate optimization.

---

## 🧱 Project Overview

The project consists of two main components:

1. **`riot_api.py`** — Fetches and filters player match, ranked, and mastery data from Riot’s official APIs.  
2. **`scraper.py`** — Uses Selenium to scrape champion statistics (win rate, pick rate, ban rate, etc.) from [U.GG](https://u.gg/).

All outputs are stored as structured **JSON** and **CSV** files for further analysis in Python or tools like Power BI, Tableau, or Excel.

### 🚀 Dependencies

```bash
uv sync
source .venv/bin/activate
```
---

## ⚙️ 1. Riot Data Collector

### 🔍 Features

- Fetch player **PUUID** using Riot ID (`gameName` + `tagLine`)
- Collect:
  - Ranked stats (`league-v4`)
  - Champion masteries (`champion-mastery-v4`)
  - Match history (`match-v5`)
- Automatically handle:
  - **Rate limits** (using deque-based timestamp logging)
  - **Pagination** for fetching all available matches
  - **Partial games filtering** (skips remakes or very short matches)
- Saves:
  - JSON files for champion mastery and ranked stats
  - CSV for structured match performance data

---

### 🧩 Environment Variables

Create a `.env` file in your project root:

```
RIOT_API_KEY=your_api_key_here

REGION_ROUTING=asia
MATCH_REGION_ROUTING=asia
PLATFORM_ROUTING=sg2

CM_FOLDER=./data/champion_mastery
RANKED_STATS_FOLDER=./data/ranked_stats

GAME_NAME_1=Player1
TAG_LINE_1=SG1
GAME_NAME_2=Player2
TAG_LINE_2=SG2
GAME_NAME_3=Player3
TAG_LINE_3=SG3
GAME_NAME_4=Player4
TAG_LINE_4=SG4
GAME_NAME_5=Player5
TAG_LINE_5=SG5

```

---

### 🧠 Key Functions

| Function | Purpose |
|-----------|----------|
| `get_puuid(game_name, tag_line)` | Retrieves player’s unique Riot ID (PUUID). |
| `get_ranked_stats(puuid)` | Gets ranked stats (tier, LP, win/loss) for a player. |
| `get_match_ids(puuid)` | Retrieves all match IDs within the last 8 months (handles pagination). |
| `get_match(match_id)` | Fetches detailed match data with retry handling for rate limits. |
| `get_champion_masteries(puuid)` | Gets champion mastery levels for all champions. |
| `save_match_data()` | Filters key stats and saves match summaries to CSV. |
| `wait_for_rate_limit()` | Manages Riot API rate limits automatically. |

---

Each line in `matches.csv` represents a **player’s perspective** from a single match, containing:

- Game context (duration, mode, version)
- Player info (champion, role, team)
- Combat, damage, economy, and vision stats
- Objective and control performance

---

## 🌐 2. U.GG Scraper

### 🔍 Features

- Uses **Selenium WebDriver (headless Chrome)** to scrape [U.GG](https://u.gg/lol/champions)
- Captures champion stats across all ranks:
  - Win Rate  
  - Pick Rate  
  - Ban Rate  
  - Tier Ranking  
  - Total Matches Played
- Cleans and formats percentages and numbers into numeric values
- Saves all champion data to `champions.csv`

---

### ⚙️ How It Works

- The scraper visits the U.GG champions page.
- Collects all champion URLs.
- Iterates through each champion and rank (Iron → Challenger).
- Extracts performance statistics.
- Cleans and saves data to a single CSV file.
