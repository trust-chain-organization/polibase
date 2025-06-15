#!/bin/bash
set -e

echo "================================================"
echo "Polibase 統合テスト - 全機能"
echo "================================================"
echo "開始時刻: $(date)"
echo ""

# カラー定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# テスト結果を保存する配列
declare -a TEST_RESULTS

# テスト実行関数
run_test() {
    local test_name=$1
    local test_script=$2

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$test_name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if [ -f "$test_script" ]; then
        if bash "$test_script"; then
            TEST_RESULTS+=("$test_name: ${GREEN}✓ 成功${NC}")
        else
            TEST_RESULTS+=("$test_name: ${RED}✗ 失敗${NC}")
        fi
    else
        echo -e "${YELLOW}テストスクリプトが見つかりません: $test_script${NC}"
        TEST_RESULTS+=("$test_name: ${YELLOW}⚠ スキップ${NC}")
    fi
}

# Python テスト実行関数
run_python_test() {
    local test_name=$1
    local test_script=$2

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$test_name (Python)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if [ -f "$test_script" ]; then
        if docker compose exec polibase uv run python "$test_script"; then
            TEST_RESULTS+=("$test_name (Python): ${GREEN}✓ 成功${NC}")
        else
            TEST_RESULTS+=("$test_name (Python): ${RED}✗ 失敗${NC}")
        fi
    else
        echo -e "${YELLOW}テストスクリプトが見つかりません: $test_script${NC}"
        TEST_RESULTS+=("$test_name (Python): ${YELLOW}⚠ スキップ${NC}")
    fi
}

# メインテスト実行
echo "テストモードを選択してください:"
echo "1) 基本テストのみ (推奨)"
echo "2) 詳細テストを含む"
echo "3) すべてのテスト"
read -p "選択 (1-3): " -n 1 -r TEST_MODE
echo ""

# 基本テスト
echo ""
echo -e "${GREEN}【基本テスト】${NC}"

# データベース管理
run_test "データベース管理" "database/test_database_management.sh"

# 議事録処理
run_test "議事録処理" "minutes/test_minutes_processing.sh"

# 政治家情報抽出
run_test "政治家情報抽出" "politicians/test_politicians_extraction.sh"

# 会議体メンバー管理
run_test "会議体メンバー管理" "conference/test_conference_members.sh"

# 議員団管理
run_test "議員団管理" "parliamentary/test_parliamentary_group_extraction.sh"

# スクレイピング
run_test "スクレイピング" "scraping/test_scraping.sh"

# 詳細テスト
if [ "$TEST_MODE" == "2" ] || [ "$TEST_MODE" == "3" ]; then
    echo ""
    echo -e "${GREEN}【詳細テスト (Python)】${NC}"

    run_python_test "データベース詳細" "database/test_database_detailed.py"
    run_python_test "議事録処理詳細" "minutes/test_minutes_detailed.py"
    run_python_test "政治家情報詳細" "politicians/test_politicians_detailed.py"
    run_python_test "会議体メンバー詳細" "conference/test_conference_detailed.py"
    run_python_test "スクレイピング詳細" "scraping/test_scraping_detailed.py"
fi

# システムヘルスチェック
if [ "$TEST_MODE" == "3" ]; then
    echo ""
    echo -e "${GREEN}【システムヘルスチェック】${NC}"

    echo ""
    echo "Docker コンテナ状態:"
    docker compose ps

    echo ""
    echo "リソース使用状況:"
    docker stats --no-stream
fi

# テスト結果サマリー
echo ""
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}テスト結果サマリー${NC}"
echo -e "${BLUE}================================================${NC}"

for result in "${TEST_RESULTS[@]}"; do
    echo -e "$result"
done

echo ""
echo "終了時刻: $(date)"

# 成功/失敗の集計
SUCCESS_COUNT=$(printf '%s\n' "${TEST_RESULTS[@]}" | grep -c "✓" || true)
FAILURE_COUNT=$(printf '%s\n' "${TEST_RESULTS[@]}" | grep -c "✗" || true)
SKIP_COUNT=$(printf '%s\n' "${TEST_RESULTS[@]}" | grep -c "⚠" || true)

echo ""
echo "統計:"
echo -e "  成功: ${GREEN}$SUCCESS_COUNT${NC}"
echo -e "  失敗: ${RED}$FAILURE_COUNT${NC}"
echo -e "  スキップ: ${YELLOW}$SKIP_COUNT${NC}"

# 終了コード
if [ "$FAILURE_COUNT" -gt 0 ]; then
    echo ""
    echo -e "${RED}テストに失敗があります${NC}"
    exit 1
else
    echo ""
    echo -e "${GREEN}すべてのテストが正常に完了しました${NC}"
    exit 0
fi
