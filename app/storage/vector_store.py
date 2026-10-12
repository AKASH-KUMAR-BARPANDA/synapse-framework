import collections
from typing import List,Optional
import chromadb
from langchain_chroma import Chroma
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_core.documents import Document


from app.config import (
    CHROMA_DIR,
    CHROMA_COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
    DEFAULT_TOP_K
)

class LocalVectorStorage:
	def __init__(self,collection_name:str=CHROMA_COLLECTION_NAME):
		self.collection_name = collection_name
		self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))
		self.embedding_function = FastEmbedEmbeddings(model_name=EMBEDDING_MODEL_NAME)
		self.store = Chroma(
			client=self.client,
			collection_name=collection_name,
			embedding_function=self.embedding_function
			)

	def add_documents(self,documents:List[Document])->List[str]:
		if not documents:
			return []
		ids = [
			str(doc.metadata.get("chunk_id"))
			for doc in documents
			if doc.metadata and doc.metadata.get("chunk_id")
		]
		if len(ids) == len(documents):
			return self.store.add_documents(documents, ids=ids)
		return self.store.add_documents(documents)


	def similarity_search(self,query:str,k:int=DEFAULT_TOP_K,filter_dict:Optional[dict]=None):
		return self.store.similarity_search(query=query,k=k,filter=filter_dict)

	def count(self)->int:
		collection = self.client.get_collection(self.collection_name)
		return collection.count()


