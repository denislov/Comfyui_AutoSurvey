import json

from .database.weaviate_node import (
    WV_NODE_CLASS_MAPPINGS,
    WV_NODE_DISPLAY_NAME_MAPPINGS,
)
from .database.database import Database


class QueryKnowledge:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "db_client": ("DB_CLIENT", {"forceInput": True}),
                "class_name": (
                    "STRING",
                    {
                        "multiline": False,  # True if you want the field to look like the one on the ClipTextEncode node
                        "default": "Toursim_compensation",
                    },
                ),
                "query_text": (
                    "STRING",
                    {
                        "multiline": False,  # True if you want the field to look like the one on the ClipTextEncode node
                        "default": "旅游",
                    },
                ),
                "rag_number": (
                    "INT",
                    {"default": 4, "min": 1, "max": 100, "display": "number"},
                ),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "search_by_text"

    CATEGORY = "Senser/database"

    def search_by_text(
        self, db_client: Database, class_name: str, query_text: str, rag_number: int
    ):
        response = db_client.search_by_text(class_name, query_text, rag_number)

        response = json.dumps(
            [obj.properties for obj in response], indent=2, ensure_ascii=False
        )
        return (response,)


class ManageDatabase:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "db_client": ("DB_CLIENT", {"forceInput": True}),
                "class_name": (
                    "STRING",
                    {
                        "multiline": False,  # True if you want the field to look like the one on the ClipTextEncode node
                        "default": "knowledge",
                    },
                ),
                "operator": (["create", "delete"],),
            },
            "optional": {
                "properties": ("WC_PROPERTY_ARRAY", {"forceInput": True}),
            },
        }

    RETURN_TYPES = "STRING"
    RETURN_NAMES = "Database Info"
    FUNCTION = "manage_database"

    CATEGORY = "Senser/database"

    def manage_database(
        self, db_client: Database, class_name: str, operator: str, properties: list
    ):
        if operator == "create" and properties is not None:
            return db_client.create_database(class_name, properties=properties)
        elif operator == "delete":
            return db_client.delete_database(class_name)
        else:
            return "unknown operator!!! or properties is None"


class AddDoc2Knowledge:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "db_client": ("DB_CLIENT", {"forceInput": True}),
                "class_name": (
                    "STRING",
                    {
                        "multiline": False,  # True if you want the field to look like the one on the ClipTextEncode node
                        "default": "Toursim_compensation",
                    },
                ),
                "file_list": (
                    "ARRAY_STRING",
                    {
                        "multiline": False,  # True if you want the field to look like the one on the ClipTextEncode node
                        "default": "旅游",
                    },
                ),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("result",)
    FUNCTION = "add_documents"

    CATEGORY = "Senser/weaviate"

    def add_documents(self, db_client: Database, class_name: str, file_list: list[str]):
        response = db_client.add_documents(class_name, file_list)
        return (response,)


DATABAE_NODE_CLASS_MAPPINGS = {
    **WV_NODE_CLASS_MAPPINGS,
    "QueryKnowledge": QueryKnowledge,
    "ManageDatabase": ManageDatabase,
    "AddDoc2Knowledge": AddDoc2Knowledge,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
DATABAE_NODE_DISPLAY_NAME_MAPPINGS = {
    **WV_NODE_DISPLAY_NAME_MAPPINGS,
    "QueryKnowledge": "Query Knowledge",
    "ManageDatabase": "Manage Database",
    "AddDoc2Knowledge": "Add Doc to Knowledge",
}
