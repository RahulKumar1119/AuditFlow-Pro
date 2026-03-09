import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_leaderboard(feed_url, target_slug):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = "/usr/bin/chromium-browser"
    
    print("🚀 Starting Deep-Scan Browser...")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(feed_url)
    time.sleep(6)
    
    last_count = 0
    clicks = 0
    consecutive_no_growth = 0

    print("Expanding feed (Deep-Scan mode)...")
    while True:
        try:
            load_more = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Load more')]"))
            )
            driver.execute_script("arguments[0].click();", load_more)
            clicks += 1
            time.sleep(4)
            
            current_cards = len(driver.find_elements(By.XPATH, "//a[contains(@href, '/content/')]"))
            if current_cards > last_count:
                print(f"Click {clicks}: Elements loaded so far: {current_cards}")
                last_count = current_cards
                consecutive_no_growth = 0
            else:
                consecutive_no_growth += 1
                
            if consecutive_no_growth >= 3:
                print("Count stalled. Reached end of content.")
                break
        except Exception:
            print(f"List fully expanded after {clicks} clicks.")
            break

    print("Extracting final leaderboard data...")
    js_extractor = """
    let results = [];
    let processed = new Set();
    let allLinks = document.querySelectorAll("a[href*='/content/']");
    
    allLinks.forEach(link => {
        let url = link.href;
        let titleText = link.innerText.trim();
        
        // Exclude empty links or links that are just numbers/images
        if (titleText.length < 5 || /^\\d+$/.test(titleText)) return;
        if (processed.has(url)) return;
        processed.add(url);
        
        // 1. DYNAMIC BOUNDARY DETECTION:
        // Go up the DOM tree until the parent container holds more than one unique article.
        // When that happens, we know 'card' is the exact boundary of a single article.
        let card = link;
        while (card.parentElement && card.parentElement.tagName !== 'BODY') {
            let parent = card.parentElement;
            let childLinks = parent.querySelectorAll("a[href*='/content/']");
            let unique = new Set();
            childLinks.forEach(a => {
                let text = a.innerText.trim();
                if (text.length > 5 && !/^\\d+$/.test(text)) {
                    unique.add(a.href);
                }
            });
            
            if (unique.size > 1) {
                break; // 'card' is now locked to exactly one article
            }
            card = parent;
        }
        
        // 2. EXTRACT LIKES:
        let likes = 0;
        // Split the card's visual text into lines
        let lines = card.innerText.split('\\n').map(l => l.trim()).filter(l => l !== "");
        
        // The first standalone number in the card is the Likes
        for (let line of lines) {
            if (/^\\d+$/.test(line)) {
                likes = parseInt(line);
                break; 
            }
        }
        
        results.push({Title: titleText, URL: url, Likes: likes});
    });
    return results;
    """
    
    data = driver.execute_script(js_extractor)
    driver.quit()

    if not data:
        print("❌ Error: No articles found.")
        return

    # Clean the data and ensure Likes are treated as integers
    df = pd.DataFrame(data).drop_duplicates(subset='URL')
    df['Likes'] = pd.to_numeric(df['Likes'], errors='coerce').fillna(0).astype(int)
    df = df.sort_values(by="Likes", ascending=False).reset_index(drop=True)
    df['Rank'] = df.index + 1
    total = len(df)

    print("\n" + "="*50)
    print(f"🏆 AIDEAS 2025 CONSOLIDATED LEADERBOARD 🏆")
    print("="*50)
    print(f"Total Articles Published: {total}")
    
    my_proj = df[df['URL'].str.contains(target_slug)]
    if not my_proj.empty:
        rank = my_proj.iloc[0]['Rank']
        likes = my_proj.iloc[0]['Likes']
        print(f"Project: AuditFlow-Pro")
        print(f"Rank: #{rank} | Likes: {likes}")
        print(f"Percentile: Top {((total - rank)/total)*100:.2f}%")
    else:
        print(f"❌ AuditFlow-Pro not found in the {total} articles scanned.")
    
    print("\n--- Verified Top 30 ---")
    print(df[['Rank', 'Likes', 'Title']].head(30).to_string(index=False))

if __name__ == "__main__":
    URL = "https://builder.aws.com/learn/topics/aideas-2025?tab=article"
    TARGET = "39f5Ig6DMc3Nd24BfkQHhVXfsg2/aideas-auditflow-pro"
    get_leaderboard(URL, TARGET)
