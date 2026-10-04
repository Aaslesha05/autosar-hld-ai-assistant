"""
Audit script to semantically inspect extracted content from both HLD PDFs.
"""
import os
import json
import sqlite3

def run_audit():
    db_path = "data/autosar_hld.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, filename, version_tag, page_count, status FROM documents WHERE status = 'processed';")
    docs = cursor.fetchall()

    for doc in docs:
        print(f"\n=======================================================")
        print(f"DOCUMENT: {doc['filename']} ({doc['version_tag']})")
        print(f"ID: {doc['id']} | Status: {doc['status']} | Total Pages: {doc['page_count']}")
        print(f"=======================================================")

        cursor.execute("SELECT page_number, word_count, char_count, has_tables, is_ocr, headings_json, tables_json, cleaned_text FROM document_pages WHERE document_id = ? ORDER BY page_number ASC;", (doc["id"],))
        pages = cursor.fetchall()

        for page in pages:
            headings = json.loads(page["headings_json"])
            tables = json.loads(page["tables_json"])
            print(f"\n--- PAGE {page['page_number']} ---")
            print(f"Metrics: {page['word_count']} words, {page['char_count']} chars, OCR used: {bool(page['is_ocr'])}")
            print(f"Detected Headings ({len(headings)}): {headings[:3]} ...")
            if tables:
                print(f"Table Found ({len(tables)}): {tables[0]['row_count']} rows x {tables[0]['col_count']} cols")
                print(f"  Header: {tables[0]['rows'][0]}")
                print(f"  Sample Row 1: {tables[0]['rows'][1] if len(tables[0]['rows']) > 1 else 'None'}")
            print(f"Text Snippet:\n  {page['cleaned_text'][:200]}...")

    conn.close()

if __name__ == "__main__":
    run_audit()
