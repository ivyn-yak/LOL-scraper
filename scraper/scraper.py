from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options

import pandas as pd

options = Options()
options.add_argument("--headless") 
driver = webdriver.Chrome(options=options)

driver.get("https://u.gg/lol/champions")

title = driver.title
driver.implicitly_wait(10)  

RANKS = ["overall", "iron", "bronze", "silver", "gold", "platinum", "emerald", "diamond", "master", "grandmaster", "challenger"]

def format(arr):
    for i in range(len(arr)):
        cleaned_item = arr[i].replace('%', '').replace(',', '').strip()
        try:
            num = float(cleaned_item)
            # if no decimal part, cast to int
            if num.is_integer():
                num = int(num)
            arr[i]=num
        except ValueError:
            arr[i]=cleaned_item
    
    print("format done", arr)
    return arr

def main():
    all_data = []

    # Collect hrefs first
    links = driver.find_elements(By.CSS_SELECTOR, "div.grid.bg-purple-400 a")
    hrefs = [link.get_attribute("href") for link in links]

    # Loop through each href
    for href in hrefs:
        champion = href.split("/")[-2]
        for rank in RANKS:
            url = href + f"?rank={rank}"
            driver.get(url)           
            print("Visiting:", url)

            # Wait for page to load (with retry logic)
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.champion-recommended-build"))
                )
            except TimeoutException:
                print(f"⚠ Timeout after 10s for {url}. Retrying with longer wait...")
                try:
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.champion-recommended-build"))
                    )
                except TimeoutException:
                    print(f"❌ Skipping {url} — element not found even after retry.")
                    all_data.append([champion, rank] + ["-"] * 6)   
                    continue  # skip to next URL
            
            stats_container = driver.find_element(
                By.CSS_SELECTOR,
                "div.grid.grid-flow-col.bg-purple-500"
            )

            stats_col = stats_container.find_elements(By.CSS_SELECTOR, "div.font-extrabold")
            stats_col_text = [el.text for el in stats_col]
            stats_cleaned = format(stats_col_text)

            stats_cleaned = [champion, rank] + stats_cleaned
            all_data.append(stats_cleaned)         

        driver.back()              # Go back to the grid page

    df = pd.DataFrame(all_data, columns=['Champion', 'Rank', 'Tier', 'Win Rate', 'Rank', 'Pick Rate', 'Ban Rate', 'Matches'])
    print(df.head)

    df.to_csv("champions.csv", index=False)

main()

driver.quit()