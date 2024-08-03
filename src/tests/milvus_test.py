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
    PyMuPDFLoader,
)  # 文本加载器
from langchain.text_splitter import RecursiveCharacterTextSplitter
import folder_paths
from weaviate.util import generate_uuid5
# from pymilvus.model.hybrid import BGEM3EmbeddingFunction
from milvus_model.hybrid import BGEM3EmbeddingFunction    
from milvus_model.reranker import BGERerankFunction

class MilvusDatabase:
    def __init__(self, name, use_bge_m3=True,use_reranker=True):
        self.client = MilvusClient(uri='http://192.168.1.103:19530')
        self.dense_dim = 768
        if use_bge_m3:
            self.use_bge_m3 = use_bge_m3
            self.ef = BGEM3EmbeddingFunction(use_fp16=False, device="cuda")
            self.dense_dim = self.ef.dim["dense"]
        self.use_reranker = use_reranker

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
        print(content)
        docs_embeddings = self.ef([content])
        # print(docs_embeddings['sparse'].shape)
        # return
        data = { "chunk_id":id,
                 "title":title,
                 "content":content,
                 "sparse_vector":docs_embeddings["sparse"],
                 "dense_vector":docs_embeddings["dense"][0]
                 }
        print(data)
        res = self.client.insert(col_name,data)
        return res
        # self.client.

    def search_by_text(self,col_name,query, topK):
        query_embeddings = self.ef([query])
        sparse_search_params = {"metric_type": "IP"}
        sparse_req = AnnSearchRequest(query_embeddings["sparse"],
                                    "sparse_vector", sparse_search_params, limit=topK)
        dense_search_params = {"metric_type": "IP"}
        dense_req = AnnSearchRequest(query_embeddings["dense"],
                                    "dense_vector", dense_search_params, limit=topK)

        # Search topK docs based on dense and sparse vectors and rerank with RRF.
        connections.connect(
            host="192.168.1.103", # Replace with your Milvus server IP
            port="19530"
        )
        res = Collection(col_name).hybrid_search([sparse_req, dense_req], rerank=RRFRanker(),
                                limit=topK, output_fields=['content'])
        if self.use_reranker:
            result_texts = [hit.fields["content"] for hit in res[0]]
            bge_rf = BGERerankFunction(device='cuda')
            # rerank the results using BGE CrossEncoder model
            results = bge_rf(query, result_texts, top_k=topK)
            # print(results)
            for hit in results:
                print(f'content: {hit.text} distance {hit.score}')
            return results
        return res
    def print_database(self):
        print(self.client.list_collections())

    def add_documents(self, class_name, docs: list[str]):
        print("file_list", docs)
        obj_uuids = []
        for doc in docs:
            full_output_folder = folder_paths.get_input_directory()
            filepath = os.path.abspath(os.path.join(full_output_folder, doc))
            loader = TextLoader(filepath, encoding="utf-8")
            if doc.endswith(".md"):
                loader = TextLoader(filepath, encoding="utf-8")
            elif doc.endswith(".docx"):
                loader = UnstructuredWordDocumentLoader(filepath)
            elif doc.endswith(".pdf"):
                loader = PyMuPDFLoader(filepath)
            else:
                break
            documents = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500, chunk_overlap=50
            )
            chunks = text_splitter.split_documents(documents)

            for chunk in chunks:
                obj_uuid = generate_uuid5(chunk)
                self.insert_data(class_name, obj_uuid, os.path.basename(chunk.metadata["source"]),chunk.page_content)
                obj_uuids.append(obj_uuid)
            print("added document success:", os.path.basename(doc))
        response = json.dumps(obj_uuids, indent=2, ensure_ascii=False)
        return response

# 1. prepare a small corpus to search
docs = [
    "Artificial intelligence was founded as an academic discipline in 1956.",
    "Alan Turing was the first person to conduct substantial research in AI.",
    "Born in Maida Vale, London, Turing was raised in southern England.",
]

database = MilvusDatabase("test")
# database.create_collection("hyper_demo1")
database.print_database()
# database.index_collection("hyper_demo1")
# res = database.load_collection("hyper_demo1")
# res = database.client.get_load_state("hyper_demo1")
# database.add_documents("hyper_demo1", ['D:/AutoSurvey/raw_data/施 等 - 2024 - 个性化算法推荐阅读服务用户持续使用意愿影响因素研究.pdf'])
# print(res)
res = database.search_by_text("hyper_demo1", "什么是个性化算法推荐", topK=10)
print(res)
