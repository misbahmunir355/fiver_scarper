from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import os

def setup_driver():
    options = Options()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-extensions')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90, 110)}.0.0.0 Safari/537.36")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument('--log-level=3')
    service = Service(ChromeDriverManager().install()) 
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def scroll_to_end(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts = 0
    while scroll_attempts < 3:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(1.5, 3.5))
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            scroll_attempts += 1
            time.sleep(1)
        else:
            scroll_attempts = 0
        last_height = new_height

def scrape_page(driver):
    """Extract data from a single page with ranking"""
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    page_data = []
    gig_links = []

    gig_cards = soup.find_all('div', {'class': 'gig-card-layout'}) or \
                soup.find_all('li', {'class': 'gig-card'}) or \
                soup.find_all('div', {'class': 'gig-wrapper'})

    rank = 1  # Initialize rank counter

    for card in gig_cards:
        try:
            name = card.find('span', class_='vp9lqtk').get_text(strip=True) if card.find('span', class_='vp9lqtk') else "N/A"
            level = card.find('p', class_='_1qwbi7a2').get_text(strip=True) if card.find('p', class_='_1qwbi7a2') else "N/A"
            rating = card.find('strong', class_='rating-score').get_text(strip=True) if card.find('strong', class_='rating-score') else "N/A"
            
            # Extract reviews count using the specific class 'ratings-count roYp76D'
            reviews_element = card.find('span', class_='ratings-count roYp76D')
            reviews = reviews_element.get_text(strip=True).replace('(', '').replace(')', '') if reviews_element else "0"
            
            price = card.find('span', class_='text-bold co-grey-1200')
            price = price.find('span').get_text(strip=True) if price else "N/A"

            # Extract gig link
            link_tag = card.find('a', href=True)
            gig_link = "https://www.fiverr.com" + link_tag['href'] if link_tag else None

            page_data.append({
                'RANK': rank,
                'NAME': name,
                'LEVEL': level,
                'RATING': rating,
                'REVIEWS_COUNT': reviews,
                'PRICE_STARTING_FROM': price,
                'GIG_LINKS': gig_link
            })

            if gig_link:
                gig_links.append(gig_link)

            rank += 1

        except Exception as e:
            print(f"Error extracting gig data: {e}")
            continue

    return page_data, gig_links

def scrape_fiverr(keyword):
    """Main scraping function for first page only"""
    driver = setup_driver()
    base_url = "https://www.fiverr.com"
    search_url = f"{base_url}/search/gigs?query={keyword.replace(' ', '%20')}"
    all_data = []
    gig_links = []

    try:
        driver.get(search_url)
        print(f"Starting scrape for: {keyword}")

        # Wait for results to load
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.vp9lqtk, .gig-card-layout"))
            )
        except TimeoutException:
            print(f"Timeout waiting for the page. No results or page too slow.")
            return [], []

        # Scroll to load all gigs
        scroll_to_end(driver)

        # Scrape only the current page
        all_data, gig_links = scrape_page(driver)

        print(f"Found {len(all_data)} gigs on first page")
    finally:
        driver.quit()
    return all_data

def save_results(data, keyword):
    """Save data to Excel"""
    if not data:
        print("No data to save!")
        return

    try:
        df = pd.DataFrame(data)
        os.makedirs('scraped_data', exist_ok=True)
        filename = f"scraped_data/fiverr_{keyword.replace(' ', '_')}_{int(time.time())}.xlsx"
        df.to_excel(filename, index=False)
        print(f"\nSuccess! Saved {len(data)} results to {filename}")
        print("\nSample data:")
        print(df.head())
    except Exception as e:
        print(f"Error saving results: {e}")

if __name__ == "__main__":
    keyword = input("Enter search keyword: ").strip()
    if not keyword:
        print("No keyword provided! Exiting.")
        exit()

    print(f"\nStarting Fiverr scrape for '{keyword}'...")
    start_time = time.time()

    results = scrape_fiverr(keyword)
    save_results(results, keyword)

    print(f"\nScraping completed in {time.time() - start_time:.2f} seconds")