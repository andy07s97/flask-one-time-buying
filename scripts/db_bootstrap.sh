#!/usr/bin/env bash
set -euo pipefail

# 1) 進入專案根目錄再跑（確保能 import app.create_app）
# 2) 確保已 source venv，且 .env 已準備好 DATABASE_URL 等設定

export FLASK_APP="app:create_app"

# migrations 只需 init 一次；做成可重跑
if [ ! -d "migrations" ]; then
  flask db init
fi

flask db migrate -m "init orders + download_tokens" || true
flask db upgrade
echo "Done. DB schema is ready."

## 使用指令如下
# chmod +x scripts/db_bootstrap.sh
# ./scripts/db_bootstrap.sh
