"""
Scraper to get "strong against" and "weak against" champions by clicking the filter buttons
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
import re

# Setup Chrome options
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
driver = webdriver.Chrome(options=options)

# Complete champions list
champions = [
    "aatrox", "ahri", "akali", "akshan", "alistar", "ambessa", "amumu", "anivia", 
    "annie", "aphelios", "ashe", "aurelionsol", "aurora", "azir", "bard", "belveth",
    "blitzcrank", "brand", "braum", "briar", "caitlyn", "camille", "cassiopeia", 
    "chogath", "corki", "darius", "diana", "drmundo", "draven", "ekko", "elise",
    "evelynn", "ezreal", "fiddlesticks", "fiora", "fizz", "galio", "gangplank",
    "garen", "gnar", "gragas", "graves", "gwen", "hecarim", "heimerdinger", "hwei",
    "illaoi", "irelia", "ivern", "janna", "jarvaniv", "jax", "jayce", "jhin", "jinx",
    "ksante", "kaisa", "kalista", "karma", "karthus", "kassadin", "katarina", "kayle",
    "kayn", "kennen", "khazix", "kindred", "kled", "kogmaw", "leblanc", "leesin",
    "leona", "lillia", "lissandra", "lucian", "lulu", "lux", "malphite", "malzahar",
    "maokai", "masteryi", "mel", "milio", "missfortune", "mordekaiser", "morgana",
    "naafiri", "nami", "nasus", "nautilus", "neeko", "nidalee", "nilah", "nocturne",
    "nunu", "olaf", "orianna", "ornn", "pantheon", "poppy", "pyke", "qiyana", "quinn",
    "rakan", "rammus", "reksai", "rell", "renata", "renekton", "rengar", "riven",
    "rumble", "ryze", "samira", "sejuani", "senna", "seraphine", "sett", "shaco",
    "shen", "shyvana", "singed", "sion", "sivir", "skarner", "smolder", "sona",
    "soraka", "swain", "sylas", "syndra", "tahmkench", "taliyah", "talon", "taric",
    "teemo", "thresh", "tristana", "trundle", "tryndamere", "twistedfate", "twitch",
    "udyr", "urgot", "varus", "vayne", "veigar", "velkoz", "vex", "vi", "viego",
    "viktor", "vladimir", "volibear", "warwick", "wukong", "xayah", "xerath",
    "xinzhao", "yasuo", "yone", "yorick", "yunara", "yuumi", "zac", "zed", "zeri",
    "ziggs", "zilean", "zoe", "zyra"
]

roles = ["top", "jungle", "middle", "adc", "support"]

# Store all results
all_data = []

# Loop through each champion and role
for champion in champions:
    for role in roles:
        url = f"https://www.leagueofgraphs.com/champions/stats/{champion}/sg/{role}/diamond/sr-ranked"
        print(f"Scraping {champion} - {role}...")

        try:
            driver.get(url)
            time.sleep(2)  # Wait for page to load

            # Get page source
            page_source = driver.page_source

            # Find the script tag with graphDD13 data using regex
            pattern = r'\$\.plot\(\$\("#graphDD13"\),\s*\[\{[^}]*data:\s*(\[\[.*?\]\])'
            match = re.search(pattern, page_source, re.DOTALL)

            if match:
                data_str = match.group(1)

                # Check if data is [[0,100]] which means no real data
                if data_str.strip() == "[[0,100]]":
                    print(f"  No data found for {champion} - {role}")
                    all_data.append({
                        'champion': champion,
                        'role': role,
                        'data': "No data found"
                    })
                else:
                    print(f"  Found data: {data_str}")
                    # Store the result
                    all_data.append({
                        'champion': champion,
                        'role': role,
                        'data': data_str
                    })
            else:
                print(f"  No data found for {champion} - {role}")
                all_data.append({
                    'champion': champion,
                    'role': role,
                    'data': "No data found"
                })

        except Exception as e:
            print(f"  Error scraping {champion} - {role}: {str(e)}")
            continue

# Close driver
driver.quit()

# Convert to DataFrame and save
df = pd.DataFrame(all_data)
df.to_csv('winrate_rankgames_data.csv', index=False)
print(f"\nScraping complete! Saved {len(all_data)} records to winrate_rankgames_data.csv")