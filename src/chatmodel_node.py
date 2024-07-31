import json
import os
from .core.model import APIModel


class ChatModel:
    def __init__(self):
        p = os.path.dirname(os.path.realpath(__file__))
        config_path = os.path.join(p, '../config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        self.API_KEY=config['API_KEY']

        self.API_URL=config['API_URL']

        self.AVAILABLE_MODELS=config['AVAILABLE_MODELS']
        print(self.AVAILABLE_MODELS)

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "name": (s().AVAILABLE_MODELS,),
            },
            "optional": {
                "api_url": ("STRING", {"default": s().API_URL}),
                "api_key": ("STRING", {"default": s().API_KEY}),
            },
        }

    RETURN_TYPES = ("CHATMODEL", "STRING")
    RETURN_NAMES = ("Chat Model", "Chat Model Info")
    FUNCTION = "chat_bot"

    CATEGORY = "Senser/chat"

    def chat_bot(self, name, api_url, api_key):
        if api_url:
            api_url = self.API_URL
        if api_key:
            api_key = self.API_KEY
        model = APIModel(name, api_url=api_url, api_key=api_key)
        resp = model.chat("hello")
        return model, json.dumps(
            {
                "model": name,
                "api_url": api_url,
                "api_key": api_key,
                "test": {"user": "hello", "answer": resp},
            },
            indent=4,
        )


CM_NODE_CLASS_MAPPINGS = {
    "ChatModel": ChatModel,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
CM_NODE_DISPLAY_NAME_MAPPINGS = {
    "ChatModel": "Chat Model",
}
