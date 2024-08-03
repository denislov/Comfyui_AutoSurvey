"""Loader that loads image files."""
from typing import List, Callable

from langchain.document_loaders import UnstructuredFileLoader
from unstructured.partition.text import partition_text
import os
import fitz
from tqdm import tqdm
from typing import Union, Any
import numpy as np
import base64

class UnstructuredPaddlePDFLoader(UnstructuredFileLoader):
    """Loader that uses unstructured to load image files, such as PNGs and JPGs."""
    def __init__(
        self,
        file_path: Union[str, List[str]],
        ocr_engine: Callable,
        mode: str = "single",
        **unstructured_kwargs: Any,
    ):
        """Initialize with file path."""
        self.ocr_engine = ocr_engine
        super().__init__(file_path=file_path, mode=mode, **unstructured_kwargs)

    def _get_elements(self) -> List:
        def pdf_ocr_txt(filepath, dir_path="tmp_files"):
            full_dir_path = os.path.join(os.path.dirname(filepath), dir_path)
            if not os.path.exists(full_dir_path):
                os.makedirs(full_dir_path)
            doc = fitz.open(filepath)
            txt_file_path = os.path.join(full_dir_path, "{}.txt".format(os.path.split(filepath)[-1]))
            img_name = os.path.join(full_dir_path, 'tmp.png')
            with open(txt_file_path, 'w', encoding='utf-8') as fout:
                for i in tqdm(range(doc.page_count)):
                    page = doc.load_page(i)
                    pix = page.get_pixmap()
                    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))

                    img_data = {"img64": base64.b64encode(img).decode("utf-8"), "height": pix.h, "width": pix.w,
                                "channels": pix.n}
                    result = self.ocr_engine(img_data)
                    result = [line for line in result if line]
                    ocr_result = [i[1][0] for line in result for i in line]
                    fout.write("\n".join(ocr_result))
            if os.path.exists(img_name):
                os.remove(img_name)
            return txt_file_path

        txt_file_path = pdf_ocr_txt(self.file_path)
        return partition_text(filename=txt_file_path, **self.unstructured_kwargs)

# def get_ocr_result(image_data: dict):
#     response = requests.post("http://localhost:8010/ocr", json=image_data, timeout=60)
#     response.raise_for_status()  # 如果请求返回了错误状态码，将会抛出异常
#     return response.json()['results']
# filepath ='D:/AutoSurvey/raw_data/施 等 - 2024 - 个性化算法推荐阅读服务用户持续使用意愿影响因素研究.pdf'
# loader = UnstructuredPaddlePDFLoader(filepath,get_ocr_result)
# text_splitter = ChineseTextSplitter(
#     separators=[".", "。", "!", "！", "?", "？", "；", ";"],
#     chunk_size=500,
#     chunk_overlap=100,
#     pdf=True
#     # length_function=num_tokens,
# )

# res = loader.load()[0]
# with open('docs.txt', 'w', encoding='utf-8') as f:
#     f.write(json.dumps(res.page_content, ensure_ascii=False))
# with open('docs.txt', 'r', encoding='utf-8') as f:
#     docs = '\n'.join(f.readlines())
#     print(json.dumps(text_splitter.split_text(docs)[:5],ensure_ascii=False))

# docs = loader.load_and_split(text_splitter)
# print(docs)
# docs = [{"source":doc.metadata['source'],"content":doc.page_content.replace('\n\n','\n')} for doc in docs]
# with open('docs.json', 'w', encoding='utf-8') as f:
#     f.write(json.dumps(docs, ensure_ascii=False, indent=4))