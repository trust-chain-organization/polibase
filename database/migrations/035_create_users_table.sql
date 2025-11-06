-- Create users table for managing logged-in users
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    picture TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_last_login_at ON users(last_login_at);

-- Add comments
COMMENT ON TABLE users IS 'ログインユーザーを管理するテーブル';
COMMENT ON COLUMN users.user_id IS 'ユーザーID（UUID）';
COMMENT ON COLUMN users.email IS 'メールアドレス（一意）';
COMMENT ON COLUMN users.name IS 'ユーザーの表示名';
COMMENT ON COLUMN users.picture IS 'プロフィール画像のURL';
COMMENT ON COLUMN users.created_at IS 'ユーザー作成日時';
COMMENT ON COLUMN users.last_login_at IS '最終ログイン日時';
