# Output Directory

This directory contains the scraped product data in JSON format.

## Generated Files

The scraper creates numbered JSON files based on the CHUNK_SIZE setting:

- `products_1.json` - First 1000 products (or whatever CHUNK_SIZE is set to)
- `products_2.json` - Next 1000 products
- `products_3.json` - And so on...

## File Structure

Each JSON file contains an array of product objects:
