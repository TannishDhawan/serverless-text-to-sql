BLOCKED_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP",
    "ALTER", "CREATE", "TRUNCATE", "EXEC"
}

def validate_sql(sql: str):
    """
    Checks if the SQL is safe to run.
    Returns (is_safe, cleaned_sql_or_error)
    """
    sql = sql.strip()
    sql_upper = sql.upper()

    # Must start with SELECT
    if not sql_upper.startswith("SELECT"):
        return False, "Only SELECT queries are allowed."

    # Block dangerous keywords
    for keyword in BLOCKED_KEYWORDS:
        if keyword in sql_upper:
            return False, f"Blocked keyword detected: {keyword}"

    # Add LIMIT if missing
    if "LIMIT" not in sql_upper:
        sql = sql.rstrip(";") + " LIMIT 50;"

    return True, sql