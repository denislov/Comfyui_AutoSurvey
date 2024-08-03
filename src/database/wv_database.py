import json
import os
import weaviate
import weaviate.classes.config as wc
from langchain_community.document_loaders import (
    TextLoader,
    UnstructuredWordDocumentLoader,
    PyMuPDFLoader,
)  # 文本加载器
from langchain.text_splitter import RecursiveCharacterTextSplitter
from weaviate.util import generate_uuid5
from weaviate.classes.query import MetadataQuery

import folder_paths
from .database import Database


class WV_database(Database):
    def __init__(
        self, http_host: str, http_port: int, grpc_host: str, grpc_port: int
    ,default_class:str) -> None:
        # self.model = SentenceTransformer(model,trust_remote_code=True)
        self.client = weaviate.connect_to_custom(
            http_host=http_host,  # URL only, no http prefix
            http_port=http_port,
            http_secure=False,  # Set to True if https
            grpc_host=grpc_host,
            grpc_port=grpc_port,  # Default is 50051, WCD uses 443
            grpc_secure=False,  # Edit as needed
        )
        self.class_name = default_class

    def create_database(self, class_name, properties=None):
        if properties is None:
            properties = [
                wc.Property(
                    name="title", data_type=wc.DataType.TEXT, skip_vectorization=True
                ),
                wc.Property(name="content", data_type=wc.DataType.TEXT),
            ]
        collection = self.client.collections.create(
            name=class_name,
            vectorizer_config=[
                wc.Configure.NamedVectors.text2vec_transformers(
                    pooling_strategy="cls",
                    name="content_vector",
                    source_properties=["content"],
                ),
            ],
            properties=properties,
        )
        config = collection.config.get()
        return (
            collection,
            f"database created:\n {json.dumps(config.to_dict(), indent=2)}",
        )

    def delete_database(self, class_name, **kargs):
        if self.client.collections.exists(class_name):
            self.client.collections.delete(class_name)
        return f"delete {class_name} successfully"

    def get_database(self, class_name):
        return self.client.collections.get(class_name)

    def get_paper_info_from_ids(self, ids: list[str]):
        collection = self.client.collections.get(self.class_name)
        objs = []
        for id in ids:
            try:
                obj = collection.query.fetch_object_by_id(uuid=id)
                objs.append(obj.properties)
            except ValueError as e:
                print(id)
                print(e)
        return objs

    def get_knowledge_all(self):
        knowledges = list(self.client.collections.list_all().keys())
        return knowledges

    def add_text(self, item: dict):
        collection = self.client.collections.get(self.class_name)
        uuid = collection.data.insert(properties=item, uuid=generate_uuid5())
        print("added text success:", uuid)

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
            collection = self.client.collections.get(class_name)
            with collection.batch.dynamic() as batch:
                for chunk in chunks:
                    obj_uuid = generate_uuid5(chunk)
                    batch.add_object(
                        properties={
                            "title": os.path.basename(chunk.metadata["source"]),
                            "content": chunk.page_content,
                        },
                        uuid=obj_uuid,
                    )
                    obj_uuids.append(obj_uuid)
            print("added document success:", os.path.basename(doc))
        response = json.dumps(obj_uuids, indent=2, ensure_ascii=False)
        return response

    def set_knowledge_class(self, class_name: str):
        self.class_name = class_name
        print("class_name is set to:", self.class_name)

    def search_by_text(self, class_name, text: str, num: int = 4, **kwargs):
        collection = self.client.collections.get(class_name)
        response = collection.query.near_text(
            query=text,
            limit=num,
            target_vector="content_vector",
            return_metadata=MetadataQuery(distance=True, score=True),
        ).objects
        return [item.properties for item in response]

    def get_ids_from_query(self, query, num, shuffle=False):
        collection = self.client.collections.get(self.class_name)
        response = collection.query.near_text(
            query=query,
            limit=num,
            target_vector="content_vector",
            return_metadata=MetadataQuery(distance=True, score=True),
        ).objects
        return [obj.uuid for obj in response]

    def get_titles_from_citations(self, citations):
        objs = []
        for cite in citations:
            collection = self.client.collections.get(self.class_name)
            objs.append(
                collection.query.near_text(
                    query=cite,
                    target_vector="content_vector",
                    limit=1,
                ).objects[0]
            )
        return [obj.uuid for obj in objs]
