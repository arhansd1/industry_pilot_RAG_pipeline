import json
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def fetch_rows():
    """
    Fetch rows from PostgreSQL and return as Python dictionaries.
    Does NOT modify or convert JSON. Only fetches raw DB data.
    """
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT")),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )

    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    query = """
        SELECT
            m.course_id AS course_id,
            r.module_id AS module_id,
            r.id AS resource_id,
            r.summary AS summary,
            r.chapters AS chapters
        FROM course.t_module m 
        JOIN course.t_resource r 
        ON m.id = r.module_id 
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows


def transform_rows(rows):
    """
    Process rows:
      - summary can be dict, stringified JSON, or None
      - extract only summary['content']
      - ensure everything stays as Python structures (NOT JSON)
      - skip rows where both summary and chapters are null/empty
    """

    transformed = []

    for row in rows:
        new_row = dict(row)

        summary = new_row.get("summary")
        chapters = new_row.get("chapters")

        # Parse summary if it's a string
        if isinstance(summary, str):
            try:
                summary = json.loads(summary)
            except Exception:
                summary = None

        # Extract summary content
        if isinstance(summary, dict) and "content" in summary:
            new_row["summary"] = summary["content"]
        else:
            new_row["summary"] = None

        # Parse chapters if it's a string
        if isinstance(chapters, str):
            try:
                chapters = json.loads(chapters)
            except Exception:
                chapters = None

        new_row["chapters"] = chapters

        # Skip if both summary and chapters are null/empty
        if not new_row["summary"] and not new_row["chapters"]:
            continue

        transformed.append(new_row)

    return transformed


def save_json(filename, data):
    """
    Convert Python data → JSON file
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"✓ Export complete! File saved as {filename}")


def export_to_json():
    """
    High-level function:
       1. Fetch raw rows
       2. Transform them
       3. Write to JSON file
    """

    try:
        print("Fetching data from PostgreSQL...")
        rows = fetch_rows()
        print(f"✓ Fetched {len(rows)} rows")

        print("Transforming data...")
        cleaned_rows = transform_rows(rows)
        print(f"✓ Transformed {len(cleaned_rows)} valid rows")

        save_json("course_data.json", cleaned_rows)

        return cleaned_rows

    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    export_to_json()