# Standard Library Imports
import csv
import time
import re
import os

# Third-Party Imports
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# Local Application Imports
# (none for now)

class FlipkartScraper:
    """A scraper class to extract product details and reviews from Flipkart."""

    def __init__(self, output_dir="data"):
        """Initialize the FlipkartScraper.

        Args:
            output_dir (str, optional): Directory to store the output CSV files.
                Defaults to "data".
        """
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def get_top_reviews(self, product_url: str, count: int = 2) -> str:
        """Retrieve top reviews for a given product URL from Flipkart.

        Args:
            product_url (str): The URL of the product page on Flipkart.
            count (int, optional): Maximum number of top reviews to fetch.
                Defaults to 2.

        Returns:
            str: Concatenated top reviews separated by `||` if found,
                otherwise "No reviews found".
        """
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        driver = uc.Chrome(options=options, use_subprocess=True)

        if (
            not product_url
            or not isinstance(product_url, str)
            or not product_url.startswith("http")
        ):
            return "No reviews found"

        try:
            driver.get(product_url)
            time.sleep(4)

            # Try closing login popup if it appears
            try:
                driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
                time.sleep(1)
            except Exception as e:
                print(f"Error occurred while closing popup: {e}")

            # Scroll to load reviews
            for _ in range(4):
                ActionChains(driver).send_keys(Keys.END).perform()
                time.sleep(1.5)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            review_blocks = soup.select("div._27M-vq, div.col.EPCmJX, div._6K-7Co")
            seen = set()
            reviews = []

            for block in review_blocks:
                text = block.get_text(separator=" ", strip=True)
                if text and text not in seen:
                    reviews.append(text)
                    seen.add(text)
                if len(reviews) >= count:
                    break
        except Exception:
            reviews = []

        driver.quit()
        return " || ".join(reviews) if reviews else "No reviews found"

    def scrape_flipkart_products(
        self, query: str, max_products: int = 1, review_count: int = 2
    ) -> list:
        """Scrape Flipkart products and their details based on a search query.

        Args:
            query (str): The search query string (e.g., "iphone 14").
            max_products (int, optional): Maximum number of products to scrape.
                Defaults to 1.
            review_count (int, optional): Number of top reviews to fetch per product.
                Defaults to 2.

        Returns:
            list: A list of product details, where each product is represented as:
                [product_id, product_title, rating, total_reviews, price, top_reviews].
        """
        options = uc.ChromeOptions()
        driver = uc.Chrome(options=options, use_subprocess=True)
        search_url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
        driver.get(search_url)
        time.sleep(4)

        # Close login popup if it appears
        try:
            driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
        except Exception as e:
            print(f"Error occurred while closing popup: {e}")

        time.sleep(2)
        products = []

        items = driver.find_elements(By.CSS_SELECTOR, "div[data-id]")[:max_products]
        for item in items:
            try:
                title = item.find_element(By.CSS_SELECTOR, "div.KzDlHZ").text.strip()
                price = item.find_element(By.CSS_SELECTOR, "div.Nx9bqj").text.strip()
                rating = item.find_element(By.CSS_SELECTOR, "div.XQDdHH").text.strip()
                reviews_text = item.find_element(
                    By.CSS_SELECTOR, "span.Wphh3N"
                ).text.strip()
                match = re.search(r"\d+(,\d+)?(?=\s+Reviews)", reviews_text)
                total_reviews = match.group(0) if match else "N/A"

                link_el = item.find_element(By.CSS_SELECTOR, "a[href*='/p/']")
                href = link_el.get_attribute("href")
                # product_link = (
                #     href
                #     if href.startswith("http")
                #     else "https://www.flipkart.com" + href
                # )
                if href:
                    product_link = (
                        href
                        if href.startswith("http")
                        else "https://www.flipkart.com" + href
                    )
                else:
                    product_link = None

                # match = re.findall(r"/p/(itm[0-9A-Za-z]+)", href)
                match = re.findall(r"/p/(itm[0-9A-Za-z]+)", href) if href else []
                product_id = match[0] if match else "N/A"
            except Exception as e:
                print(f"Error occurred while processing item: {e}")
                continue

            # top_reviews = (
            #     self.get_top_reviews(product_link, count=review_count)
            #     if "flipkart.com" in product_link
            #     else "Invalid product URL"
            # )
            top_reviews = (
                self.get_top_reviews(product_link, count=review_count)
                if product_link and "flipkart.com" in product_link
                else "Invalid product URL"
            )

            products.append(
                [product_id, title, rating, total_reviews, price, top_reviews]
            )

        driver.quit()
        return products

    def save_to_csv(self, data: list, filename: str = "product_reviews.csv") -> None:
        """Save scraped product data into a CSV file.

        Args:
            data (list): List of product details to be written to the CSV file.
            filename (str, optional): Name of the output file.
                Defaults to "product_reviews.csv".

        Returns:
            None
        """
        if os.path.isabs(filename):
            path = filename
        elif os.path.dirname(
            filename
        ):  # filename includes subfolder like 'data/product_reviews.csv'
            path = filename
            os.makedirs(os.path.dirname(path), exist_ok=True)
        else:
            # plain filename like 'output.csv'
            path = os.path.join(self.output_dir, filename)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "product_id",
                    "product_title",
                    "rating",
                    "total_reviews",
                    "price",
                    "top_reviews",
                ]
            )
            writer.writerows(data)
