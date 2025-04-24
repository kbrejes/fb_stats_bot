#!/usr/bin/env python3
"""
Script to print the current database structure.
Connects to the database using SQLAlchemy engine and inspects table definitions.
"""

from sqlalchemy import inspect
from src.storage.database import engine


def print_db_structure():
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    if not table_names:
        print("No tables found in the database.")
        return
    
    for table in table_names:
        print(f"Table: {table}")
        columns = inspector.get_columns(table)
        for column in columns:
            col_name = column.get("name")
            col_type = column.get("type")
            nullable = column.get("nullable")
            default = column.get("default")
            print(f" - {col_name}: {col_type}, nullable={nullable}, default={default}")
        print()  


if __name__ == "__main__":
    print_db_structure() 