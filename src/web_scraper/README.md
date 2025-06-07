# Web Scraper Module

This module provides a modular and extensible architecture for scraping meeting minutes from various Japanese council websites.

## Architecture Overview

The web scraper has been refactored to follow the Single Responsibility Principle with the following components:

### Core Components

1. **Models** (`models/`)
   - `MinutesData`: Main data model for scraped meeting minutes
   - `SpeakerData`: Model for speaker information within minutes

2. **Extractors** (`extractors/`)
   - `ContentExtractor`: HTML parsing and content extraction
   - `DateParser`: Japanese date parsing utilities (令和/平成/西暦)
   - `SpeakerExtractor`: Speaker information extraction from minutes

3. **Handlers** (`handlers/`)
   - `PDFHandler`: PDF download and text extraction
   - `FileHandler`: File management utilities

4. **Base Classes**
   - `BaseScraper`: Abstract base class for all scrapers
   - `KaigirokuNetScraper`: Implementation for kaigiroku.net system

5. **Services**
   - `ScraperService`: High-level service for scraping operations

## Usage Examples

### Basic Scraping

```python
from src.web_scraper import KaigirokuNetScraper

scraper = KaigirokuNetScraper()
minutes = await scraper.fetch_minutes("https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=6030&schedule_id=1")

if minutes:
    print(f"Title: {minutes.title}")
    print(f"Date: {minutes.date}")
    print(f"Speakers: {len(minutes.speakers)}")
```

### Using the Service Layer

```python
from src.web_scraper import ScraperService

service = ScraperService()

# Single URL with caching
minutes = await service.fetch_from_url(url, use_cache=True)

# Multiple URLs concurrently
urls = ["url1", "url2", "url3"]
results = await service.fetch_multiple(urls, max_concurrent=3)

# Export to various formats
success, gcs_url = service.export_to_text(minutes, "output.txt", upload_to_gcs=True)
```

### Custom Date Parsing

```python
from src.web_scraper.extractors import DateParser

parser = DateParser()
date = parser.parse("令和6年12月20日")  # Returns datetime(2024, 12, 20)
```

### Speaker Extraction

```python
from src.web_scraper.extractors import SpeakerExtractor

extractor = SpeakerExtractor()
speakers = extractor.extract_speakers(content)
# Returns list of SpeakerData objects with name, content, and role
```

## Supported Websites

Currently supports:
- **kaigiroku.net system**: Used by many Japanese local councils
  - Kyoto City Council
  - Osaka City Council
  - Kobe City Council
  - And many others using the same system

## Error Handling

The module provides specific exceptions for different error scenarios:

- `ScraperConnectionError`: Connection failures
- `ScraperParseError`: Content parsing errors
- `ScraperTimeoutError`: Timeout during scraping
- `PDFDownloadError`: PDF download failures
- `PDFExtractionError`: PDF text extraction errors
- `CacheError`: Cache operation failures
- `GCSUploadError`: Google Cloud Storage upload failures

## Extension Points

To add support for a new council website:

1. Create a new scraper class inheriting from `BaseScraper`
2. Implement the required abstract methods
3. Register it in `ScraperService._get_scraper_for_url()`

Example:
```python
from src.web_scraper import BaseScraper

class CustomCouncilScraper(BaseScraper):
    async def fetch_minutes(self, url: str) -> Optional[MinutesData]:
        # Implementation
        pass
    
    async def extract_minutes_text(self, html_content: str) -> str:
        # Implementation
        pass
    
    async def extract_speakers(self, html_content: str) -> List[SpeakerData]:
        # Implementation
        pass
```

## Dependencies

- `playwright`: For JavaScript-heavy websites
- `beautifulsoup4`: HTML parsing
- `pypdfium2`: PDF text extraction (optional)
- `aiohttp`: Async HTTP requests

## Testing

Run tests with:
```bash
docker compose exec polibase uv run pytest tests/test_web_scraper.py -v
```