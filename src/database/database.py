class Database:
    def __init__(self, **kargs) -> None:
        # self.model = SentenceTransformer(model,trust_remote_code=True)
        pass

    def create_database(self, class_name, **kargs):
        raise NotImplementedError

    def delete_database(self, class_name, **kargs):
        raise NotImplementedError

    def get_database(self, class_name):
        raise NotImplementedError

    def get_paper_info_from_ids(self, ids: list[str]):
        raise NotImplementedError

    def get_knowledge_all(self):
        raise NotImplementedError

    def add_text(self, item: dict):
        raise NotImplementedError

    def add_documents(self, docs: list[str]):
        raise NotImplementedError

    def set_knowledge_class(self, class_name: str):
        raise NotImplementedError

    def search_by_text(self, class_name: str, text: str, num: int, **kargs):
        raise NotImplementedError

    def get_ids_from_query(self, query, num, shufflee):
        raise NotImplementedError

    def get_titles_from_citations(self, citations):
        raise NotImplementedError
