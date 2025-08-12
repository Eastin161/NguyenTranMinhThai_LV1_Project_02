import os

class Config:
    def __init__(self):
        # Project root directory
        self.PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Input/Output directories
        self.INPUT_DIR = os.path.join(self.PROJECT_ROOT, "input")
        self.OUTPUT_DIR = os.path.join(self.PROJECT_ROOT, "output")
        self.LOGS_DIR = os.path.join(self.PROJECT_ROOT, "logs")

        # File paths
        self.INPUT_FILE = os.path.join(self.INPUT_DIR, "list_products.csv")
        self.ERROR_FILE = os.path.join(self.LOGS_DIR, "Error.txt")
        self.DUPLICATE_FILE = os.path.join(self.LOGS_DIR, "Duplicates.txt")

        # Scraping settings
        self.CHUNK_SIZE = 1000
        self.MAX_RETRIES = 3
        self.RETRY_DELAY = 2  # seconds

        # API settings
        self.BASE_URL = "https://api.tiki.vn/product-detail/api/v1/products/{}"
        self.HEADERS = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }

        # Create directories if they don't exist
        self._create_directories()

        # Threading settings
        self.MAX_WORKERS = 10  # number of threads
        self.DELAY_BETWEEN_CALLS = 0.3  # seconds between requests

    def _create_directories(self):
        for directory in [self.INPUT_DIR, self.OUTPUT_DIR, self.LOGS_DIR]:
            os.makedirs(directory, exist_ok=True)
