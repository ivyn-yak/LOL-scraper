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

def clean_value(text):
    """Clean and convert text to appropriate numeric type"""
    cleaned = text.replace('%', '').replace(',', '').strip()
    try:
        num = float(cleaned)
        return int(num) if num.is_integer() else num
    except ValueError:
        return cleaned

def extract_champion_name_from_img(img_element):
    """Extract champion name from image element"""
    try:
        # Try alt attribute first
        alt_text = img_element.get_attribute('alt')
        if alt_text and alt_text.strip():
            # Clean the name
            name = alt_text.lower()
            name = name.replace("'", "").replace(" ", "").replace(".", "")
            return name
        
        # Try src attribute as fallback
        src = img_element.get_attribute('src')
        if src:
            match = re.search(r'/champ[^/]+/([^/\.]+)\.webp', src)
            if match:
                return match.group(1).lower()
    except Exception as e:
        print(f"    ⚠ Error extracting champion name: {e}")
    return None

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

def scrape_visible_matchups(driver, champion, counter_type):
    """Scrape the currently visible matchups after clicking a filter button"""
    matchups = []
    
    try:
        # Wait for content to fully load after button click
        time.sleep(2)
        
        # Find all role sections
        # Each section has class: "flex h-[146px] mb-2 border"
        sections = driver.find_elements(By.CSS_SELECTOR, "div.flex.h-\\[146px\\].mb-2.border")
        print(f"    🔍 Found {len(sections)} sections")
        
        for idx, section in enumerate(sections):
            try:
                # Get the role for this section
                role = get_role_from_lane_icon(section)
                if not role:
                    print(f"    ⚠ Section {idx}: No role found")
                    continue
                
                print(f"    📍 Processing role: {role}")
                
                # Find the scrollable container
                try:
                    scroll_container = section.find_element(By.CSS_SELECTOR, "div.cursor-grab.overflow-y-hidden.overflow-x-scroll")
                except:
                    print(f"       ⚠ No scroll container found for {role}")
                    continue
                
                # Inside scroll container, find the flex container with all matchups
                try:
                    matchup_flex = scroll_container.find_element(By.CSS_SELECTOR, "div.flex.gap-\\[6px\\]")
                except:
                    print(f"       ⚠ No matchup flex container found for {role}")
                    continue
                
                # Get all direct child divs - each is a matchup card
                matchup_cards = matchup_flex.find_elements(By.XPATH, "./div")
                print(f"       Found {len(matchup_cards)} matchup cards")
                
                processed = 0
                for card in matchup_cards:
                    try:
                        # Extract champion image (nested: div > a > span > img)
                        img = card.find_element(By.CSS_SELECTOR, "img[src*='champ']")
                        opponent = extract_champion_name_from_img(img)
                        
                        if not opponent or opponent == champion.lower():
                            continue
                        
                        # Get all divs with class "my-1" - these contain the stats
                        stat_divs = card.find_elements(By.CSS_SELECTOR, "div.my-1")
                        
                        if len(stat_divs) < 4:
                            if processed == 0:
                                print(f"       ⚠ {opponent}: Only found {len(stat_divs)} stat divs")
                            continue
                        
                        # Extract Win Rate (first div with my-1, contains a span)
                        try:
                            win_rate_span = stat_divs[0].find_element(By.TAG_NAME, "span")
                            win_rate = clean_value(win_rate_span.text)
                        except:
                            win_rate = clean_value(stat_divs[0].text)
                        
                        # Extract Delta 1 (second div with my-1)
                        delta1 = clean_value(stat_divs[1].text)
                        
                        # Extract Delta 2 (third div with my-1)
                        delta2 = clean_value(stat_divs[2].text)
                        
                        # Extract Pick Rate (fourth div with my-1)
                        pick_rate = clean_value(stat_divs[3].text)
                        
                        # Extract Games (div with class text-[9px])
                        games = 0
                        try:
                            games_div = card.find_element(By.CSS_SELECTOR, "div.text-\\[9px\\]")
                            games = clean_value(games_div.text)
                        except:
                            pass
                        
                        matchups.append({
                            'champion': champion,
                            'role': role,
                            'counter_type': counter_type,
                            'opponent': opponent,
                            'win_rate': win_rate,
                            'delta_1': delta1,
                            'delta_2': delta2,
                            'pick_rate': pick_rate,
                            'games': games
                        })
                        
                        processed += 1
                        if processed <= 3:  # Print first 3 for debugging
                            print(f"       ✓ {opponent} - WR: {win_rate}% (Δ1: {delta1}, Δ2: {delta2})")
                    
                    except Exception as e:
                        if processed == 0:
                            print(f"       ⚠ Error processing card: {str(e)[:80]}")
                        continue
                
                print(f"       Total processed: {processed}")
            
            except Exception as e:
                print(f"    ⚠ Error in section {idx}: {str(e)[:80]}")
                continue
    
    except Exception as e:
        print(f"    ❌ Error scraping: {str(e)[:100]}")
    
    return matchups

def scrape_champion_counters(champion):
    """Scrape strong_against and weak_against for a champion"""
    url = f"https://lolalytics.com/lol/{champion}/build/?tier=diamond_plus&patch=15.19"
    
    print(f"\n{'='*60}")
    print(f"🔍 Scraping {champion.upper()}...")
    driver.get(url)
    
    all_matchups = []
    
    try:
        # Wait for page to load - wait for filter buttons to appear
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-type='strong_counter']"))
        )
        time.sleep(3)  # Let page fully render
        
        # ===== CLICK STRONG COUNTER BUTTON =====
        print("  📊 Clicking 'Strong Against' button...")
        try:
            strong_button = driver.find_element(By.CSS_SELECTOR, "div[data-type='strong_counter']")
            
            # Check if already active (has bg-[#3a7e93])
            button_classes = strong_button.get_attribute('class')
            
            # Click the button
            driver.execute_script("arguments[0].scrollIntoView(true);", strong_button)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", strong_button)
            
            # Wait for button to become active
            WebDriverWait(driver, 5).until(
                lambda d: 'bg-[#3a7e93]' in strong_button.get_attribute('class')
            )
            print("    ✓ Button activated")
            
            # DEBUG: Save HTML for first champion to inspect
            if champion == "aatrox":
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print("    🔍 Saved debug_page.html for inspection")
            
            # Scrape the matchups
            strong_matchups = scrape_visible_matchups(driver, champion, 'strong_against')
            print(f"    ✅ Collected {len(strong_matchups)} 'strong against' matchups")
            all_matchups.extend(strong_matchups)
        
        except Exception as e:
            print(f"    ⚠ Could not get strong_counter: {str(e)[:100]}")
        
        # ===== CLICK WEAK COUNTER BUTTON =====
        print("  📊 Clicking 'Weak Against' button...")
        try:
            weak_button = driver.find_element(By.CSS_SELECTOR, "div[data-type='weak_counter']")
            
            # Click the button
            driver.execute_script("arguments[0].scrollIntoView(true);", weak_button)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", weak_button)
            
            # Wait for button to become active
            WebDriverWait(driver, 5).until(
                lambda d: 'bg-[#3a7e93]' in weak_button.get_attribute('class')
            )
            print("    ✓ Button activated")
            
            # Scrape the matchups
            weak_matchups = scrape_visible_matchups(driver, champion, 'weak_against')
            print(f"    ✅ Collected {len(weak_matchups)} 'weak against' matchups")
            all_matchups.extend(weak_matchups)
        
        except Exception as e:
            print(f"    ⚠ Could not get weak_counter: {str(e)[:100]}")
    
    except TimeoutException:
        print(f"  ⏱ Timeout loading {champion}")
        return []
    
    return all_matchups

def main():
    all_data = []
    
    # Scrape each champion
    for i, champion in enumerate(champions, 1):
        print(f"\n{'#'*60}")
        print(f"Progress: {i}/{len(champions)}")
        
        try:
            matchups = scrape_champion_counters(champion)
            all_data.extend(matchups)
            print(f"  📊 Total matchups so far: {len(all_data)}")
        
        except Exception as e:
            print(f"  ❌ Failed to scrape {champion}: {e}")
            continue
        
        # Small delay between champions
        time.sleep(1)
    
    # Save final results
    if all_data:
        df = pd.DataFrame(all_data)
        df = df.sort_values(['champion', 'role', 'counter_type', 'win_rate'])
        
        # Save complete data
        df.to_csv("champions_counters.csv", index=False)
        print(f"\n✅ Saved {len(df)} total matchups to champions_counters.csv")
        
        # Create separate files for strong and weak
        strong_df = df[df['counter_type'] == 'strong_against'].copy()
        weak_df = df[df['counter_type'] == 'weak_against'].copy()
        
        strong_df.to_csv("champions_strong_against.csv", index=False)
        weak_df.to_csv("champions_weak_against.csv", index=False)
        
        print(f"✅ Saved {len(strong_df)} 'strong against' matchups")
        print(f"✅ Saved {len(weak_df)} 'weak against' matchups")
        
        # Print sample
        print("\n" + "="*60)
        print("SAMPLE DATA:")
        print("="*60)
        print(df.head(10).to_string(index=False))
    
    else:
        print("\n❌ No data collected!")

if __name__ == "__main__":
    try:
        main()
    finally:
        driver.quit()
        print("\n🏁 Scraping completed!")