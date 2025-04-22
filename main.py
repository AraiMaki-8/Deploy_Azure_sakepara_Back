import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# 超シンプルなAPIを作成 - データベース接続なし
app = FastAPI()

# CORS設定（フロントエンドとの通信を許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 固定のダミーデータ
DUMMY_USERS = [
    {"id": 1, "name": "山田太郎", "company_name": "サンプル株式会社"},
    {"id": 2, "name": "佐藤花子", "company_name": "テスト合同会社"},
    {"id": 3, "name": "鈴木一郎", "company_name": "デモ企業"}
]

DUMMY_BALANCES = [
    {"user_id": 1, "current_points": 500, "expiring_points": 100},
    {"user_id": 2, "current_points": 1000, "expiring_points": 200},
    {"user_id": 3, "current_points": 1500, "expiring_points": 0}
]

DUMMY_HISTORY = [
    {"id": 1, "user_id": 1, "date": datetime.utcnow(), "description": "初回登録ボーナス", "points": 500},
    {"id": 2, "user_id": 2, "date": datetime.utcnow(), "description": "商品購入", "points": 1000},
    {"id": 3, "user_id": 3, "date": datetime.utcnow(), "description": "友達紹介ボーナス", "points": 1500}
]

DUMMY_ITEMS = [
    {"id": 1, "name": "QUOカード 500円分", "points_required": 500},
    {"id": 2, "name": "Amazonギフト券 1000円分", "points_required": 1000},
    {"id": 3, "name": "高級ディナー招待券", "points_required": 2000}
]

# ルートエンドポイント
@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Point Management System API! (超シンプル版)",
        "status": "正常",
        "mode": "固定データのみ - データベース接続なし"
    }

# データベース接続テスト用エンドポイント
@app.get("/test-db-connection")
def test_db_connection():
    return {
        "status": "success",
        "message": "テストモード: 固定データのみを使用",
        "mode": "データベースなし"
    }

# ユーザー一覧取得API
@app.get("/users")
def get_users():
    return DUMMY_USERS

# 特定ユーザー情報取得API
@app.get("/users/{user_id}")
def get_user(user_id: int):
    for user in DUMMY_USERS:
        if user["id"] == user_id:
            return user
    return {"error": "User not found"}

# ユーザーの残高取得API
@app.get("/users/{user_id}/balance")
def get_user_balance(user_id: int):
    for balance in DUMMY_BALANCES:
        if balance["user_id"] == user_id:
            return balance
    return {"error": "Balance not found"}

# ユーザーのポイント履歴取得API
@app.get("/users/{user_id}/point-history")
def get_point_history(user_id: int):
    user_history = []
    for history in DUMMY_HISTORY:
        if history["user_id"] == user_id:
            user_history.append(history)
    return user_history

# アイテム一覧取得API
@app.get("/redeemable-items")
def get_redeemable_items():
    return DUMMY_ITEMS

# ==============================
# 🎯 FastAPI の起動コマンド
# ==============================
# uvicorn main:app --reload