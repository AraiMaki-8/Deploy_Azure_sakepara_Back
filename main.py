import os
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, TIMESTAMP, desc, Text
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, Session
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Optional
from pydantic import BaseModel
import sys
import traceback

# ==============================
# 🎯 .env ファイルの読み込み
# ==============================
load_dotenv()

# 環境変数の取得 - デフォルト値を設定
MYSQL_USER = os.getenv("MYSQL_USER", "sakeparadb")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "lzxVB3hCBTDi")
MYSQL_HOST = os.getenv("MYSQL_HOST", "tech0-gen-8-step4-sakepara-db.mysql.database.azure.com")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "point_program_db")
MYSQL_SSL_CA = os.getenv("MYSQL_SSL_CA", "DigiCertGlobalRootCA.crt.pem")
SSL_MODE = os.getenv("SSL_MODE", "preferred")  # preferred, required, disabled

# ポート番号を整数に変換
try:
    MYSQL_PORT = int(MYSQL_PORT)
except (ValueError, TypeError):
    MYSQL_PORT = 3306  # 変換できない場合はデフォルト値を使用

# 環境変数の読み込み状況（デバッグ用）
print("✅ 環境変数の確認:")
print(f"MYSQL_USER: {MYSQL_USER}")
print(f"MYSQL_HOST: {MYSQL_HOST}")
print(f"MYSQL_PORT: {MYSQL_PORT}")
print(f"MYSQL_DATABASE: {MYSQL_DATABASE}")
print(f"MYSQL_SSL_CA: {MYSQL_SSL_CA}")
print(f"SSL_MODE: {SSL_MODE}")

# カレントディレクトリの確認
current_dir = os.getcwd()
print(f"現在の作業ディレクトリ: {current_dir}")

# ファイルの存在確認
ssl_ca_path = os.path.join(current_dir, MYSQL_SSL_CA)
ssl_ca_exists = os.path.isfile(ssl_ca_path)
print(f"SSL証明書ファイル({ssl_ca_path})の存在: {ssl_ca_exists}")

# ==============================
# 🎯 リクエスト/レスポンスのモデル
# ==============================
class UserResponse(BaseModel):
    id: int
    name: str
    company_name: str

# 期間限定ポイントを削除したバランスレスポンス
class BalanceResponse(BaseModel):
    user_id: int
    current_points: int
    # scheduled_points 削除
    expiring_points: int

class PointHistoryResponse(BaseModel):
    id: int
    date: datetime
    description: str
    points: int
    remarks: Optional[str] = None

class RedeemableItemResponse(BaseModel):
    id: int
    name: str
    points_required: int

class UsePointsRequest(BaseModel):
    user_id: int
    item_id: int
    points: int

# ==============================
# 🎯 MySQL の接続設定
# ==============================
db_connection_error = None
try:
    # SSL設定を環境に応じて調整
    connect_args = {}
    
    if SSL_MODE == "required":
        if ssl_ca_exists:
            # SSL証明書ファイルが存在する場合は使用
            print(f"✅ SSL証明書ファイルを使用: {ssl_ca_path}")
            connect_args = {"ssl": {"ca": ssl_ca_path}}
            DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
        else:
            # SSL証明書ファイルが存在しない場合は警告
            print(f"⚠️ SSL証明書ファイルが見つかりません: {ssl_ca_path}")
            # SSL接続なしで試行
            DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    elif SSL_MODE == "disabled":
        # SSL無効モード
        print("⚠️ SSLは無効に設定されています。本番環境では推奨されません。")
        DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    else:
        # デフォルト（preferred）- connect_argsを使用するため、URLにはSSLパラメータを含めない
        print("✅ SSL設定: preferred（利用可能な場合はSSLを使用）")
        # 証明書ファイルが存在する場合のみ追加
        if ssl_ca_exists:
            connect_args = {"ssl": {"ca": ssl_ca_path}}
        DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    
    print(f"✅ データベース接続URL（パスワードなし）: {DATABASE_URL.replace(MYSQL_PASSWORD, '***')}")
    print(f"✅ 使用するconnect_args: {connect_args}")
    
    # 明示的にconnect_argsを指定
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    
    # 試験的に接続してみる
    with engine.connect() as connection:
        print("✅ データベース接続テスト成功!")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    db_connection_error = str(e)
    print(f"❌ データベース接続エラー: {str(e)}")
    print(f"❌ エラーの種類: {type(e).__name__}")
    
    # エラーが発生した場合でもアプリケーションを続行できるようにする
    DATABASE_URL = "sqlite:///:memory:"  # メモリ内SQLiteを使用
    print(f"⚠️ フォールバック: SQLiteメモリデータベースを使用します")
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ==============================
# 🎯 データモデル (SQLAlchemy)
# ==============================

class User(Base):
    """ ユーザー情報を管理するテーブル """
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)

class UserBalance(Base):
    """ ユーザーのポイント残高を管理するテーブル """
    __tablename__ = "user_balance"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    current_points = Column(Integer, default=0)
    scheduled_points = Column(Integer, default=0)  # DBには残すが、APIレスポンスには含めない
    expiring_points = Column(Integer, default=0)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

class PointHistory(Base):
    """ ユーザーのポイント履歴を管理するテーブル """
    __tablename__ = "point_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(TIMESTAMP, default=datetime.utcnow)
    description = Column(String(255), nullable=False)
    points = Column(Integer, nullable=False)
    remarks = Column(Text, nullable=True)  # 追加：備考欄

class RedeemableItem(Base):
    """ 交換可能なアイテムを管理するテーブル """
    __tablename__ = "redeemable_items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    points_required = Column(Integer, nullable=False)

class RedemptionHistory(Base):
    """ ユーザーのポイント交換履歴を管理するテーブル """
    __tablename__ = "redemption_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("redeemable_items.id"), nullable=False)
    date = Column(TIMESTAMP, default=datetime.utcnow)
    points_spent = Column(Integer, nullable=False)


# ==============================
# 🎯 FastAPI の設定
# ==============================
app = FastAPI()

# CORS設定（フロントエンドとの通信を許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データベーステーブルの作成
try:
    Base.metadata.create_all(bind=engine)
    print("✅ データベーステーブルの作成または確認が完了しました")
except Exception as e:
    print(f"❌ データベーステーブル作成エラー: {str(e)}")

# 🎯 ルートエンドポイント
@app.get("/")
def read_root():
    db_status = "正常" if db_connection_error is None else "エラー"
    return {
        "message": "Welcome to the Point Management System API!",
        "database_status": db_status,
        "database_error": db_connection_error
    }

# データベース接続テスト用エンドポイント
@app.get("/test-db-connection")
def test_db_connection():
    try:
        # 実際にデータベースに接続してみる
        conn = engine.connect()
        # 簡単なSQLクエリを実行してみる
        result = conn.execute("SELECT 1").fetchone()
        conn.close()
        
        # カレントディレクトリの内容を確認
        try:
            dir_contents = os.listdir(os.getcwd())
        except Exception as e:
            dir_contents = f"ディレクトリ内容取得エラー: {str(e)}"
        
        return {
            "status": "success",
            "message": "データベース接続に成功しました",
            "sql_result": result[0] if result else None,
            "database_url": DATABASE_URL.replace(MYSQL_PASSWORD, "***"),
            "database_config": {
                "user": MYSQL_USER,
                "host": MYSQL_HOST,
                "port": MYSQL_PORT,
                "database": MYSQL_DATABASE,
                "ssl_ca": MYSQL_SSL_CA,
                "ssl_ca_exists": os.path.isfile(os.path.join(os.getcwd(), MYSQL_SSL_CA)),
                "ssl_mode": SSL_MODE,
                # パスワードはセキュリティ上の理由で含めない
            },
            "environment": {
                "current_dir": os.getcwd(),
                "dir_contents": dir_contents,
                "python_version": sys.version,
                "platform": sys.platform
            }
        }
    except Exception as e:
        # エラーの詳細情報を収集
        error_info = {
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc()
        }
        
        # カレントディレクトリの内容を確認
        try:
            dir_contents = os.listdir(os.getcwd())
        except Exception as dir_e:
            dir_contents = f"ディレクトリ内容取得エラー: {str(dir_e)}"
        
        return {
            "status": "error",
            "message": f"データベース接続エラー: {str(e)}",
            "error_details": error_info,
            "database_config": {
                "user": MYSQL_USER,
                "host": MYSQL_HOST,
                "port": MYSQL_PORT,
                "database": MYSQL_DATABASE,
                "ssl_ca": MYSQL_SSL_CA,
                "ssl_ca_exists": os.path.isfile(os.path.join(os.getcwd(), MYSQL_SSL_CA)),
                "ssl_mode": SSL_MODE,
                # パスワードはセキュリティ上の理由で含めない
            },
            "environment": {
                "current_dir": os.getcwd(),
                "dir_contents": dir_contents,
                "python_version": sys.version,
                "platform": sys.platform
            }
        }

# ==============================
# 🎯 DBセッション取得関数
# ==============================
def get_db():
    """ データベースセッションを取得する関数 """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==============================
# 🎯 API: ユーザー情報取得
# ==============================
@app.get("/users", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db)):
    """ ユーザーの一覧を取得する """
    users = db.query(User).all()
    return users

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """ 指定ユーザーの情報を取得する """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# ==============================
# 🎯 API: ユーザーのポイント残高取得
# ==============================
@app.get("/users/{user_id}/balance", response_model=BalanceResponse)
def get_user_balance(user_id: int, db: Session = Depends(get_db)):
    """ 指定ユーザーの現在のポイント、失効予定ポイントを取得（期間限定ポイント削除） """
    balance = db.query(UserBalance).filter(UserBalance.user_id == user_id).first()
    if not balance:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user_id,
        "current_points": balance.current_points,
        # "scheduled_points": balance.scheduled_points,  # 削除
        "expiring_points": balance.expiring_points,
    }

# ==============================
# 🎯 API: ユーザーのポイント履歴取得
# ==============================
# 既存のエンドポイントを残す
@app.get("/users/{user_id}/points/history", response_model=List[dict])
def get_point_history_legacy(user_id: int, db: Session = Depends(get_db)):
    """ 指定ユーザーのポイント履歴を取得する（レガシーエンドポイント） """
    history = db.query(PointHistory).filter(PointHistory.user_id == user_id).all()
    return [
        {"date": h.date, "description": h.description, "points": h.points}
        for h in history
    ]

@app.get("/users/{user_id}/point-history", response_model=List[PointHistoryResponse])
def get_point_history(
    user_id: int, 
    limit: Optional[int] = Query(5, description="取得する履歴の最大数"),
    filter_type: Optional[str] = Query(None, description="履歴タイプ（all, earned, used）"),
    db: Session = Depends(get_db)
):
    """ 指定ユーザーのポイント履歴を取得する（フィルタリング機能付き） """
    query = db.query(PointHistory).filter(PointHistory.user_id == user_id)
    
    # フィルタリング条件
    if filter_type == "earned":
        query = query.filter(PointHistory.points > 0)
    elif filter_type == "used":
        query = query.filter(PointHistory.points < 0)
    
    # 日付の新しい順に取得
    query = query.order_by(desc(PointHistory.date))
    
    # 件数制限
    if limit:
        query = query.limit(limit)
    
    history = query.all()
    return history

# ==============================
# 🎯 API: 交換可能アイテム一覧取得
# ==============================
@app.get("/redeemable-items", response_model=List[RedeemableItemResponse])
def get_redeemable_items(db: Session = Depends(get_db)):
    """ 交換可能なアイテム一覧を取得する """
    items = db.query(RedeemableItem).all()
    return items

# ==============================
# 🎯 API: ポイント交換処理
# ==============================
# 既存のエンドポイントを残す
@app.post("/users/{user_id}/redeem/{item_id}")
def redeem_points_legacy(user_id: int, item_id: int, db: Session = Depends(get_db)):
    """ ユーザーがポイントを使ってアイテムを交換する処理（レガシーエンドポイント） """
    
    # 交換可能なアイテムを取得
    item = db.query(RedeemableItem).filter(RedeemableItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # ユーザーの残高を取得
    balance = db.query(UserBalance).filter(UserBalance.user_id == user_id).first()
    if not balance:
        raise HTTPException(status_code=404, detail="User not found")

    # 必要なポイントが足りるか確認
    if balance.current_points < item.points_required:
        raise HTTPException(status_code=400, detail="Not enough points")

    # ポイントを減算
    balance.current_points -= item.points_required

    # 交換履歴を追加
    redemption = RedemptionHistory(user_id=user_id, item_id=item_id, points_spent=item.points_required)
    db.add(redemption)

    # ポイント履歴を追加
    history = PointHistory(
        user_id=user_id, 
        description=f"{item.name}と交換", 
        points=-item.points_required
    )
    db.add(history)

    # 変更をデータベースに保存
    db.commit()

    return {"message": "ポイント交換が完了しました", "new_balance": balance.current_points}

@app.post("/use-points")
def use_points(request: UsePointsRequest, db: Session = Depends(get_db)):
    """ ユーザーがポイントを使ってアイテムと交換する処理 """
    
    # 交換可能なアイテムを取得
    item = db.query(RedeemableItem).filter(RedeemableItem.id == request.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # ユーザーの残高を取得
    balance = db.query(UserBalance).filter(UserBalance.user_id == request.user_id).first()
    if not balance:
        raise HTTPException(status_code=404, detail="User not found")

    # 必要なポイントが足りるか確認
    if balance.current_points < request.points:
        raise HTTPException(status_code=400, detail="Not enough points")

    # ポイントを減算
    balance.current_points -= request.points

    # 交換履歴を追加
    redemption = RedemptionHistory(
        user_id=request.user_id, 
        item_id=request.item_id, 
        points_spent=request.points
    )
    db.add(redemption)

    # ポイント履歴を追加
    history = PointHistory(
        user_id=request.user_id, 
        date=datetime.now(),
        description=f"{item.name}と交換", 
        points=-request.points,
        remarks=f"アイテム交換: {item.name}"
    )
    db.add(history)

    # 変更をデータベースに保存
    db.commit()

    return {
        "success": True,
        "message": "ポイント交換が完了しました", 
        "remaining_points": balance.current_points
    }

# ==============================
# 🎯 FastAPI の起動コマンド
# ==============================
# uvicorn main:app --reload