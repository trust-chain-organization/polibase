# コードの配置

.
├── src/
│   ├── config/              # 設定関連 (必要であれば)
│   │   └── __init__.py
│   │   └── settings.py
│   ├── minutes_divide_processor/   # 議事録分割処理
│   │   ├── __init__.py
│   │   ├── dividor.py
│   │   ├── agent.py
│   │   └── models.py
│   ├── metadata_processor/  # 会議メタデータ処理
│   │   ├── __init__.py
│   │   ├── collector.py
│   │   ├── storage.py
│   │   └── models.py
│   ├── politician_processor/ # 政治家情報処理
│   │   ├── __init__.py
│   │   ├── scraper.py
│   │   ├── db_handler.py
│   │   ├── linker.py
│   │   └── models.py
│   ├── utils/               # 共通ユーティリティ
│   │   ├── __init__.py
│   │   └── text_extractor.py
│   └── main.py              # エントリーポイント
├── data/
│   ├── input/
│   └── output/
├── tests/                   # テストコード
│   └── ...
├── pyproject.toml           # or requirements.txt
├── README.md
└── .gitignore
