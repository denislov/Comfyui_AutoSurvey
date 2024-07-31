from typing import List
import tiktoken


class tokenCounter:

    def __init__(self) -> None:
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        self.model_price = {}

    def num_tokens_from_string(self, string: str) -> int:
        return len(self.encoding.encode(string))

    def num_tokens_from_list_string(self, list_of_string: List[str]) -> int:
        num = 0
        for s in list_of_string:
            if s is None:
                continue
            num += len(self.encoding.encode(s))
        return num

    def compute_price(self, input_tokens, output_tokens, model):
        return (input_tokens / 1000) * self.model_price[model][0] + (
            output_tokens / 1000
        ) * self.model_price[model][1]

    def text_truncation(self, text, max_len=1000):
        encoded_id = self.encoding.encode(text, disallowed_special=())
        return self.encoding.decode(encoded_id[: min(max_len, len(encoded_id))])
