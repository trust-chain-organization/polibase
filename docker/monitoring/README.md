# Polibase監視システム

このディレクトリには、Polibaseアプリケーションの監視に必要な設定ファイルが含まれています。

## 構成要素

- **Grafana**: メトリクスとログの可視化ダッシュボード
- **Prometheus**: メトリクス収集とストレージ
- **Loki**: ログ集約システム
- **Promtail**: ログ収集エージェント
- **Node Exporter**: システムメトリクス収集
- **PostgreSQL Exporter**: データベースメトリクス収集

## クイックスタート

```bash
# プロジェクトルートから実行
cd /path/to/polibase

# 監視サービスを起動
docker compose -f docker/docker-compose.yml -f docker/docker-compose.monitoring.yml up -d

# サービスの確認
docker compose -f docker/docker-compose.yml -f docker/docker-compose.monitoring.yml ps
```

## アクセスURL

- **Grafana**: http://localhost:3000 (初期: admin/admin)
- **Prometheus**: http://localhost:9091
- **Loki**: http://localhost:3100

## ディレクトリ構造

```
monitoring/
├── grafana/
│   ├── provisioning/
│   │   ├── dashboards/     # ダッシュボード設定
│   │   └── datasources/    # データソース設定
│   └── dashboards/         # ダッシュボードJSON
├── prometheus/
│   ├── prometheus.yml      # Prometheus設定
│   └── alerts/            # アラートルール
├── loki/
│   └── loki-config.yaml   # Loki設定
└── promtail/
    └── promtail-config.yaml # Promtail設定
```

## 詳細なドキュメント

[Grafana監視システムセットアップガイド](../../docs/monitoring/grafana-setup.md)を参照してください。
