import json
import os
from .src.database_node import (
    DATABAE_NODE_CLASS_MAPPINGS,
    DATABAE_NODE_DISPLAY_NAME_MAPPINGS,
)
from .src.chatmodel_node import CM_NODE_CLASS_MAPPINGS, CM_NODE_DISPLAY_NAME_MAPPINGS
from .src.autosurvey_node import AS_NODE_CLASS_MAPPINGS, AS_NODE_DISPLAY_NAME_MAPPINGS

NODE_CLASS_MAPPINGS = {
    **DATABAE_NODE_CLASS_MAPPINGS,
    **CM_NODE_CLASS_MAPPINGS,
    **AS_NODE_CLASS_MAPPINGS,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    **DATABAE_NODE_DISPLAY_NAME_MAPPINGS,
    **CM_NODE_DISPLAY_NAME_MAPPINGS,
    **AS_NODE_DISPLAY_NAME_MAPPINGS,
}
WEB_DIRECTORY = "./js"

if not os.path.isfile(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")
):
    config = {
        "API_KEY": "u api key",
        "API_URL": "http://api.openai.com/v1/chat/completions",
        "AVAILABLE_MODELS": ["gpt-4o", "gpt-4o-mini"],
    }
    with open(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json"), "w"
    ) as f:
        json.dump(config, f, indent=4)

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
