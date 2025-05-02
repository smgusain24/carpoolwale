import time

import psycopg2
from psycopg2 import pool
from typing import List, Dict, Any, Optional, Tuple, Union
from contextlib import contextmanager
from config.app_logger import logger


class PostgresDB:
    """
    PostgreSQL database connection and query execution utility class.
    """



    def __init__(self, config=None):
        _default_schema = "dev"
        self.config = config or {
            "dbname": "carpoolwale",
            "user": "postgres",
            "password": "admin1234567",
            "host": "localhost",
            "port": "5432"
        }
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=5,
                maxconn=20,
                **self.config
            )
            logger.info("PostgreSQL connection pool created successfully")
            conn = self.connection_pool.getconn()

            self._set_default_schema(conn, _default_schema)
            logger.info(f"Default schema set to {_default_schema}")

        except Exception as e:
            logger.error(f"Error creating PostgreSQL connection pool: {e}", exc_info=True)
            raise

    @staticmethod
    def _set_default_schema(conn, _default_schema):
        """
        Set the default schema to use for all database operations.

        Args:
            conn
        """
        with conn.cursor() as schema_cursor:
            schema_cursor.execute(f"SET search_path TO {_default_schema}, public;")

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections
        """
        conn = None
        try:


            yield conn
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            raise
        finally:
            if conn:
                try:
                    self.connection_pool.putconn(conn)
                except Exception as e:
                    logger.error(f"Error returning connection to pool: {e}", exc_info=True)


    @contextmanager
    def get_cursor(self, commit=False):
        """
        Context manager for database cursors.
        """
        with self.get_connection() as conn:
            cursor = None
            try:
                cursor = conn.cursor()
                yield cursor
                if commit:
                    try:
                        conn.commit()
                    except Exception as e:
                        logger.error(f"Error committing transaction: {e}", exc_info=True)
                        conn.rollback()
                        raise
            except Exception as e:
                logger.error(f"Error in cursor operation: {e}", exc_info=True)
                try:
                    conn.rollback()
                except Exception as rollback_error:
                    logger.error(f"Error during rollback: {rollback_error}", exc_info=True)
                raise
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except Exception as e:
                        logger.error(f"Error closing cursor: {e}", exc_info=True)

    def execute_select_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results as a list of dictionaries.

        Args:
            query (str): SQL SELECT query
            params (tuple, optional): Parameters for the query

        Returns:
            List[Dict[str, Any]]: List of dictionaries with column names as keys
        """
        start_time = time.time()
        try:
            logger.info(f"query:\n{query}\nparams:\n{params}")
            with self.get_cursor() as cursor:
                try:
                    cursor.execute(query, params)
                    columns = [desc[0] for desc in cursor.description]
                    results = cursor.fetchall()

                    execution_time = time.time() - start_time
                    if execution_time > 1.0:  # Log slow queries (> 1 second)
                        logger.warning(f"Slow SELECT query ({execution_time:.2f}s): {query}")

                    # Convert results to list of dictionaries
                    return [dict(zip(columns, row)) for row in results]
                except Exception as e:
                    logger.error(f"Error executing SELECT query: {query}")
                    logger.error(f"Parameters: {params}")
                    logger.error(f"Exception: {str(e)}")
                    logger.error(f"Exception type: {type(e).__name__}")
                    logger.error(f"Stack trace:", exc_info=True)
                    return []
        except Exception as e:
            logger.error(f"Unexpected error in execute_select_query: {e}", exc_info=True)
            return []

    def execute_insert_query(
            self,
            query: str,
            params: Optional[Union[Tuple, List[Tuple]]] = None,
            return_id: bool = False,
            id_column: str = "id"
    ) -> Union[int, List[int], None]:
        """
        Execute an INSERT query

        Args:
            query (str): SQL INSERT query
            params (tuple or list of tuples): Parameters for single insert or batch insert
            return_id (bool): Whether to return the ID(s) of inserted row(s)
            id_column (str): Name of the ID column to return

        Returns:
            int, List[int], or None: ID(s) of inserted row(s) if return_id=True, otherwise None
        """
        start_time = time.time()
        try:
            logger.info(f"query:\n{query}\nparams:\n{params}")

            with self.get_cursor(commit=True) as cursor:
                try:
                    if return_id:
                        query += f" RETURNING {id_column}"

                    # Handle batch inserts
                    if isinstance(params, list) and len(params) > 0 and isinstance(params[0], tuple):
                        # For batch inserts
                        cursor.executemany(query, params)
                        if return_id and cursor.rowcount > 0:
                            # Return list of IDs for batch inserts
                            return [row[0] for row in cursor.fetchall()]
                    else:
                        # For single inserts
                        cursor.execute(query, params)
                        if return_id and cursor.rowcount > 0:
                            # Return single ID
                            result = cursor.fetchone()
                            return result[0] if result else None

                    execution_time = time.time() - start_time
                    if execution_time > 1.0:  # Log slow queries (> 1 second)
                        logger.warning(f"Slow INSERT query ({execution_time:.2f}s): {query}")

                    return cursor.rowcount
                except Exception as e:
                    logger.error(f"Error executing INSERT query: {query}")
                    logger.error(f"Parameters: {params}")
                    logger.error(f"Exception: {str(e)}")
                    logger.error(f"Exception type: {type(e).__name__}")
                    logger.error(f"Stack trace:", exc_info=True)
                    return None
        except Exception as e:
            logger.error(f"Unexpected error in execute_insert_query: {e}", exc_info=True)
            return None

    def execute_update_query(self, query: str, params: Optional[Tuple] = None) -> int:
        """
        Execute an UPDATE query

        Args:
            query (str): SQL UPDATE query
            params (tuple, optional): Parameters for the query

        Returns:
            int: Number of affected rows
        """
        start_time = time.time()
        try:
            logger.info(f"query:\n{query}\nparams:\n{params}")

            with self.get_cursor(commit=True) as cursor:
                try:
                    cursor.execute(query, params)
                    affected_rows = cursor.rowcount

                    execution_time = time.time() - start_time
                    if execution_time > 1.0:  # Log slow queries (> 1 second)
                        logger.warning(f"Slow UPDATE query ({execution_time:.2f}s): {query}")

                    return affected_rows
                except Exception as e:
                    logger.error(f"Error executing UPDATE query: {query}")
                    logger.error(f"Parameters: {params}")
                    logger.error(f"Exception: {str(e)}")
                    logger.error(f"Exception type: {type(e).__name__}")
                    logger.error(f"Stack trace:", exc_info=True)
                    return 0
        except Exception as e:
            logger.error(f"Unexpected error in execute_update_query: {e}", exc_info=True)
            return 0

    def execute_delete_query(self, query: str, params: Optional[Tuple] = None) -> int:
        """
        Execute a DELETE query

        Args:
            query (str): SQL DELETE query
            params (tuple, optional): Parameters for the query

        Returns:
            int: Number of affected rows
        """
        start_time = time.time()
        try:
            with self.get_cursor(commit=True) as cursor:
                try:
                    cursor.execute(query, params)
                    affected_rows = cursor.rowcount

                    execution_time = time.time() - start_time
                    if execution_time > 1.0:  # Log slow queries (> 1 second)
                        logger.warning(f"Slow DELETE query ({execution_time:.2f}s): {query}")

                    return affected_rows
                except Exception as e:
                    logger.error(f"Error executing DELETE query: {query}")
                    logger.error(f"Parameters: {params}")
                    logger.error(f"Exception: {str(e)}")
                    logger.error(f"Exception type: {type(e).__name__}")
                    logger.error(f"Stack trace:", exc_info=True)
                    return 0
        except Exception as e:
            logger.error(f"Unexpected error in execute_delete_query: {e}", exc_info=True)
            return 0

    def execute_transaction(self, queries_with_params: List[Tuple[str, Optional[Tuple]]]) -> bool:
        """
        Execute multiple queries in a transaction.

        Args:
            queries_with_params: List of (query, params) tuples to execute in transaction

        Returns:
            bool: True if transaction successful, False otherwise
        """
        start_time = time.time()
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    for idx, (query, params) in enumerate(queries_with_params):
                        logger.info(f"query:\n{query}\nparams:\n{params}")

                        try:
                            cursor.execute(query, params)
                        except Exception as e:
                            logger.error(f"Error in transaction (query #{idx + 1}): {query}")
                            logger.error(f"Parameters: {params}")
                            logger.error(f"Exception: {str(e)}")
                            logger.error(f"Exception type: {type(e).__name__}")
                            logger.error(f"Stack trace:", exc_info=True)
                            raise

                conn.commit()

                execution_time = time.time() - start_time
                if execution_time > 2.0:  # Log slow transactions (> 2 seconds)
                    logger.warning(f"Slow transaction ({execution_time:.2f}s) with {len(queries_with_params)} queries")

                return True
            except Exception as e:
                try:
                    conn.rollback()
                except Exception as rollback_error:
                    logger.error(f"Error during transaction rollback: {rollback_error}", exc_info=True)

                logger.error(f"Transaction failed: {e}", exc_info=True)
                return False

db = PostgresDB()