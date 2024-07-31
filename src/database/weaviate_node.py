import json
import weaviate.classes.config as wc

from .wv_database import WV_database


class ComfyWeaviate:

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
                    "INT",
                    {
                        "default": 8080,
                        "min": 3000,  # Minimum value
                        "max": 10000,  # Maximum value
                        "display": "number",  # Cosmetic only: display as "number" or "slider"
                    },
                ),
                "grpc_host": (
                    "STRING",
                    {
                        "multiline": False,  # True if you want the field to look like the one on the ClipTextEncode node
                        "default": "localhost",
                    },
                ),
                "grpc_port": (
                    "INT",
                    {
                        "default": 50051,
                        "min": 10000,  # Minimum value
                        "max": 60000,  # Maximum value
                        "display": "number",  # Cosmetic only: display as "number" or "slider"
                    },
                ),
                "default_class": (
                    "STRING",
                    {
                        "multiline": False,  # True if you want the field to look like the one on the ClipTextEncode node
                        "default": "Toursim_compensation",
                    },
                ),
            },
        }

    RETURN_TYPES = ("DB_CLIENT", "STRING")
    RETURN_NAMES = ("Weavite Client", "text")

    FUNCTION = "create_client"

    # OUTPUT_NODE = False

    CATEGORY = "Senser/weaviate"

    def create_client(
        self, http_host, http_port, grpc_host, grpc_port, default_class
    ):
        print(
            json.dumps(
                [
                    http_host,
                    http_port,
                    grpc_host,
                    grpc_port,
                ],
                indent=2,
                ensure_ascii=False,
            )
        )
        self.db = WV_database(http_host, http_port, grpc_host, grpc_port,default_class)
        message = f"weaviate client is ready: {self.db.client.is_ready()}"
        print(message)
        return (self.db, message)


class WcPropertyComb:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "prop_1": ("WC_PROPERTY",),
            },
            "optional": {
                "prop_2": ("WC_PROPERTY",),
                "prop_3": ("WC_PROPERTY",),
            },
            "hidden": {
                "prop_4": ("WC_PROPERTY",),
                "prop_5": ("WC_PROPERTY",),
                "prop_6": ("WC_PROPERTY",),
            },
        }

    RETURN_TYPES = ("WC_PROPERTY_ARRAY", "STRING")
    RETURN_NAMES = ("Weaviate Property Comb", "text")
    FUNCTION = "combine_property"

    CATEGORY = "Senser/weaviate"

    def combine_property(self, **kargs):
        properties = []
        name_dict = {}
        for k, arg in kargs.items():
            if isinstance(arg, wc.Property):
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


class WcProperty:
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
                "data_type": (["TEXT", "INT"],),
                "skip_vectorization": (["enable", "disable"],),
            },
        }

    RETURN_TYPES = ("WC_PROPERTY", "STRING")
    RETURN_NAMES = ("Weaviate Property", "text")
    FUNCTION = "generate_property"

    CATEGORY = "Senser/weaviate"

    def generate_property(self, name, data_type, skip_vectorization):
        prop_str = {
            "name": name,
            "data_type": data_type,
            "skip_vectorization": skip_vectorization,
        }
        if skip_vectorization == "enable":
            skip_vectorization = True
        else:
            skip_vectorization = False
        if data_type == "TEXT":
            data_type = wc.DataType.TEXT
        else:
            data_type = wc.DataType.INT
        prop = wc.Property(
            name=name, data_type=data_type, skip_vectorization=skip_vectorization
        )
        return prop, prop_str


# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
WV_NODE_CLASS_MAPPINGS = {
    "ComfyWeaviate": ComfyWeaviate,
    "WcProperty": WcProperty,
    "WcPropertyComb": WcPropertyComb,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
WV_NODE_DISPLAY_NAME_MAPPINGS = {
    "ComfyWeaviate": "Weaviate Client",
    "WcProperty": "Wc Property",
    "WcPropertyComb": "Wc Property Comb",
}
