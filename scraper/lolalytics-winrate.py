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
# options.add_argument("--headless")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
driver = webdriver.Chrome(options=options)

def clean_value(text):
    """Clean and convert text to appropriate numeric type"""
    if "\n" in text:
        text = text.split("\n")[0]
    cleaned = text.replace('%', '').replace(',', '').strip()
    try:
        num = float(cleaned)
        return int(num) if num.is_integer() else num
    except ValueError:
        return cleaned

def get_role_from_lane_icon(section):
    """Extract role from the lane icon"""
    try:
        lane_img = section.find_element(By.CSS_SELECTOR, "img[alt*='lane']")
        src = lane_img.get_attribute('src')
        
        if 'top.webp' in src:
            return 'top'
        elif 'middle.webp' in src:
            return 'middle'
        elif 'jungle.webp' in src:
            return 'jungle'
        elif 'bottom.webp' in src:
            return 'bottom'
        elif 'support.webp' in src:
            return 'support'
    except:
        pass
    return None

def scrape_champion_data(lane):
    url = f"https://lolalytics.com/lol/tierlist/?lane={lane}&tier=diamond&region=sg&patch=15.19"
    driver.get(url)
    try:
        # Wait for at least one row
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.flex.h-\\[52px\\].justify-between.text-\\[13px\\]")
            )
        )
        time.sleep(2)  # let initial page render

        data = []
        seen_rows = set()
        last_count = 0

        while True:
            # Find all currently loaded rows
            champions = driver.find_elements(
                By.CSS_SELECTOR, "div.flex.h-\\[52px\\].justify-between.text-\\[13px\\]"
            )

            # Break if no new rows are loaded
            if len(champions) == last_count:
                break
            last_count = len(champions)

            for i, c in enumerate(champions):
                if c in seen_rows:
                    continue  # skip already processed
                seen_rows.add(c)

                # Scroll row into view
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", c
                )
                time.sleep(0.3)

                cells = c.find_elements(By.CSS_SELECTOR, "div.my-auto.justify-center")
                if len(cells) < 9:  # skip incomplete rows
                    continue

                role = get_role_from_lane_icon(cells[4])
                texts = [cell.text.strip() for cell in cells if cell.text.strip()]

                name = texts[1]
                win_rate = clean_value(texts[4])
                pick_rate = clean_value(texts[5])
                ban_rate = clean_value(texts[6])
                pbi = clean_value(texts[7])
                num_games = clean_value(texts[8])

                print(f"🔍 Scraping {len(seen_rows)} champions - {name}")
                data.append([name, role, win_rate, pick_rate, ban_rate, pbi, num_games])

            # Scroll to bottom to trigger lazy loading
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)  # wait for new rows to load
        
        return data

    except TimeoutException:
        print(f"⏱ Timeout loading page: {url}")
        return []

def main():
    all_data = []
    lanes = ['top', 'jungle', 'middle', 'bottom', 'support']
    for lane in lanes:
        print(f"\n🚀 Starting scrape for lane: {lane}")
        data = scrape_champion_data(lane)
        if not data:
            print(f"❌ No data scraped for lane: {lane}")
            continue
        else:
            print(f"✅ Scraped {len(data)} champions for lane: {lane}")
            all_data.extend(data)

    # --- Convert to DataFrame ---
    df = pd.DataFrame(all_data, columns=["name", "role", "win_rate", "pick_rate", "ban_rate", "pbi", "num_games"])
    print(df.head())

    # --- Save to CSV ---
    df.to_csv("lolalytics_champions_all.csv", index=False)
    print(f"\n✅ Saved {len(df)} champions to lolalytics_champions.csv")

if __name__ == "__main__":
    try:
        main()
    finally:
        driver.quit()
        print("\n🏁 Scraping completed!")