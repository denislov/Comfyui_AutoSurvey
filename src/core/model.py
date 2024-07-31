import requests
import json
from tqdm import tqdm
import concurrent.futures


class APIModel:

    def __init__(self, model, api_key, api_url) -> None:
        self.__api_key = api_key
        self.__api_url = api_url
        self.model = model

    def __req(self, text, temperature, max_try=5):
        url = f"{self.__api_url}"
        pay_load_dict = {
            "model": f"{self.model}",
            "messages": [
                {"role": "user", "temperature": temperature, "content": f"{text}"}
            ],
        }
        payload = json.dumps(pay_load_dict)
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.__api_key}",
            "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
            "Content-Type": "application/json",
        }
        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            return json.loads(response.text)["choices"][0]["message"]["content"]
        except:  # noqa: E722
            for _ in range(max_try):
                try:
                    response = requests.request(
                        "POST", url, headers=headers, data=payload
                    )
                    return json.loads(response.text)["choices"][0]["message"]["content"]
                except:  # noqa: E722
                    pass
            return None

    def chat(self, text, temperature=1):
        response = self.__req(text, temperature=temperature, max_try=5)
        return response

    def __chat(self, text, temperature, res_l, idx):

        response = self.__req(text, temperature=temperature)
        res_l[idx] = response
        return response

    def batch_chat(self, text_batch, temperature=0):
        res_l = ["No response"] * len(text_batch)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.__chat, text, temperature, res_l, i): i
                for i, text in enumerate(text_batch)
            }
            for future in tqdm(
                concurrent.futures.as_completed(futures), total=len(futures)
            ):
                idx = futures[future]
                try:
                    future.result()
                except Exception as exc:
                    print(f"Thread {idx} generated an exception: {exc}")
                else:
                    print(f"Thread {idx} completed successfully")

        return res_l
