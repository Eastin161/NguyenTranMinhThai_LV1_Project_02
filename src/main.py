"""
Tiki Product Scraper - Main Application
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper import TikiScraper
from config import Config

def main():
    scraper = TikiScraper(Config())
    scraper.main()

def retry_only():
    scraper = TikiScraper(Config())
    scraper.retry_failed_ids()

def main_threaded():
    scraper = TikiScraper(Config())
    scraper.main_threaded()

if __name__ == "__main__":
    main_threaded()  # Use threading for multiproceesing
    #main()          # Use 1 process
    # retry_only()
