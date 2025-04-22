import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import mysql.connector
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# アプリケーション初期化
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

# データベース接続情報
def get_db_config():
    config = {
        "user": os.getenv("MYSQL_USER", "sakeparadb"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "host": os.getenv("MYSQL_HOST", "tech0-gen-8-step4-sakepara-db.mysql.database.azure.com"),
        "port": os.getenv("MYSQL_PORT", "3306"),
        "database": os.getenv("MYSQL_DATABASE", "point_program_db"),
        "ssl_ca": os.getenv("MYSQL_SSL_CA", "DigiCertGlobalRootCA.crt.pem")
    }
    logger.info(f"DB設定: ホスト={config['host']}, ポート={config['port']}, DB={config['database']}, ユーザー={config['user']}")
    return config

# データベース接続を試みる関数
def get_db_connection():
    try:
        config = get_db_config()
        # パスワード以外のログを出力
        logger.info(f"データベース接続を試みています: {config['host']}:{config['port']}/{config['database']} (ユーザー: {config['user']})")
        
        # SSL_CAファイルのパスを確認
        ssl_ca_path = config['ssl_ca']
        if os.path.exists(ssl_ca_path):
            logger.info(f"SSL CA ファイルが見つかりました: {ssl_ca_path}")
        else:
            logger.warning(f"SSL CA ファイルが見つかりません: {ssl_ca_path}")
            
        conn = mysql.connector.connect(
            user=config["user"],
            password=config["password"],
            host=config["host"],
            port=config["port"],
            database=config["database"],
            ssl_ca=ssl_ca_path
        )
        
        logger.info("データベース接続に成功しました")
        return conn
    except Exception as e:
        logger.error(f"データベース接続エラー: {str(e)}")
        raise e

# ルートエンドポイント
@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Point Management System API!",
        "status": "正常",
        "version": "1.0"
    }

# データベース接続テスト用エンドポイント
@app.get("/test-db-connection")
def test_db_connection():
    try:
        conn = get_db_connection()
        conn.close()
        
        config = get_db_config()
        # パスワードを除外
        config_safe = {k: v for k, v in config.items() if k != "password"}
        
        return {
            "success": True,
            "message": "データベース接続成功！",
            "config": config_safe,
            "environment_variables": {
                "MYSQL_USER": os.getenv("MYSQL_USER", "未設定"),
                "MYSQL_HOST": os.getenv("MYSQL_HOST", "未設定"),
                "MYSQL_PORT": os.getenv("MYSQL_PORT", "未設定"),
                "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE", "未設定"),
                "MYSQL_SSL_CA": os.getenv("MYSQL_SSL_CA", "未設定"),
                "PASSWORD_SET": "はい" if os.getenv("MYSQL_PASSWORD") else "いいえ"
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"データベース接続エラー: {str(e)}",
            "mode": "フォールバック：固定データを使用",
            "environment_variables": {
                "MYSQL_USER": os.getenv("MYSQL_USER", "未設定"),
                "MYSQL_HOST": os.getenv("MYSQL_HOST", "未設定"),
                "MYSQL_PORT": os.getenv("MYSQL_PORT", "未設定"),
                "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE", "未設定"),
                "MYSQL_SSL_CA": os.getenv("MYSQL_SSL_CA", "未設定"),
                "PASSWORD_SET": "はい" if os.getenv("MYSQL_PASSWORD") else "いいえ"
            }
        }

# ユーザー一覧取得API
@app.get("/users")
def get_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, company_name FROM users")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return users
    except Exception as e:
        logger.error(f"ユーザー取得エラー: {str(e)}")
        logger.info("モックデータを返します")
        return DUMMY_USERS

# 特定ユーザー情報取得API
@app.get("/users/{user_id}")
def get_user(user_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, company_name FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            return user
        raise HTTPException(status_code=404, detail="User not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ユーザー取得エラー: {str(e)}")
        logger.info("モックデータを返します")
        # モックデータから検索
        for user in DUMMY_USERS:
            if user["id"] == user_id:
                return user
        raise HTTPException(status_code=404, detail="User not found")

# ユーザーの残高取得API
@app.get("/users/{user_id}/balance")
def get_user_balance(user_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id, current_points, expiring_points FROM point_balances WHERE user_id = %s", (user_id,))
        balance = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if balance:
            return balance
        raise HTTPException(status_code=404, detail="Balance not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ポイント残高取得エラー: {str(e)}")
        logger.info("モックデータを返します")
        # モックデータから検索
        for balance in DUMMY_BALANCES:
            if balance["user_id"] == user_id:
                return balance
        raise HTTPException(status_code=404, detail="Balance not found")

# ユーザーのポイント履歴取得API
@app.get("/users/{user_id}/point-history")
def get_point_history(user_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, user_id, date, description, points FROM point_history WHERE user_id = %s", (user_id,))
        history = cursor.fetchall()
        cursor.close()
        conn.close()
        return history
    except Exception as e:
        logger.error(f"ポイント履歴取得エラー: {str(e)}")
        logger.info("モックデータを返します")
        # モックデータから検索
        user_history = []
        for history in DUMMY_HISTORY:
            if history["user_id"] == user_id:
                user_history.append(history)
        return user_history

# アイテム一覧取得API
@app.get("/redeemable-items")
def get_redeemable_items():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, points_required FROM redeemable_items")
        items = cursor.fetchall()
        cursor.close()
        conn.close()
        return items
    except Exception as e:
        logger.error(f"アイテム取得エラー: {str(e)}")
        logger.info("モックデータを返します")
        return DUMMY_ITEMS

# ==============================
# 🎯 FastAPI の起動コマンド
# ==============================
# uvicorn main:app --reload