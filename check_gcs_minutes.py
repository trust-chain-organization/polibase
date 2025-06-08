#!/usr/bin/env python3
"""Check GCS minutes content"""

from src.config.settings import get_settings
from src.utils.gcs_storage import GCSStorage

settings = get_settings()

if settings.gcs_upload_enabled and settings.gcs_bucket_name:
    gcs = GCSStorage(settings.gcs_bucket_name)
    content = gcs.download_content("gs://polibase-scraped-minutes/scraped/2025/04/23/unknown_unknown.txt")
    if content:
        # 最初の2000文字と最後の2000文字を表示
        print("=== 冒頭部分 ===")
        print(content[:2000])
        print("\n=== 末尾部分 ===")
        print(content[-2000:])
        print(f"\n全体の長さ: {len(content)}文字")