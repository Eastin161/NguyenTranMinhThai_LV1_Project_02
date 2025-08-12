# Tiki Product Scraper

A Python tool for scraping product information from Tiki.vn API with robust error handling, retry mechanisms, and duplicate detection.

## Features

- **Batch Processing**: Process 200,000 of product IDs in configurable chunks
- **Multi-threaded scraping** for faster data collection
- **Retry Logic**: Automatic retry with exponential backoff for failed requests
- **Duplicate Detection**: Identifies and logs duplicate product IDs before processing
- **Comprehensive Logging**: Detailed error logs and processing statistics
- **Rate Limit Handling**: Respects API rate limits with intelligent waiting
- **JSON Output**: Clean, structured JSON output for easy data processing


