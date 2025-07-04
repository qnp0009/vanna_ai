import os
import sqlite3
import pandas as pd
from urllib.parse import urlparse
import psycopg2
from psycopg2.extras import RealDictCursor
import re

class DatabaseAdapter:
    """
    Database adapter that supports both SQLite and PostgreSQL connections.
    Provides a unified interface for different database types.
    """
    
    def __init__(self):
        self.connection = None
        self.db_type = None
        self.connection_string = None
        
    def connect(self, connection_string: str):
        """
        Connect to database using connection string.
        
        Args:
            connection_string: 
                - SQLite: "sqlite:///path/to/file.db" or "sqlite:///C:/path/to/file.db"
                - PostgreSQL: "postgresql://user:password@host:port/database"
        """
        self.connection_string = connection_string
        
        if connection_string.startswith("sqlite:///"):
            self._connect_sqlite(connection_string)
        elif connection_string.startswith("postgresql://"):
            self._connect_postgresql(connection_string)
        else:
            raise ValueError(f"Unsupported database type. Use 'sqlite:///' or 'postgresql://' prefix.")
    
    def _connect_sqlite(self, connection_string: str):
        """Connect to SQLite database"""
        try:
            # Extract file path from connection string
            # sqlite:///path/to/file.db -> path/to/file.db
            file_path = connection_string.replace("sqlite:///", "")
            
            # Handle Windows paths
            if file_path.startswith("/"):
                file_path = file_path[1:]
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            self.connection = sqlite3.connect(file_path, check_same_thread=False)
            self.db_type = "sqlite"
            print(f"✅ Connected to SQLite database: {file_path}")
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect to SQLite database: {e}")
    
    def _connect_postgresql(self, connection_string: str):
        """Connect to PostgreSQL database"""
        try:
            self.connection = psycopg2.connect(connection_string)
            self.db_type = "postgresql"
            print(f"✅ Connected to PostgreSQL database")
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect to PostgreSQL database: {e}")
    
    def execute_query(self, sql: str) -> pd.DataFrame:
        """
        Execute SQL query and return results as pandas DataFrame
        
        Args:
            sql: SQL query to execute
            
        Returns:
            pandas.DataFrame: Query results
        """
        if not self.connection:
            raise ValueError("No database connection. Call connect() first.")
        
        try:
            if self.db_type == "sqlite":
                return pd.read_sql_query(sql, self.connection)
            elif self.db_type == "postgresql":
                return pd.read_sql_query(sql, self.connection)
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")
                
        except Exception as e:
            print(f"Error executing SQL: {e}")
            return pd.DataFrame()
    
    def get_tables(self) -> list:
        """
        Get list of tables in the database
        
        Returns:
            list: List of table names
        """
        if not self.connection:
            raise ValueError("No database connection. Call connect() first.")
        
        try:
            if self.db_type == "sqlite":
                query = "SELECT name FROM sqlite_master WHERE type='table'"
            elif self.db_type == "postgresql":
                query = """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")
            
            df = self.execute_query(query)
            return df.iloc[:, 0].tolist() if not df.empty else []
            
        except Exception as e:
            print(f"Error getting tables: {e}")
            return []
    
    def get_table_schema(self, table_name: str) -> pd.DataFrame:
        """
        Get schema information for a specific table
        
        Args:
            table_name: Name of the table
            
        Returns:
            pandas.DataFrame: Schema information
        """
        if not self.connection:
            raise ValueError("No database connection. Call connect() first.")
        
        try:
            if self.db_type == "sqlite":
                query = f"PRAGMA table_info({table_name})"
            elif self.db_type == "postgresql":
                query = f"""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position
                """
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")
            
            return self.execute_query(query)
            
        except Exception as e:
            print(f"Error getting table schema: {e}")
            return pd.DataFrame()
    
    def test_connection(self) -> bool:
        """
        Test if the database connection is working
        
        Returns:
            bool: True if connection is working, False otherwise
        """
        if not self.connection:
            return False
        
        try:
            if self.db_type == "sqlite":
                # Simple query to test SQLite connection
                self.execute_query("SELECT 1")
            elif self.db_type == "postgresql":
                # Simple query to test PostgreSQL connection
                self.execute_query("SELECT 1")
            return True
            
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def close(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.db_type = None
            print("Database connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def parse_connection_string(connection_string: str) -> dict:
    """
    Parse connection string to extract database information
    
    Args:
        connection_string: Database connection string
        
    Returns:
        dict: Parsed connection information
    """
    if connection_string.startswith("sqlite:///"):
        file_path = connection_string.replace("sqlite:///", "")
        if file_path.startswith("/"):
            file_path = file_path[1:]
        return {
            "type": "sqlite",
            "file_path": file_path,
            "display_name": os.path.basename(file_path)
        }
    elif connection_string.startswith("postgresql://"):
        parsed = urlparse(connection_string)
        return {
            "type": "postgresql",
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "database": parsed.path[1:],  # Remove leading slash
            "username": parsed.username,
            "display_name": f"{parsed.username}@{parsed.hostname}:{parsed.port or 5432}/{parsed.path[1:]}"
        }
    else:
        raise ValueError("Unsupported connection string format")


def validate_connection_string(connection_string: str) -> bool:
    """
    Validate if connection string format is correct
    
    Args:
        connection_string: Database connection string
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        if connection_string.startswith("sqlite:///"):
            # Basic SQLite validation
            file_path = connection_string.replace("sqlite:///", "")
            if file_path.startswith("/"):
                file_path = file_path[1:]
            # Check if directory is writable
            dir_path = os.path.dirname(file_path)
            if dir_path and not os.access(dir_path, os.W_OK):
                return False
            return True
        elif connection_string.startswith("postgresql://"):
            # Basic PostgreSQL validation
            parsed = urlparse(connection_string)
            return all([parsed.hostname, parsed.username, parsed.path])
        else:
            return False
    except Exception:
        return False 