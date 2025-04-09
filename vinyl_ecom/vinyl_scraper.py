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

        genre_toggle = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@href='#collapseFilterGender']"))
        )
        genre_toggle.click()
        print("Genre toggle clicked")

        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "collapseFilterGender"))
        )
        print("Filter section expanded")

        filter_label = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//label[@for='filterRock']"))
        )
        filter_label.click()
        print("Rock filter label clicked")

        time.sleep(5)  # Wait for filter to apply
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".product-grid .product-item"))
        )
        print("Rock filter applied successfully")

        visible_items = [item for item in driver.find_elements(By.CSS_SELECTOR, ".product-grid .product-item") if item.is_displayed()]
        print(f"Found {len(visible_items)} visible vinyl items in product grid")
    except Exception as e:
        print(f"Error applying filters: {e}")

    return driver

def scrape_vinyl_data():
    base_url = "https://vinyl.com/pages/shop"
    driver = setup_driver()
    driver = apply_filters(driver, base_url)

    # Get visible items within product-grid only
    vinyl_items = [item for item in driver.find_elements(By.CSS_SELECTOR, ".product-grid .product-item") if item.is_displayed()]
    soup = BeautifulSoup(driver.page_source, "html.parser")
    with open("filtered_page.html", "w") as f:
        f.write(soup.prettify())
    print("Filtered page saved to filtered_page.html")

    vinyl_data = []
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    session.headers.update(headers)

    for i, item in enumerate(vinyl_items[:2]):  # Limit to 2
        try:
            vinyl_info = {}
            item_html = item.get_attribute("outerHTML")
            item_soup = BeautifulSoup(item_html, "html.parser")

            # Debug: Print raw item HTML
            print(f"Item {i+1} HTML: {item_html[:200]}...")

            title_elem = item_soup.select_one(".product-name h2")
            vinyl_info["title"] = title_elem.text.strip() if title_elem else "N/A"
            print(f"Title: {vinyl_info['title']}")

            price_elem = item_soup.select_one(".new-price")
            vinyl_info["price"] = price_elem.text.strip() if price_elem else "N/A"
            print(f"Price: {vinyl_info['price']}")

            artist_elem = item_soup.select_one(".product-artist h3")
            vinyl_info["artist"] = artist_elem.text.strip() if artist_elem else "N/A"
            print(f"Artist: {vinyl_info['artist']}")

            detail_link_elem = item_soup.select_one(".product-name")
            detail_link = detail_link_elem["href"] if detail_link_elem else None
            if detail_link:
                full_detail_url = f"https://vinyl.com{detail_link}"
                detail_response = session.get(full_detail_url)
                detail_soup = BeautifulSoup(detail_response.content, "html.parser")

                release_date = detail_soup.select_one(".release-date")
                vinyl_info["release_date"] = release_date.text.strip() if release_date else "N/A"
                print(f"Release Date: {vinyl_info['release_date']}")
            else:
                vinyl_info["release_date"] = "N/A"

            vinyl_data.append(vinyl_info)
            time.sleep(1)
        except AttributeError as e:
            print(f"Error scraping item: {e}")
            continue

    driver.quit()
    write_to_csv(vinyl_data)
    return vinyl_data

def write_to_csv(data):
    if not data:
        print("No data to write")
        return
    fieldnames = ["title", "price", "artist", "release_date"]
    with open("vinyl_data.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print("Data written to vinyl_data.csv")

def main():
    print("Starting scraper...")
    scraped_data = scrape_vinyl_data()
    print(f"Scraped {len(scraped_data)} vinyl records")

if __name__ == "__main__":
    main()