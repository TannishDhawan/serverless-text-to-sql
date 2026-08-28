import os
import sqlite3
import json
import cohere
from dotenv import load_dotenv
from sql_validator import validate_sql
from schema import SCHEMA

load_dotenv()

co = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))
DB_PATH = "ecommerce.db"

def text_to_sql(question: str) -> dict:
    print(f"\nQuestion: {question}")

    # Step 1 — Send schema + question to Cohere to generate SQL
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

    # Step 2 — Validate SQL is safe
    is_safe, result = validate_sql(sql)
    if not is_safe:
        return {"error": result}
    sql = result

    # Step 3 — Run SQL against SQLite database
    print("Running query...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(sql)
        rows = [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        return {"error": f"SQL execution failed: {str(e)}"}
    finally:
        conn.close()

    print(f"Got {len(rows)} rows back")

    # Step 4 — Send results to Cohere to format a plain English answer
    print("Formatting answer...")
    format_response = co.chat(
        model="command-r7b-12-2024",
        messages=[
            {
                "role": "user",
                "content": f"Question: {question}\n\nDatabase results: {json.dumps(rows[:10])}\n\nWrite a short clear answer in plain English based on these results."
            }
        ]
    )

    answer = format_response.message.content[0].text.strip()

    return {
        "question": question,
        "sql": sql,
        "row_count": len(rows),
        "results": rows[:10],
        "answer": answer
    }


# Test with sample questions
if __name__ == "__main__":
    questions = [
        "What are the top 5 products by revenue?",
        "Which city has the most customers?",
        "How many orders are pending?",
        "What is the total revenue in 2024?",
        "Which product category generates the most revenue?"
    ]

    for q in questions:
        result = text_to_sql(q)
        print("\n" + "="*60)
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Answer: {result['answer']}")
            print(f"SQL:    {result['sql']}")
        print("="*60)