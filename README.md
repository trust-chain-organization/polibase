# テーブル構造
こちらにプロジェクトのテーブル構造を記載します。
https://dbdocs.io/polibase/Polibase

# 開発環境の生成AIの設定
https://code.visualstudio.com/docs/copilot/copilot-customization

- .github/prompts/hogehoge.prompt.md
  - chat/editで使えるカスタムのプロンプトを配置

- .vscode/settings.json
    - 開発環境の設定を記載
    - このプロジェクト用のMCPの設定を記載
- .github/copilot-instructions.md
  - エージェントが従う作業フローの指示を記載
    - プロダクトマネージャー業務の指示
        - product_management業務の参照ドキュメント
            - product_management_reference/product_goal.md
            - product_management_reference/daily_task.md
    - コード修正業務の指示
- このプロジェクト用のcopilotの作業時の設定を記載(copilot-instructions.mdを継承)
    - .vscode/code-style.md
        - コード生成時のルール
    - .vscode/test-style.md
        - テスト生成時のルール
    - .vscode/review-style.md
        - レビュー時のルール
    - .vscode/commit-message-style.md
        - コミットメッセージの生成時のルール
    - .vscode/pull-request-style.md
        - pull requestの生成時のルール
