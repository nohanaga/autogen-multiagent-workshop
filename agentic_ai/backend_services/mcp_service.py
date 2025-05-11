import os
import asyncio
import asyncpg
import json
from typing import List, Optional, Dict, Any
import datetime
from dotenv import load_dotenv
from datetime import date
import uuid
from pymongo import MongoClient
import re

# Load environment variables from .env file.
load_dotenv()

DB_CONFIG = {
    "user": os.getenv("PGUSER", "your_user"),
    "password": os.getenv("PGPASSWORD", "your_password"),
    "database": os.getenv("PGDATABASE", "your_database"),
    "host": os.getenv("PGHOST", "your_host"),
    "port": int(os.getenv("PGPORT", 5432)),
}

# ────────────────────────── FastMCP INITIALISATION ──────────────────────
from fastmcp import FastMCP
mcp = FastMCP(
    name="Game Shop API as Tools",
    instructions="All product, order, and inventory data is accessible ONLY via the declared tools below. Return values are JSON strings. Always call the most specific tool that answers the user's question."
)

# ────────────────────────────── DB Connection ───────────────────────────
async def get_conn():
    return await asyncpg.connect(**DB_CONFIG)

# 共通のJSON変換ヘルパー
def to_json(data):
    """データを安全にJSONに変換するヘルパー関数"""
    try:
        # datetimeなどを文字列化するためにdefault=strを使用
        return json.dumps(data, ensure_ascii=False, default=str)
    except Exception as e:
        print(f"JSON変換エラー: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)

##############################################################################
#                               TOOL ENDPOINTS                               #
##############################################################################

@mcp.tool(description="List all product categories")
async def get_all_categories() -> dict:
    """
    List all product categories
    """
    conn = await get_conn()
    print("Fetching all categories")
    try:
        rows = await conn.fetch("SELECT * FROM categories LIMIT 10")
        return to_json([dict(r) for r in rows])
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        await conn.close()

@mcp.tool(description="List all products (optionally filter by category)")
async def get_products(category_id: Optional[int] = None) -> str:
    """
    List all products (optionally filter by category)
    """
    conn = await get_conn()
    try:
        if category_id:
            rows = await conn.fetch("SELECT * FROM products WHERE category_id = $1 LIMIT 10", category_id)
        else:
            rows = await conn.fetch("SELECT * FROM products LIMIT 10")
        return to_json([dict(r) for r in rows])
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        await conn.close()

@mcp.tool(description="Get product detail by product_id")
async def get_product_detail(product_id: int) -> str:
    """
    Get product detail by product_id
    """
    conn = await get_conn()
    try:
        # 単一レコード取得なのでLIMITは必要ないが、安全のために追加
        row = await conn.fetchrow("SELECT * FROM products WHERE product_id = $1 LIMIT 1", product_id)
        if not row:
            return json.dumps({"error": "Product not found"}, ensure_ascii=False)
        return to_json(dict(row))
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        await conn.close()

@mcp.tool(description="List all game products")
async def get_game_products() -> str:
    """
    List all game products
    """
    conn = await get_conn()
    try:
        rows = await conn.fetch("SELECT * FROM game_products LIMIT 10")
        return to_json([dict(r) for r in rows])
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        await conn.close()

@mcp.tool(description="Get inventory status for a product")
async def get_inventory_status(product_id: str) -> str:
    """
    Get inventory status for a product
    """
    conn = await get_conn()
    try:
        row = await conn.fetchrow("SELECT * FROM inventory WHERE product_id = $1 LIMIT 1", product_id)
        if not row:
            return json.dumps({"error": "Inventory not found"}, ensure_ascii=False)
        return to_json(dict(row))
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        await conn.close()

@mcp.tool(description="List all orders for a customer")
async def get_customer_orders(customer_id: str) -> str:
    """
    List all orders for a customer
    """
    conn = await get_conn()
    try:
        rows = await conn.fetch("SELECT * FROM orders WHERE customer_id = $1 ORDER BY order_date DESC LIMIT 10", customer_id)
        return to_json([dict(r) for r in rows])
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        await conn.close()

@mcp.tool(description="Get order details for an order")
async def get_order_details(order_id: int) -> str:
    """
    Get order details for an order
    """
    conn = await get_conn()
    try:
        rows = await conn.fetch("SELECT * FROM order_details WHERE order_id = $1 LIMIT 10", order_id)
        return to_json([dict(r) for r in rows])
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        await conn.close()

@mcp.tool(description="Get shipping status for a user's order")
async def get_shipping_status(user_id: int) -> str:
    """
    Get shipping status for a user's order
    """
    conn = await get_conn()
    print("Fetching shipping status for user_id:", user_id)
    try:
        # すでにLIMIT 1が指定されているのでそのまま
        row = await conn.fetchrow("""
            SELECT 
                s.order_id,
                s.user_id,
                s.product_id,
                s.order_date,
                s.shipping_status,
                s.shipping_date,
                s.delivery_date
            FROM 
                shipping_status s
            WHERE 
                s.user_id = $1
            ORDER BY s.order_date DESC LIMIT 1
        """, user_id)
        print(row)
        if not row:
            return json.dumps({})
        return to_json(dict(row))
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        await conn.close()

@mcp.tool(description="List all users")
async def get_all_users() -> str:
    """
    List all users
    """
    conn = await get_conn()
    try:
        rows = await conn.fetch("SELECT * FROM users LIMIT 10")
        return to_json([dict(r) for r in rows])
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        await conn.close()

@mcp.tool(description="指定期間の売上合計を取得する")
async def get_total_sales(start_date: str, end_date: str) -> str:
    """
    start_date から end_date までの orders.total_amount 合計を返します。
    日付文字列は 'YYYY-MM-DD' 形式としてください。
    """
    # 文字列を date オブジェクトに変換
    try:
        start: date = date.fromisoformat(start_date)
        end: date = date.fromisoformat(end_date)
    except ValueError as e:
        return json.dumps({"error": f"日付形式エラー: {e}"}, ensure_ascii=False)

    conn = await get_conn()
    try:
        rows = await conn.fetch(
            """
            SELECT
                COALESCE(SUM(total_amount), 0) AS total_amount
            FROM public.orders
            WHERE order_date BETWEEN $1 AND $2
            """,
            start,
            end
        )
        # rows は [{"total_amount": 数値}] のリストになるはずなので、
        # 最初の要素だけ返す場合は rows[0] を使ってもOKです。
        return to_json([dict(r) for r in rows])
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        await conn.close()
        

@mcp.tool(description="指定期間の日別受注数を取得する")
async def get_daily_order_counts(start_date: str, end_date: str) -> str:
    """
    start_date から end_date までの期間について、
    orders テーブルの order_date ごとに日別受注数を集計し返します。
    日付文字列は 'YYYY-MM-DD' 形式で指定してください。
    """
    # 文字列を date オブジェクトに変換
    try:
        start: date = date.fromisoformat(start_date)
        end:   date = date.fromisoformat(end_date)
    except ValueError as e:
        return json.dumps({"error": f"日付形式エラー: {e}"}, ensure_ascii=False)

    conn = await get_conn()
    try:
        rows = await conn.fetch(
            """
            SELECT
                DATE(order_date) AS order_date,
                COUNT(*)        AS order_count
            FROM public.orders
            WHERE order_date BETWEEN $1 AND $2
            GROUP BY DATE(order_date)
            ORDER BY DATE(order_date)
            """,
            start,
            end
        )
        return to_json([dict(r) for r in rows])
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        await conn.close()

@mcp.tool(description="日別のツイート数を取得する")
async def get_daily_tweet_counts() -> str:
    """
    CosmosDBのMongoDBインターフェースを使用して、日付ごとのツイート数を集計して返します。
    結果は日付順にソートされます。
    """
    try:
        # MongoDB クライアントの設定
        conn_str = os.getenv("MONGODB_CONNECTION_STRING")
        db_name = os.getenv("MONGODB_DB_NAME", "Twitter")
        coll_name = os.getenv("MONGODB_COLLECTION_NAME", "tweets")
        client = MongoClient(conn_str)
        coll = client[db_name][coll_name]

        # 日別ドキュメント数をカウントするための集約パイプライン
        pipeline = [
            {
                '$group': {
                    '_id': {
                        '$dateToString': {
                            'format': '%Y-%m-%d',  # 日付形式を指定
                            'date': '$created_at'  # created_at フィールドを使用
                        }
                    },
                    'count': {'$sum': 1}  # ドキュメント数をカウント
                }
            },
            {
                '$sort': {'_id': 1}  # 日付でソート
            }
        ]

        # 集約パイプラインを実行
        daily_counts = coll.aggregate(pipeline)
        
        # 結果をリストに変換
        results = []
        for daily_count in daily_counts:
            results.append({
                "date": daily_count['_id'],
                "count": daily_count['count']
            })
            
        return to_json(results)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        if 'client' in locals():
            client.close()

# --- 1. ユーザーごとの投稿数上位を取得 ---
@mcp.tool(description="ユーザー別のツイート数上位を取得する")
async def get_top_users_by_tweet_count(limit: int = 10) -> str:
    """
    日別ではなく、ユーザー（screen_name）ごとのツイート数を集計し、
    投稿数の多い順に上位 limit 件を返します。
    """
    try:
        conn_str = os.getenv("MONGODB_CONNECTION_STRING")
        db_name = os.getenv("MONGODB_DB_NAME", "Twitter")
        coll_name = os.getenv("MONGODB_COLLECTION_NAME", "tweets")
        client = MongoClient(conn_str)
        coll = client[db_name][coll_name]
        pipeline = [
            {"$group": {"_id": "$user.screen_name", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]
        agg = coll.aggregate(pipeline)
        results = [{"user": doc["_id"], "tweet_count": doc["count"]} for doc in agg]
        return to_json(results)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.close()


# --- 2. ハッシュタグ別の出現頻度上位を取得 ---
@mcp.tool(description="ハッシュタグの出現頻度上位を取得する")
async def get_top_hashtags(limit: int = 10) -> str:
    """
    text フィールドから正規表現でハッシュタグを抽出し、
    各ハッシュタグごとの出現数を集計、上位 limit 件を返します。
    """
    try:
        conn_str = os.getenv("MONGODB_CONNECTION_STRING")
        db_name = os.getenv("MONGODB_DB_NAME", "Twitter")
        coll_name = os.getenv("MONGODB_COLLECTION_NAME", "tweets")
        client = MongoClient(conn_str)
        coll = client[db_name][coll_name]
        pipeline = [
            {"$project": {"tags": {"$regexFindAll": {"input": "$text", "regex": r"#\w+"}}}},
            {"$unwind": "$tags"},
            {"$group": {"_id": "$tags.match", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]
        agg = coll.aggregate(pipeline)
        results = [{"hashtag": doc["_id"], "count": doc["count"]} for doc in agg]
        return to_json(results)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.close()


# --- 3. 言語（lang）ごとのツイート分布を取得 ---
@mcp.tool(description="言語ごとのツイート数を集計する")
async def get_language_distribution() -> str:
    """
    lang フィールドを基に、ツイートの言語分布を集計し、割合も算出して返します。
    """
    try:
        conn_str = os.getenv("MONGODB_CONNECTION_STRING")
        db_name = os.getenv("MONGODB_DB_NAME", "Twitter")
        coll_name = os.getenv("MONGODB_COLLECTION_NAME", "tweets")
        client = MongoClient(conn_str)
        coll = client[db_name][coll_name]
        total = coll.count_documents({})
        pipeline = [
            {"$group": {"_id": "$lang", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        agg = coll.aggregate(pipeline)
        results = []
        for doc in agg:
            results.append({
                "lang": doc["_id"],
                "count": doc["count"],
                "ratio": round(doc["count"] / total, 4)
            })
        return to_json(results)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.close()


# --- 4. 時間帯（時間単位）ごとのツイート数を取得 ---
@mcp.tool(description="時間帯別のツイート数を取得する")
async def get_hourly_tweet_distribution() -> str:
    """
    created_at を時間粒度（0～23 時）で集計し、
    どの時間帯に投稿が多いかを可視化できるように返します。
    """
    try:
        conn_str = os.getenv("MONGODB_CONNECTION_STRING")
        db_name = os.getenv("MONGODB_DB_NAME", "Twitter")
        coll_name = os.getenv("MONGODB_COLLECTION_NAME", "tweets")
        client = MongoClient(conn_str)
        coll = client[db_name][coll_name]
        pipeline = [
            {
                "$group": {
                    "_id": {"$hour": "$created_at"},
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        agg = coll.aggregate(pipeline)
        results = [{"hour": doc["_id"], "count": doc["count"]} for doc in agg]
        return to_json(results)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.close()


# --- 5. 日別平均エンゲージメントを取得 ---
@mcp.tool(description="日別の平均いいね・リプライ・リツイート数を取得する")
async def get_daily_average_engagement() -> str:
    """
    favorite_count, reply_count, retweet_count, quote_count の平均を
    日ごとに算出して返します。
    """
    try:
        conn_str = os.getenv("MONGODB_CONNECTION_STRING")
        db_name = os.getenv("MONGODB_DB_NAME", "Twitter")
        coll_name = os.getenv("MONGODB_COLLECTION_NAME", "tweets")
        client = MongoClient(conn_str)
        coll = client[db_name][coll_name]
        pipeline = [
            {
                "$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "avg_favorite": {"$avg": "$favorite_count"},
                    "avg_reply": {"$avg": "$reply_count"},
                    "avg_retweet": {"$avg": "$retweet_count"},
                    "avg_quote": {"$avg": "$quote_count"}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        agg = coll.aggregate(pipeline)
        results = []
        for doc in agg:
            results.append({
                "date": doc["_id"],
                "avg_favorite": round(doc["avg_favorite"], 2),
                "avg_reply": round(doc["avg_reply"], 2),
                "avg_retweet": round(doc["avg_retweet"], 2),
                "avg_quote": round(doc["avg_quote"], 2)
            })
        return to_json(results)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.close()


# --- 6. プロダクト別の言及回数を取得 ---
@mcp.tool(description="product_name 別のツイート数を集計する")
async def get_product_mentions_count() -> str:
    """
    product_name フィールドを基に、各プロダクトの言及回数を
    多い順に集計して返します。
    """
    try:
        conn_str = os.getenv("MONGODB_CONNECTION_STRING")
        db_name = os.getenv("MONGODB_DB_NAME", "Twitter")
        coll_name = os.getenv("MONGODB_COLLECTION_NAME", "tweets")
        client = MongoClient(conn_str)
        coll = client[db_name][coll_name]
        pipeline = [
            {"$group": {"_id": "$product_name", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        agg = coll.aggregate(pipeline)
        results = [{"product_name": doc["_id"], "count": doc["count"]} for doc in agg]
        return to_json(results)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.close()


@mcp.tool(description="特定のハッシュタグを含むツイートを検索する")
async def search_tweets_by_hashtag(hashtag: str, limit: int = 100) -> str:
    """
    指定されたハッシュタグを含むツイートを MongoDB から検索し、
    Python 側で日付順ソートして最新の limit 件を返します。
    """
    try:
        conn_str = os.getenv("MONGODB_CONNECTION_STRING")
        db_name = os.getenv("MONGODB_DB_NAME", "Twitter")
        coll_name = os.getenv("MONGODB_COLLECTION_NAME", "tweets")
        client = MongoClient(conn_str)
        coll = client[db_name][coll_name]

        regex = re.compile(rf"#{re.escape(hashtag)}", re.IGNORECASE)
        # まずはマッチするドキュメントを取得（必要に応じてフィルタを追加できます）
        cursor = coll.find({"text": {"$regex": regex}})
        docs = list(cursor)

        # Python 側で created_at をキーにソート（降順）
        docs.sort(
            key=lambda d: d.get("created_at", datetime.datetime.min),
            reverse=True
        )

        # 上位 limit 件を結果化
        results = []
        for doc in docs[:limit]:
            results.append({
                "id": str(doc.get("_id")),
                "created_at": doc.get("created_at"),
                "user": doc.get("user", {}).get("screen_name"),
                "text": doc.get("text"),
                "favorite_count": doc.get("favorite_count", 0),
                "retweet_count": doc.get("retweet_count", 0),
                "reply_count": doc.get("reply_count", 0),
                "quote_count": doc.get("quote_count", 0),
            })

        return to_json(results)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.close()
##############################################################################
#                                RUN SERVER                                  #
##############################################################################

if __name__ == "__main__":
    # デバッグ用
    # asyncio.run(get_shipping_status(123))
    asyncio.run(mcp.run_sse_async(host="0.0.0.0", port=8000))