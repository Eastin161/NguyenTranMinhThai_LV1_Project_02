import requests
import json
import os
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

class TikiScraper:
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()

    def load_ids(self):
        if not os.path.exists(self.config.INPUT_FILE):
            print(f"❌ Input file not found: {self.config.INPUT_FILE}")
            return []

        with open(self.config.INPUT_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip().isdigit()]

    def clean_description(self, html):
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator=" ").strip()

    def check_duplicates(self, product_ids):
        seen_ids = set()
        unique_ids = []
        duplicates = []

        for pid in product_ids:
            if pid in seen_ids:
                duplicates.append(pid)
                print(f"🔄 Duplicate ID found: {pid}")
            else:
                seen_ids.add(pid)
                unique_ids.append(pid)

        return unique_ids, duplicates

    def fetch_product_with_retry(self, product_id, error_log):

        def single_fetch(product_id):
            url = self.config.BASE_URL.format(product_id)
            response = self.session.get(url, headers=self.config.HEADERS, timeout=10)

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                print(f"⏳ Rate limit hit for ID {product_id}, waiting {retry_after} seconds")
                time.sleep(retry_after)
                raise requests.exceptions.HTTPError(f"429 Too Many Requests")

            if response.status_code != 200:
                raise requests.exceptions.HTTPError(f"HTTP {response.status_code}")

            data = response.json()
            return {
                "id": data.get("id"),
                "name": data.get("name"),
                "url_key": data.get("url_key"),
                "price": data.get("price"),
                "description": self.clean_description(data.get("description", "")),
                "images": [img.get("thumbnail_url") for img in data.get("images", []) if img.get("thumbnail_url")]
            }

        # Retry
        for attempt in range(1, self.config.MAX_RETRIES + 1):
            try:
                result = single_fetch(product_id)
                if attempt > 1:
                    print(f"✅ Success on retry {attempt} for ID {product_id}")
                return result

            except Exception as e:
                print(f"❌ Attempt {attempt} failed for ID {product_id}: {e}")

                if attempt == self.config.MAX_RETRIES:
                    # Final failure
                    if "429" in str(e):
                        error_log.append(f"{product_id},429_final_failure")
                    elif "HTTP" in str(e):
                        status_code = str(e).split()[-1]
                        error_log.append(f"{product_id},{status_code}")
                    else:
                        error_log.append(f"{product_id},Exception:{str(e)}")
                    return None
                else:
                    # Wait before retry
                    wait_time = self.config.RETRY_DELAY * attempt
                    print(f"⏳ Waiting {wait_time} seconds before retry {attempt + 1}")
                    time.sleep(wait_time)

        return None

    def save_chunk(self, chunk, index):
        filename = os.path.join(self.config.OUTPUT_DIR, f"products_{index}.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False, indent=2)
        print(f"✅ Saved {len(chunk)} products to {filename}")

    def save_duplicates(self, duplicates):
        if duplicates:
            with open(self.config.DUPLICATE_FILE, "w", encoding="utf-8") as f:
                f.write("duplicate_product_id\n")
                for duplicate_id in duplicates:
                    f.write(f"{duplicate_id}\n")
            print(f"🔄 Saved {len(duplicates)} duplicate IDs to {self.config.DUPLICATE_FILE}")

    def retry_failed_ids(self):
        if not os.path.exists(self.config.ERROR_FILE):
            print("No error file found to retry")
            return

        retry_ids = []
        with open(self.config.ERROR_FILE, "r", encoding="utf-8") as f:
            next(f)  # Skip header
            for line in f:
                if line.strip():
                    product_id = line.split(",")[0]
                    retry_ids.append(product_id)

        if not retry_ids:
            print("No failed IDs to retry")
            return

        print(f"🔄 Retrying {len(retry_ids)} failed IDs...")

        products = []
        errors = []
        file_index = 1

        # if error id successful at retry, check and save it to the next index of products.json
        existing_files = [f for f in os.listdir(self.config.OUTPUT_DIR) 
                         if f.startswith("products_") and f.endswith(".json")]
        if existing_files:
            file_numbers = [int(f.split("_")[1].split(".")[0]) for f in existing_files]
            file_index = max(file_numbers) + 1

        for i, pid in enumerate(retry_ids, 1):
            print(f"🔄 Retrying ID {pid} ({i}/{len(retry_ids)})")
            product = self.fetch_product_with_retry(pid, errors)
            if product:
                products.append(product)

            if len(products) == self.config.CHUNK_SIZE:
                self.save_chunk(products, file_index)
                file_index += 1
                products = []

        if products:
            self.save_chunk(products, file_index)

        if errors:
            retry_error_file = self.config.ERROR_FILE.replace(".txt", "_retry.txt")
            with open(retry_error_file, "w", encoding="utf-8") as f:
                f.write("product_id,status\n")
                for line in errors:
                    f.write(line + "\n")
            print(f"⚠️ Saved {len(errors)} still-failed IDs to {retry_error_file}")

    def main(self):
        print("🚀 Loading product IDs...")
        all_product_ids = self.load_ids()

        if not all_product_ids:
            print("❌ No product IDs found. Please check your input file.")
            return

        print(f"📊 Loaded {len(all_product_ids)} total IDs")

        # Check for duplicates
        print("🔍 Checking for duplicates...")
        unique_product_ids, duplicates = self.check_duplicates(all_product_ids)
        print(f"✨ Found {len(unique_product_ids)} unique IDs")

        # Save duplicates log
        self.save_duplicates(duplicates)

        products = []
        errors = []
        file_index = 1

        print("🔍 Starting to fetch products...")
        for i, pid in enumerate(unique_product_ids, 1):
            print(f"🔍 Fetching ID {pid} ({i}/{len(unique_product_ids)})")
            product = self.fetch_product_with_retry(pid, errors)
            if product:
                products.append(product)

            if len(products) == self.config.CHUNK_SIZE:
                self.save_chunk(products, file_index)
                file_index += 1
                products = []

        if products:
            self.save_chunk(products, file_index)

        # Save errors
        if errors:
            with open(self.config.ERROR_FILE, "w", encoding="utf-8") as f:
                f.write("product_id,status\n")
                for line in errors:
                    f.write(line + "\n")
            print(f"⚠️ Saved {len(errors)} failed IDs to {self.config.ERROR_FILE}")

        print(f"✅ Process completed!")
        print(f"📊 Summary: {len(unique_product_ids)} unique IDs, {len(duplicates)} duplicates, {len(errors)} errors")

    def main_threaded(self):
        """Main scraping process with threading"""
        print("🚀 Loading product IDs...")
        all_product_ids = self.load_ids()

        if not all_product_ids:
            print("❌ No product IDs found. Please check your input file.")
            return

        print(f"📊 Loaded {len(all_product_ids)} total IDs")

        # Check for duplicates
        print("🔍 Checking for duplicates...")
        unique_product_ids, duplicates = self.check_duplicates(all_product_ids)
        print(f"✨ Found {len(unique_product_ids)} unique IDs")

        # Save duplicates log
        self.save_duplicates(duplicates)

        products = []
        errors = []
        file_index = 1

        print(f"🚀 Starting with {len(unique_product_ids)} IDs using {self.config.MAX_WORKERS} threads...")

        with ThreadPoolExecutor(max_workers=self.config.MAX_WORKERS) as executor:
            # Submit all tasks and store futures with their corresponding product IDs
            future_to_pid = {executor.submit(self.fetch_product_threaded, pid): pid for pid in unique_product_ids}
            
            for i, future in enumerate(tqdm(as_completed(future_to_pid), total=len(future_to_pid)), 1):
                try:
                    result, error = future.result()
                    if result:
                        products.append(result)
                        print(f"✅ Added product ID {result['id']}")
                    if error:
                        errors.append(error)

                    if len(products) == self.config.CHUNK_SIZE:
                        self.save_chunk(products, file_index)
                        file_index += 1
                        products = []

                except Exception as e:
                    pid = future_to_pid[future]
                    print(f"🔥 Crash for ID {pid}: {type(e).__name__}: {e}")
                    errors.append(f"{pid},ThreadCrash:{type(e).__name__}:{e}")

        if products:
            self.save_chunk(products, file_index)

        # Save errors
        if errors:
            with open(self.config.ERROR_FILE, "w", encoding="utf-8") as f:
                f.write("product_id,status\n")
                for line in errors:
                    f.write(line + "\n")
        print(f"⚠️ Saved {len(errors)} failed IDs to {self.config.ERROR_FILE}")

        print(f"✅ Process completed!")
        print(f"📊 Summary: {len(unique_product_ids)} unique IDs, {len(duplicates)} duplicates, {len(errors)} errors")

    def fetch_product_threaded(self, product_id):
        """Fetch product with threading-compatible return format"""
        import time
        
        for attempt in range(1, self.config.MAX_RETRIES + 1):
            try:
                time.sleep(self.config.DELAY_BETWEEN_CALLS)
                url = self.config.BASE_URL.format(product_id)
                response = self.session.get(url, headers=self.config.HEADERS, timeout=10)

                if response.status_code == 429:
                    wait_time = int(response.headers.get("Retry-After", 2))
                    print(f"⏳ 429 Too Many Requests for ID {product_id}, retrying after {wait_time} sec (attempt {attempt})")
                    time.sleep(wait_time)
                    continue

                if response.status_code != 200:
                    return None, f"{product_id},{response.status_code}"

                try:
                    data = response.json()
                except Exception as e:
                    return None, f"{product_id},JSONDecodeError:{e}"

                return {
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "url_key": data.get("url_key"),
                    "price": data.get("price"),
                    "description": self.clean_description(data.get("description", "")),
                    "images": [img.get("thumbnail_url") for img in data.get("images", []) if img.get("thumbnail_url")]
                }, None

            except Exception as e:
                print(f"🔥 Exception for ID {product_id} on attempt {attempt}: {e}")
                time.sleep(2)

        return None, f"{product_id},FailedAfter{self.config.MAX_RETRIES}Retries"
