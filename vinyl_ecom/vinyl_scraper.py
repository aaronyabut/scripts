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

## Feature scope ##
# complete adding all data needed in catalog page [DONE]
# toggle in stock filter to also show out of stock
# navigate to the product page for each of the vinyls

scrapingGenre = "Blues"

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
            EC.element_to_be_clickable((By.XPATH, f"//label[@for='filter{scrapingGenre}']"))
        )
        filter_label.click()
        print(f"{scrapingGenre} filter label clicked")

        time.sleep(5)  # Wait for filter to apply
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".product-grid .product-item"))
        )
        print(f"{scrapingGenre} filter applied successfully")

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

    for i, item in enumerate(vinyl_items[:4]):  # Limit
        try:
            vinyl_info = {}
            item_html = item.get_attribute("outerHTML")
            item_soup = BeautifulSoup(item_html, "html.parser")

            # Debug: Print raw item HTML
            print(f"Item {i+1} HTML: {item_html[:200]}...")

            image_elem = item_soup.select_one(".img-fluid")
            vinyl_info["vinyl_img"] = image_elem.get("src") if image_elem else ""
            print(f"Image link: {vinyl_info['vinyl_img']}")


            product_link_elem = item_soup.select_one(".product-name")
            relative_href = product_link_elem.get("href") if product_link_elem else ""
            vinyl_info["product_href"] = urljoin("https://vinyl.com/", relative_href) if relative_href else ""
            print(f"H REF: {vinyl_info['product_href']}")

            title_elem = item_soup.select_one(".product-name h2")
            vinyl_info["vinyl_title"] = title_elem.text.strip() if title_elem else ""
            print(f"Title: {vinyl_info['vinyl_title']}")

            price_elem = item_soup.select_one(".new-price")
            vinyl_info["price"] = price_elem.text.strip("$") if price_elem else ""
            print(f"Price: {vinyl_info['price']}")

            old_price_elem = item_soup.select_one(".old-price")
            vinyl_info["old_price"] = old_price_elem.text.strip("$") if old_price_elem else ""
            print(f"Old price: {vinyl_info['old_price']}")

            artist_elem = item_soup.select_one(".product-artist h3")
            vinyl_info["vinyl_artist"] = artist_elem.text.strip().title() if artist_elem else ""
            print(f"Artist: {vinyl_info['vinyl_artist']}")

            sale_elem = item_soup.select_one(".sale-label")
            vinyl_info["sale_label"] = sale_elem.text.strip().upper() if sale_elem else ""
            print(f"Sale label: {vinyl_info['sale_label']}")

            stock_elem = item_soup.select_one(".low-stock-label")
            vinyl_info["low_stock_label"] = stock_elem.text.strip().upper() if stock_elem else ""
            print(f"Stock label: {vinyl_info['low_stock_label']}")

            vinyl_info["genre"] = scrapingGenre.lower()

            # detail_link_elem = item_soup.select_one(".product-name")
            # detail_link = detail_link_elem["href"] if detail_link_elem else None
            # if detail_link:
            #     full_detail_url = f"https://vinyl.com{detail_link}"
            #     detail_response = session.get(full_detail_url)
            #     detail_soup = BeautifulSoup(detail_response.content, "html.parser")

            #     release_date = detail_soup.select_one(".release-date")
            #     vinyl_info["release_date"] = release_date.text.strip() if release_date else "N/A"
            #     print(f"Release Date: {vinyl_info['release_date']}")
            # else:
            #     vinyl_info["release_date"] = "N/A"

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
    # fieldnames = ["vinyl_title", "vinyl_artist", "price", "old_price", "release_date", "sale_label", "genre"]
    fieldnames = ["vinyl_img", "product_href", "vinyl_title", "vinyl_artist", "price", "old_price", "sale_label", "low_stock_label", "genre"]
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