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

        visible_items = [item for item in driver.find_elements(By.CSS_SELECTOR, ".product-grid .product-item") if item.is_displayed()]
        print(f"Found {len(visible_items)} visible vinyl items in product grid")
    except Exception as e:
        print(f"Error applying filters: {e}")

    return driver

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
    for i, item in enumerate(vinyl_items):  # Removed [:2] to scrape all items
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
            print(f"No stock label {i+1}: {vinyl_info['no_stock_label']}")

            vinyl_info["genre"] = scrapingGenre.lower()

            detail_link = product_link_elem["href"] if product_link_elem else None
            item_details.append((vinyl_info, detail_link))
        except Exception as e:
            print(f"Error collecting basic info for item {i+1}: {e}")
            continue

    # Second pass: Fetch detail pages with Selenium
    for i, (vinyl_info, detail_link) in enumerate(item_details):
        try:
            if detail_link:
                full_detail_url = f"https://vinyl.com{detail_link}"
                driver.get(full_detail_url)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".product-info p"))
                )
                detail_soup = BeautifulSoup(driver.page_source, "html.parser")
                with open(f"detail_page_{i+1}.html", "w", encoding="utf-8") as f:
                    f.write(detail_soup.prettify())
                print(f"Saved detail page to detail_page_{i+1}.html for {full_detail_url}")

                # Vinyl description
                description_elements = detail_soup.select(".inner-show-read-more p")
                description = [p.text.strip() for p in description_elements] if description_elements else ["N/A"]
                vinyl_info["vinyl_description"] = " ".join(description) if description != ["N/A"] else "N/A"

                # Product info
                product_info_elem = detail_soup.select(".product-info p")
                print(f"Product elements {i+1}: {product_info_elem}")
                product_info = [p.text.strip() for p in product_info_elem if p.text.strip()] if product_info_elem else ["N/A"]
                print(f"Product INFO {i+1}: {product_info}")
                vinyl_info["vinyl_info"] = product_info
            else:
                vinyl_info["vinyl_info"] = ["N/A"]
                print(f"Item {i+1}: NO DETAIL PAGE ACCESSED")

            vinyl_data.append(vinyl_info)
            time.sleep(1)  # Delay between detail page requests
        except Exception as e:
            print(f"Error scraping detail page for item {i+1}: {e}")
            vinyl_info["vinyl_info"] = ["N/A"]
            vinyl_data.append(vinyl_info)  # Still add partial data
            continue

    driver.quit()
    write_to_csv(vinyl_data)
    return vinyl_data

def write_to_csv(data):
    if not data:
        print("No data to write")
        return
    fieldnames = ["vinyl_info", "vinyl_img", "product_href", "vinyl_title", "vinyl_artist", "price", "old_price", "sale_label", "low_stock_label", "no_stock_label", "genre", "vinyl_description"]
    with open(f"{scrapingGenre.lower()}_vinyl_data.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print(f"Data written to {scrapingGenre.lower()}_vinyl_data.csv")

def main():
    print("Starting scraper...")
    scraped_data = scrape_vinyl_data()
    print(f"Scraped {len(scraped_data)} vinyl records")

if __name__ == "__main__":
    main()