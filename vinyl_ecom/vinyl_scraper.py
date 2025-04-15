import requests
from bs4 import BeautifulSoup
import csv
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
from selenium.common.exceptions import TimeoutException, WebDriverException

## Feature scope ##
# complete adding all data needed in catalog page [DONE]
# toggle in stock filter to also show out of stock [DONE]
# Navigate to the product page for each of the vinyls [ON-GOING]
## UPC
## Color
## Format
## Weight
## Release date
## First released

print("=========================================================================================")

# Update to which genre to scrape data from
scrapingGenre = "Rock"

def setup_driver():
    options = webdriver.ChromeOptions()
    # Keep visible for debugging
    # options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def apply_filters(driver, url):
    driver.get(url)

    try:
        with open("initial_page.html", "w") as f:
            f.write(driver.page_source)
        print("Initial page saved to initial_page.html")

        genre_toggle = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@href='#collapseFilterGender']"))
        )
        genre_toggle.click()
        print("Genre toggle clicked")

        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.ID, "collapseFilterGender"))
        )
        print("Filter section expanded")

        filter_label = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, f"//label[@for='filter{scrapingGenre.title()}']"))
        )
        filter_label.click()
        print(f"{scrapingGenre} filter label clicked")

        time.sleep(5)  # Wait for filter to apply
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".product-grid .product-item"))
        )
        print(f"{scrapingGenre} filter applied successfully")

        stock_toggle = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@class='icon-filter-switch']"))
        )
        stock_toggle.click()
        print("Stock filter applied successfully")

        # Count initial items
        initial_items = len([item for item in driver.find_elements(By.CSS_SELECTOR, ".product-grid .product-item") if item.is_displayed()])
        print(f"Initial visible items: {initial_items}")

        # Click Show More button with retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                show_more_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'btn-primary') and contains(@class, 'btn-sm') and text()='Show More']"))
                )
                # Enhanced scroll with offset
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'}); window.scrollBy(0, -100);", show_more_button)
                # Wait for potential overlays to disappear
                time.sleep(1)
                # Check visibility
                if not show_more_button.is_displayed():
                    raise WebDriverException("Show More button is not visible")
                # Log nearby elements for debugging
                nearby_elements = driver.execute_script(
                    "var rect = arguments[0].getBoundingClientRect(); "
                    "var elements = document.elementsFromPoint(rect.left + rect.width/2, rect.top + rect.height/2); "
                    "return Array.from(elements).slice(0, 3).map(el => el.outerHTML);",
                    show_more_button
                )
                print(f"Attempt {attempt + 1}: Nearby elements at button: {nearby_elements}")
                # Click with JavaScript
                driver.execute_script("arguments[0].click();", show_more_button)
                print(f"Attempt {attempt + 1}: SHOW MORE button clicked successfully")
                break  # Success, exit retry loop
            except Exception as e:
                print(f"Attempt {attempt + 1} failed to click Show More button: {e}")
                if attempt == max_retries - 1:
                    raise  # Re-raise last error after retries
                time.sleep(2)  # Pause before retry

        # Wait for new items to load
        WebDriverWait(driver, 10).until(
            lambda d: len([item for item in d.find_elements(By.CSS_SELECTOR, ".product-grid .product-item") if item.is_displayed()]) > initial_items
        )
        print("New items loaded after Show More click")

        visible_items = [item for item in driver.find_elements(By.CSS_SELECTOR, ".product-grid .product-item") if item.is_displayed()]
        print(f"Found {len(visible_items)} visible vinyl items in product grid")
    except Exception as e:
        print(f"Error applying filters: {e}")
        # Save debug HTML
        timestamp = time.time()
        with open(f"debug_filters_failure_{timestamp}.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"Saved page source to debug_filters_failure_{timestamp}.html")

    return driver

def click_songwriters_div(driver):
    """
    Expands the Credits accordion and clicks the Songwriters div in the product-content-creators section.

    Args:
        driver: Selenium WebDriver instance (e.g., Chrome driver).

    Returns:
        bool: True if the click was successful, False if the Songwriters div doesn't exist or an error occurred.
    """
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Wait for the product-content-collapse section
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".product-content-collapse"))
            )
            # Find the Credits accordion button
            credits_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".accordion-button[data-bs-target='#collapseOne']"))
            )
            # Scroll into view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", credits_button)
            # Check if accordion is collapsed
            if "collapsed" in credits_button.get_attribute("class"):
                print(f"Attempt {attempt + 1}: Expanding Credits accordion")
                driver.execute_script("arguments[0].click();", credits_button)
                # Wait for the accordion content to be visible
                WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.ID, "collapseOne"))
                )
                print(f"Attempt {attempt + 1}: Credits accordion expanded")
            else:
                print(f"Attempt {attempt + 1}: Credits accordion already expanded")

            # Wait for the product-content-creators section
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".product-content-creators"))
            )
            # More specific XPath for Songwriters div
            xpath = "//div[contains(@class, 'splide__slide') and .//span[@class='badge text-bg-secondary'] and normalize-space(text())='Songwriters']"
            # Wait for the Songwriters div to be present and visible
            songwriters_div = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, xpath))
            )
            # Scroll into view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", songwriters_div)
            # Wait for clickability
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            # Click using JavaScript
            driver.execute_script("arguments[0].click();", songwriters_div)
            print(f"Attempt {attempt + 1}: Clicked on the 'Songwriters' div successfully")
            return True
        except (TimeoutException, WebDriverException) as e:
            print(f"Attempt {attempt + 1} failed to click 'Songwriters' div: {e}")
            if attempt == max_attempts - 1:
                # Save page source for debugging
                timestamp = time.time()
                # with open(f"debug_songwriters_failure_{timestamp}.html", "w", encoding="utf-8") as f:
                    # f.write(driver.page_source)
                print(f"Saved page source to debug_songwriters_failure_{timestamp}.html")
                return False
            time.sleep(1)  # Brief pause before retry
    return False

def scrape_vinyl_data():
    base_url = "https://vinyl.com/pages/shop"
    driver = setup_driver()
    driver = apply_filters(driver, base_url)

    # Get visible items within product-grid and collect detail links
    vinyl_items = [item for item in driver.find_elements(By.CSS_SELECTOR, ".product-grid .product-item") if item.is_displayed()]
    soup = BeautifulSoup(driver.page_source, "html.parser")
    with open("filtered_page.html", "w") as f:
        f.write(soup.prettify())
    print("Filtered page saved to filtered_page.html")

    vinyl_data = []
    item_details = []

    # First pass: Collect basic info and detail links from catalog
    for i, item in enumerate(vinyl_items[:35]):
        try:
            vinyl_info = {}
            item_html = item.get_attribute("outerHTML")
            item_soup = BeautifulSoup(item_html, "html.parser")

            image_elem = item_soup.select_one(".img-fluid")
            vinyl_info["vinyl_img"] = image_elem.get("src") if image_elem else ""

            product_link_elem = item_soup.select_one(".product-name")
            relative_href = product_link_elem.get("href") if product_link_elem else ""
            vinyl_info["product_href"] = urljoin("https://vinyl.com/", relative_href) if relative_href else ""

            title_elem = item_soup.select_one(".product-name h2")
            vinyl_info["vinyl_title"] = title_elem.text.strip() if title_elem else ""
            print(f"Title {i+1}: {vinyl_info['vinyl_title']}")

            price_elem = item_soup.select_one(".new-price")
            vinyl_info["price"] = price_elem.text.strip("$") if price_elem else ""

            old_price_elem = item_soup.select_one(".old-price")
            vinyl_info["old_price"] = old_price_elem.text.strip("$") if old_price_elem else ""

            artist_elem = item_soup.select_one(".product-artist h3")
            vinyl_info["vinyl_artist"] = artist_elem.text.strip().title() if artist_elem else ""

            sale_elem = item_soup.select_one(".sale-label")
            vinyl_info["sale_label"] = sale_elem.text.strip().upper() if sale_elem else ""

            stock_elem = item_soup.select_one(".low-stock-label")
            vinyl_info["low_stock_label"] = stock_elem.text.strip().upper() if stock_elem else ""

            no_stock_elem = item_soup.select_one(".no-stock-label")
            vinyl_info["no_stock_label"] = "SOLD OUT" if no_stock_elem else ""

            vinyl_info["genre"] = scrapingGenre.lower()

            detail_link = product_link_elem["href"] if product_link_elem else None
            item_details.append((vinyl_info, detail_link))
        except Exception as e:
            print(f"Error collecting basic info for item {i+1}: {e}")
            continue

    # Second pass: Fetch detail pages with Selenium
    for i, (vinyl_info, detail_link) in enumerate(item_details):
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # Restart driver every 10 items
                if i > 0 and i % 10 == 0:
                    print(f"Restarting driver at item {i+1}")
                    driver.quit()
                    driver = setup_driver()
                    driver.set_page_load_timeout(180)  # Increase timeout

                if detail_link:
                    full_detail_url = f"https://vinyl.com{detail_link}"
                    print(f"Attempt {attempt + 1}: Loading {full_detail_url}")
                    driver.get(full_detail_url)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".product-info p"))
                    )
                    detail_soup = BeautifulSoup(driver.page_source, "html.parser")

                    # Vinyl description
                    description_elements = detail_soup.select(".inner Sce-scrape-main-artist-and-companies-after-expanding-credits-accordion-inner-show-read-more p")
                    description = [p.text.strip() for p in description_elements] if description_elements else ["N/A"]
                    vinyl_info["vinyl_description"] = " ".join(description) if description != ["N/A"] else "N/A"

                    # Product info
                    product_info_elem = detail_soup.select(".product-info p")
                    product_info = [[p.find('b').text.strip(), p.text.split(':', 1)[1].strip()] for p in product_info_elem if p.text.strip() and p.find('b')] if product_info_elem else [["N/A", "N/A"]]
                    vinyl_info["vinyl_info"] = product_info

                    # Playlist name
                    playlist_name_elem = detail_soup.select_one(".playlist-name")
                    vinyl_info["playlist_name"] = playlist_name_elem.text.strip() if playlist_name_elem else ""

                    # Tracklist
                    tracklist_elem = detail_soup.select(".tracklist-table tr")
                    tracklist = [[td.text.strip() for td in tr.select("td")[:3]] for tr in tracklist_elem if tr.text.strip()] if tracklist_elem else [["N/A", "N/A", "N/A"]]
                    vinyl_info["tracklist"] = tracklist

                    # Main artists
                    creator_content_elem = detail_soup.select(".creators-content .creators-content-item")
                    creator_content = [
                        [
                            item.select_one(".wrap-image img")["src"] if item.select_one(".wrap-image img") else "N/A",
                            item.select_one(".info .title").text.strip() if item.select_one(".info .title") else "N/A",
                            item.select_one(".info .desc").text.strip() if item.select_one(".info .desc") else "N/A"
                        ]
                        for item in creator_content_elem
                        if item.select_one(".info") and item.select_one(".info").text.strip()
                    ] if creator_content_elem else [["N/A", "N/A", "N/A"]]
                    vinyl_info["main_artists"] = creator_content
                    print(f"creator content 2:{creator_content}")

                    # Companies
                    company_content_elem = detail_soup.select(".companies .company-item")
                    company_content = [
                        [
                            item.select_one(".wrap-image img")["src"] if item.select_one(".wrap-image img") else "N/A",
                            item.select_one(".info .title").text.strip() if item.select_one(".info .title") else "N/A",
                            item.select_one(".info .desc").text.strip() if item.select_one(".info .desc") else "N/A"
                        ]
                        for item in company_content_elem
                        if item.select_one(".info") and item.select_one(".info").text.strip()
                    ] if company_content_elem else [["N/A", "N/A", "N/A"]]
                    vinyl_info["companies"] = company_content

                    # Click the Songwriters div to switch to Songwriters view
                    if click_songwriters_div(driver):
                        print(f"SONG WRITERS CLICKED")
                        # Wait for the creators-content to update
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".creators-content"))
                        )
                        # Update the soup to reflect the new page state
                        detail_soup = BeautifulSoup(driver.page_source, "html.parser")

                        # Scrape Songwriters data
                        songwriters_content_elem = detail_soup.select(".creators-content .creators-content-item")
                        songwriters_content = [
                            [
                                item.select_one(".wrap-image img")["src"] if item.select_one(".wrap-image img") else "N/A",
                                item.select_one(".info .title").text.strip() if item.select_one(".info .title") else "N/A",
                                item.select_one(".info .desc").text.strip() if item.select_one(".info .desc") else "N/A"
                            ]
                            for item in songwriters_content_elem
                            if item.select_one(".info") and item.select_one(".info").text.strip()
                        ]
                        vinyl_info["songwriters"] = songwriters_content if songwriters_content else [["N/A", "N/A", "N/A"]]
                        print(f"Songwriters added")
                    else:
                        vinyl_info["songwriters"] = [["N/A", "N/A", "N/A"]]
                        print(f"Item {i+1}: No Songwriters data available")

                else:
                    vinyl_info["vinyl_info"] = ["N/A"]
                    vinyl_info["songwriters"] = [["N/A", "N/A", "N/A"]]
                    print(f"Item {i+1}: NO DETAIL PAGE ACCESSED")

                vinyl_data.append(vinyl_info)
                break  # Success, exit retry loop

            except Exception as e:
                print(f"Attempt {attempt + 1} failed for item {i+1}: {e}")
                if attempt == max_retries - 1:
                    print(f"Item {i+1}: Max retries reached, skipping")
                    vinyl_info["vinyl_info"] = ["N/A"]
                    vinyl_info["songwriters"] = [["N/A", "N/A", "N/A"]]
                    vinyl_data.append(vinyl_info)
                time.sleep(2)  # Pause before retry

        time.sleep(1)  # Delay between items

    driver.quit()
    write_to_csv(vinyl_data)
    return vinyl_data

def write_to_csv(data):
    if not data:
        print("No data to write")
        return
    fieldnames = [
        "playlist_name", "vinyl_img", "product_href",
        "vinyl_title", "vinyl_artist", "price", "old_price",
        "sale_label", "low_stock_label", "no_stock_label", "genre",
        "vinyl_description", "vinyl_info", "tracklist",
        "companies", "main_artists", "songwriters"
    ]
    with open(f"{scrapingGenre.lower()}_vinyl_data.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print(f"Data written to {scrapingGenre.lower()}_vinyl_data.csv")

def main():
    print("Starting scraper...")
    scraped_data = scrape_vinyl_data()
    print(f"Scraped {len(scraped_data)} vinyl records")

if __name__ == "__main__":
    main()