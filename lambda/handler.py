import os
import re
import sqlite3
import json
import shutil
import cohere

BLOCKED_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP",
    "ALTER", "CREATE", "TRUNCATE", "EXEC"
}

SCHEMA = """
You have access to an e-commerce SQLite database with these tables:

customers(customer_id, customer_name, email, city, country, created_at)
products(product_id, product_name, category, price, stock_quantity)
orders(order_id, customer_id, order_date, status, total_amount)
order_items(item_id, order_id, product_id, quantity, unit_price)

Rules you MUST follow:
1. Only write SELECT statements. Never write INSERT, UPDATE, DELETE, DROP.
2. If the user specifies a number like top 5 or top 10 use that as the LIMIT.
3. If no number is specified use LIMIT 50.
4. Only use the tables listed above.
5. Return ONLY the raw SQL query.
6. No explanations. No markdown. No backticks. Just SQL.
"""

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type"
}

DANGEROUS_WORDS = {
    "drop", "delete", "insert", "update",
    "alter", "truncate", "exec", "create"
}

def validate_sql(sql: str):
    sql = sql.strip()
    sql_upper = sql.upper()

    if not sql_upper.startswith("SELECT"):
        return False, "Only SELECT queries are allowed."

    for keyword in BLOCKED_KEYWORDS:
        if keyword in sql_upper:
            return False, f"Blocked keyword detected: {keyword}"

    if "LIMIT" not in sql_upper:
        sql = sql.rstrip(";") + " LIMIT 50;"

    return True, sql

def handler(event, context):
    # Handle CORS preflight
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": ""
        }

    try:
        # 1. Parse question
        body = json.loads(event.get("body", "{}"))
        question = body.get("question", "").strip()

        if not question:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "No question provided"})
            }

        # 2. Block dangerous keywords — strips punctuation first
        question_words = set(re.findall(r"[a-zA-Z]+", question.lower()))
        if question_words & DANGEROUS_WORDS:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "That type of query is not allowed."})
            }

        print(f"Question: {question}")

        # 3. Copy SQLite DB to /tmp/
        db_source = os.path.join(os.path.dirname(__file__), "ecommerce.db")
        db_path = "/tmp/ecommerce.db"
        if not os.path.exists(db_path):
            shutil.copy(db_source, db_path)

        # 4. Setup Cohere
        co = cohere.ClientV2(api_key=os.environ.get("COHERE_API_KEY"))

        # 5. Generate SQL
        print("Generating SQL...")
        response = co.chat(
            model="command-r7b-12-2024",
            messages=[
                {
                    "role": "user",
                    "content": f"{SCHEMA}\n\nQuestion: {question}"
                }
            ]
        )

        sql = response.message.content[0].text.strip()
        print(f"Generated SQL: {sql}")

        # 6. Validate SQL
        is_safe, result = validate_sql(sql)
        if not is_safe:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": result})
            }
        sql = result

        # 7. Run SQL
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(sql)
            rows = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            return {
                "statusCode": 500,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": f"SQL execution failed: {str(e)}"})
            }
        finally:
            conn.close()

        print(f"Got {len(rows)} rows")

        # 8. Format answer
        print("Formatting answer...")
        format_response = co.chat(
            model="command-r7b-12-2024",
            messages=[
                {
                    "role": "user",
                    "content": f"""Question: {question}

Database results: {json.dumps(rows[:10])}

Format your answer like this:
- Use bullet points or numbered list
- Each item on its own line
- Include the actual numbers and values
- Keep it short and clear
- No paragraphs
- No intro sentence needed"""
                }
            ]
        )

        answer = format_response.message.content[0].text.strip()

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "question": question,
                "sql": sql,
                "row_count": len(rows),
                "results": rows[:10],
                "answer": answer
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": str(e)})
        }