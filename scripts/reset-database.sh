#!/bin/bash
# PostgreSQLデータベースリセットスクリプト

echo "🗑️  Polibase データベースリセット"
echo "=================================="

# 確認メッセージ
echo "⚠️  注意: この操作は以下を実行します:"
echo "   - PostgreSQLコンテナを停止"
echo "   - データベースボリュームを削除 (全データが失われます)"
echo "   - コンテナを再作成してデータベースを初期化"
echo ""
read -p "本当に実行しますか？ (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 操作をキャンセルしました"
    exit 0
fi

echo ""
echo "🛑 PostgreSQLコンテナを停止中..."
docker compose stop postgres

echo "🗑️  データベースボリュームを削除中..."
docker compose down -v

echo "🚀 コンテナを再作成中..."
docker compose up -d postgres

echo "⏳ PostgreSQLの起動を待機中..."
sleep 10

# PostgreSQLの起動確認
while ! docker compose exec -T postgres pg_isready -U polibase_user -d polibase_db > /dev/null 2>&1; do
    echo "   PostgreSQL起動待機中..."
    sleep 2
done

echo "✅ PostgreSQLが起動しました"

echo ""
echo "🔍 データベース初期化状態を確認中..."
docker compose exec -T postgres psql -U polibase_user -d polibase_db -c "\dt"

echo ""
echo "🎉 データベースリセット完了！"
echo "初期データが設定されています："
docker compose exec -T postgres psql -U polibase_user -d polibase_db -c "SELECT name, type FROM governing_bodies;"
docker compose exec -T postgres psql -U polibase_user -d polibase_db -c "SELECT name FROM political_parties;"

echo ""
echo "📝 次のステップ:"
echo "   - アプリケーションを起動: docker compose up -d"
echo "   - セットアップテスト: ./test-setup.sh"
