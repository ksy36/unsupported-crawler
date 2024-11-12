import psycopg2
from google.cloud import bigquery

def global_100k():
    client = bigquery.Client()
    query = """
        SELECT *
        FROM `cr-ux-366917.test.global_100k_jan_2024`
        ORDER BY rank ASC
    """

    query_job = client.query(query)
    results = query_job.result()
    rows_to_insert = [tuple(row.values()) for row in results]

    conn = psycopg2.connect("dbname='unsupported_crawl' user='uc_test'", port=5434)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS global_100k (
            id SERIAL PRIMARY KEY,
            origin TEXT,
            rank INTEGER,
            text TEXT DEFAULT '',
            screenshot_path TEXT DEFAULT '',
            is_crawled INTEGER DEFAULT 0,
            is_error INTEGER DEFAULT 0
        )
    """)
    conn.commit()

    insert_query = 'INSERT INTO global_100k (origin, rank) VALUES (%s, %s)'
    cursor.executemany(insert_query, rows_to_insert)

    conn.commit()
    cursor.close()
    conn.close()

def classification_results_global():
    conn = psycopg2.connect("dbname='unsupported_crawl' user='uc_test'", port=5434)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classification_results_global (
            id INTEGER PRIMARY KEY,
            is_unsupported INTEGER,
            message_chunk TEXT,
            confidence FLOAT,
            FOREIGN KEY (id) REFERENCES global_100k(id)
        );
    """)

    conn.commit()  # Commit the changes
    cursor.close()
    conn.close()

if __name__ == "__main__":
    global_100k()
    #classification_results_global()
