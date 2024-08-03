import json
import os
from pymilvus import (
    MilvusClient,
    connections,
    FieldSchema, CollectionSchema, DataType,
    Collection, AnnSearchRequest, RRFRanker,
)
from langchain_community.document_loaders import (
    TextLoader,
    UnstructuredWordDocumentLoader,
)  # 文本加载器
import folder_paths
import requests
import tqdm
from weaviate.util import generate_uuid5
from milvus_model.hybrid import BGEM3EmbeddingFunction    
from milvus_model.reranker import BGERerankFunction
from .database import Database
from ComfyUI_Autosurvey.src.utils.ocrpdfoader import UnstructuredPaddlePDFLoader
from ComfyUI_Autosurvey.src.utils.chinese_text_spliter import ChineseTextSplitter

class MilvusDatabase(Database):
    def __init__(self, name:str,http_host:str,http_port:str,use_bge_m3=True,use_reranker=True):
        self.host = http_host
        self.port = http_port
        uri = f"http://{http_host}:{http_port}"
        self.client = MilvusClient(uri=uri)
        self.class_name = name
        self.dense_dim = 1024
        self.use_bge_m3 = use_bge_m3
        self.use_reranker = use_reranker
        self.ef = None
        self.bge_rf = None

    @property
    def fields(self):
        fields = [
            FieldSchema(
                name="chunk_id", dtype=DataType.VARCHAR, is_primary=True, max_length=100
            ),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=640),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4000),
            FieldSchema(name="sparse_vector", dtype=DataType.SPARSE_FLOAT_VECTOR),
            FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR,
                    dim=self.dense_dim),
        ]
        return fields
    def create_collection(self,col_name):
        schema = CollectionSchema(self.fields, "")
        self.client.create_collection(col_name, schema=schema, consistency_level="Strong")
        res = self.client.get_collection_stats(col_name)
        return res
    def index_collection(self,col_name):
        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="sparse_vector",
            metric_type="IP",
            index_type="SPARSE_INVERTED_INDEX",
            index_name="sparse_vector_index",
            params={ "nlist": 128 }
        )
        index_params.add_index(
            field_name="dense_vector",
            metric_type="IP",
            index_type="FLAT",
            index_name="dense_vector_index",
            params={ "nlist": 128 }
        )
        self.client.create_index(col_name, index_params=index_params)

    def load_collection(self,col_name):
        self.client.load_collection(col_name)
        res = self.client.get_load_state(col_name)
        return res
    
    def insert_data(self,col_name,id,title,content):
        if len(self.client.query(col_name,filter=f'chunk_id == "{id}"'))==0:
            return
        if self.ef is None:
            self.ef = BGEM3EmbeddingFunction(use_fp16=False, device="cuda")
            self.dense_dim = self.ef.dim["dense"]
        docs_embeddings = self.ef([content])
        # print(docs_embeddings['sparse'].shape)
        # return
        data = { "chunk_id":id,
                 "title":title,
                 "content":content,
                 "sparse_vector":docs_embeddings["sparse"],
                 "dense_vector":docs_embeddings["dense"][0]
                 }
        try:
            res = self.client.insert(col_name,data)
            return res
        except Exception as e:
            print(e)
            print(data)
            print("content length:",len(content))

        
        # self.client.

    def search_by_text(self,col_name,query, topK):
        if self.ef is None:
            self.ef = BGEM3EmbeddingFunction(use_fp16=False, device="cuda")
            self.dense_dim = self.ef.dim["dense"]
        query_embeddings = self.ef([query])
        sparse_search_params = {"metric_type": "IP"}
        sparse_req = AnnSearchRequest(query_embeddings["sparse"],
                                    "sparse_vector", sparse_search_params, limit=topK)
        dense_search_params = {"metric_type": "IP"}
        dense_req = AnnSearchRequest(query_embeddings["dense"],
                                    "dense_vector", dense_search_params, limit=topK)

        # Search topK docs based on dense and sparse vectors and rerank with RRF.
        connections.connect(
            host=self.host, # Replace with your Milvus server IP
            port=self.port
        )
        res = Collection(col_name).hybrid_search([sparse_req, dense_req], rerank=RRFRanker(),
                                limit=topK, output_fields=['content','title','chunk_id'])
        if self.use_reranker:
            result_texts = [hit.fields["content"] for hit in res[0]]
            if self.bge_rf is None:
                self.bge_rf = BGERerankFunction(device='cuda')
            
            # rerank the results using BGE CrossEncoder model
            results = self.bge_rf(query, result_texts, top_k=topK)
            # print(results)
            
            resp = []
            for hit in results:
                # print(f'content: {hit.text} distance {hit.score}')
                resp.append(res[0][hit.index].fields)
            return resp
        return res
    def print_database(self):
        print(self.client.list_collections())
    
    @staticmethod
    def get_ocr_result(image_data: dict):
        response = requests.post("http://localhost:8010/ocr", json=image_data, timeout=60)
        response.raise_for_status()  # 如果请求返回了错误状态码，将会抛出异常
        return response.json()['results']

    def add_documents(self, class_name, docs: list[str]):
        print("file_list", docs)
        obj_uuids = []
        for doc in docs:
            full_output_folder = folder_paths.get_input_directory()
            filepath = os.path.abspath(os.path.join(full_output_folder, doc))
            loader = TextLoader(filepath, encoding="utf-8")
            isPdf = False
            if doc.endswith(".md"):
                loader = TextLoader(filepath, encoding="utf-8")
            elif doc.endswith(".docx"):
                loader = UnstructuredWordDocumentLoader(filepath)
            elif doc.endswith(".pdf"):
                isPdf = True
                loader = UnstructuredPaddlePDFLoader(filepath,MilvusDatabase.get_ocr_result)
            else:
                break
            text_splitter = ChineseTextSplitter(
                separators=[' ',".", "。", "!", "！", "?", "？", "；", ";"],
                chunk_size=500,
                chunk_overlap=100,
                pdf=isPdf
            )
            chunks = loader.load_and_split(text_splitter)
            for chunk in tqdm.tqdm(chunks):
                obj_uuid = generate_uuid5(chunk)
                self.insert_data(class_name, obj_uuid, os.path.basename(chunk.metadata["source"]),chunk.page_content[:3000])
                obj_uuids.append(obj_uuid)
            print("added document success:", os.path.basename(doc))
        response = json.dumps(obj_uuids, indent=2, ensure_ascii=False)
        return response
    def get_paper_info_from_ids(self, ids: list[str]):
        resp = self.client.query(self.class_name,filter=f'chunk_id in {ids}',output_fields=['content','title'])
        return resp
    
    def get_ids_from_query(self, query, num, shuffle=False):
        response = self.search_by_text(self.class_name,query,num)
        return [obj['chunk_id'] for obj in response]

    def get_titles_from_citations(self, citations):
        objs = []
        for cite in citations:
            objs.append(self.search_by_text(self.class_name, cite, 3))
        return [obj[0]['chunk_id'] for obj in objs]
