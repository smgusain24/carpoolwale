from typing import Dict, Optional, Any, List, Union

from pymongo import MongoClient

from config.app_logger import logger

MONGO_URL="mongodb+srv://smgusain:SMGan1957@carpoolwale.nupzh.mongodb.net/"
mongo_client = MongoClient(MONGO_URL)
db = mongo_client['carpoolwaale']


def fetch_documents(
        collection_name: str,
        filter_query: Dict[str, Any],
        projection: Optional[List[str]] = None,
        sort_by: Optional[List[tuple]] = None,
        limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Fetch documents based on a filter query

    Parameters:
    - collection_name (str): The name of the collection to fetch documents from
    - filter_query (Dict[str, Any]): The filter query to match documents
    - projection (Optional[List[str]]): List of fields to include in the returned documents. Default: All
    - sort_by (Optional[List[tuple]]): List of tuples specifying the sort order. Each tuple contains a field name and
                                    the sort direction (1 for ascending, -1 for descending).
    - limit (Optional[int]): Maximum number of documents to return. Defaults to None (no limit).

    Returns:
    - List[Dict[str, Any]]: Fetched documents
    """
    try:
        collection = db[collection_name]

        # Build the projection dictionary if projection list is provided
        projection_dict = None
        if projection:
            projection_dict = {field: 1 for field in projection}

        cursor = collection.find(filter_query, projection_dict)

        if sort_by:
            cursor = cursor.sort(sort_by)

        if limit:
            cursor = cursor.limit(limit)

        return list(cursor)
    except Exception as e:
        logger.error(e, exc_info=True, stack_info=True)
        return []


def update_documents(
        collection_name: str,
        filter_query: Dict[str, Any],
        update_data: Dict[str, Any],
        upsert: bool = False,
        multi: bool = False
) -> Any:
    """
    Update documents based on a filter query.

    Parameters:
    - collection_name (str): The name of the collection to update documents in
    - filter_query (Dict[str, Any]): The filter query to match documents to update
    - update_data (Dict[str, Any]): The update operations to apply to the matched documents.
    - upsert (bool): Whether to insert a new document if no document matches the filter query. Defaults is False.
    - multi (bool): Whether to update multiple documents. Defaults is False.

    Returns:
    - Any: Result of the update operation.
    """
    try:
        collection = db[collection_name]

        if multi:
            result = collection.update_many(filter_query, update_data, upsert=upsert)
        else:
            result = collection.update_one(filter_query, update_data, upsert=upsert)
    except Exception as e:
        logger.error(e, exc_info=True, stack_info=True)


def insert_document(
        collection_name: str,
        document: Union[Dict[str, Any], List[Dict[str, Any]]]
) -> Any:
    """
    Insert a document into a MongoDB collection.

    Parameters:
    - collection_name (str): The name of the collection to insert the document into.
    - document Union[Dict[str, Any], List[Dict[str, Any]]]: The document or list of documents to insert.
    """
    try:
        collection = db[collection_name]
        if isinstance(document, list):
            collection.insert_many(document)
        elif isinstance(document, dict):
            collection.insert_one(document)
    except Exception as e:
        logger.error(e, exc_info=True, stack_info=True)
