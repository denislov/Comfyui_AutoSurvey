import json
from .ms_database import MilvusDatabase
from pymilvus import (
    FieldSchema, DataType,
)

class ComfyMilvus:

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "http_host": (
                    "STRING",
                    {
                        "multiline": False,  # True if you want the field to look like the one on the ClipTextEncode node
                        "default": "localhost",
                    },
                ),
                "http_port": (
                    "STRING",
                    {
                        "multiline": False, 
                        "default": "19530",
                    },
                ),
                "default_class": (
                    "STRING",
                    {
                        "multiline": False,  # True if you want the field to look like the one on the ClipTextEncode node
                        "default": "toursim_compensation",
                    },
                ),
            },
        }

    RETURN_TYPES = ("DB_CLIENT", "STRING")
    RETURN_NAMES = ("Milvus Client", "text")

    FUNCTION = "create_client"

    # OUTPUT_NODE = False

    CATEGORY = "Senser/milvus"

    def create_client(
        self, http_host:str,http_port:str, default_class:str
    ):

        client_info =  json.dumps(
            {"http_host":http_host,"http_port":http_port, "default_class":default_class},
            indent=2,
            ensure_ascii=False,
        )
        self.db = MilvusDatabase(default_class,http_host,http_port)
        message = f"Milvus client:\n{client_info}\n{self.db.client.get_collection_stats(default_class)}"
        print(message)
        return (self.db, message)


class MilvusScheme:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "prop_1": ("MS_FIELD",),
            },
            "optional": {
                "prop_2": ("MS_FIELD",),
                "prop_3": ("MS_FIELD",),
            },
            "hidden": {
                "prop_4": ("MS_FIELD",),
                "prop_5": ("MS_FIELD",),
                "prop_6": ("MS_FIELD",),
            },
        }

    RETURN_TYPES = ("MS_SCHEME", "STRING")
    RETURN_NAMES = ("MilvusScheme", "text")
    FUNCTION = "combine_field"

    CATEGORY = "Senser/milvus"

    def combine_field(self, **kargs):
        properties = []
        name_dict = {}
        for k, arg in kargs.items():
            if isinstance(arg, FieldSchema):
                if arg.name in name_dict:
                    name_dict[arg.name] += 1
                else:
                    name_dict[arg.name] = 1
                properties.append(arg)
        duplicates = [name for name, count in name_dict.items() if count > 1]
        if len(duplicates) > 0:
            prop_str = f"存在重复的属性名称:{', '.join(duplicates)}"
            return None, prop_str
        prop_str = [json.loads(prop.model_dump_json()) for prop in properties]
        return properties, json.dumps(prop_str, indent=2, ensure_ascii=False)


class MsField:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "name": (
                    "STRING",
                    {
                        "multiline": False,  # True if you want the field to look like the one on the ClipTextEncode node
                        "default": "title",
                    },
                ),
                "data_type": (["TEXT", "INT","SPARSE_VECTOR","DENSE_VECTOR"],),
                "is_primary": (["enable", "disable"],),
                "max_length": (
                    "INT",
                    {
                        "default": 100,
                        "min": 100,  # Minimum value
                        "max": 10000,  # Maximum value
                        "display": "number",  # Cosmetic only: display as "number" or "slider"
                    },
                ),
            },
        }

    RETURN_TYPES = ("MS_FIELD", "STRING")
    RETURN_NAMES = ("Milvus Field", "text")
    FUNCTION = "generate_field"

    CATEGORY = "Senser/milvus"

    def generate_field(self, name, data_type, is_primary,max_length):
        prop_str = {
            "name": name,
            "data_type": data_type,
            "is_primary": is_primary,
            "max_length": max_length,
        }
        if is_primary == "enable":
            is_primary = True
        else:
            is_primary = False
        if data_type == "TEXT":
            data_type = DataType.VARCHAR
        elif data_type == "SPARSE_VECTOR":
            data_type = DataType.SPARSE_FLOAT_VECTOR
        elif data_type == "DENSE_VECTOR":
            data_type = DataType.FLOAT_VECTOR
        else:
            data_type = DataType.VARCHAR
        prop = FieldSchema(
                name=name, dtype=data_type, is_primary=is_primary, max_length=max_length
            )
        return prop, prop_str


# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
MS_NODE_CLASS_MAPPINGS = {
    "ComfyMilvus": ComfyMilvus,
    "MsField": MsField,
    "MilvusScheme": MilvusScheme,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
MS_NODE_DISPLAY_NAME_MAPPINGS = {
    "ComfyMilvus": "Milvus Client",
    "MsField": "Milvus Field",
    "MilvusScheme": "Milvus Scheme",
}
