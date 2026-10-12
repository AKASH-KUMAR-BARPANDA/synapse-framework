import re
from typing import List ,Dict , Any,Optional
from langchain_core.documents import Document

from app.storage.graph_store import PersistentGraphStore
from app.storage.vector_store import LocalVectorStorage
from app.config import DEFAULT_TOP_K



class HybridRAGEngine:

	def __init__(self,vector_store:Optional[LocalVectorStorage],
		graph_store:Optional[PersistentGraphStore]):

		self.vector_store = vector_store or LocalVectorStorage()
		self.graph_store = graph_store or PersistentGraphStore()


	def _extract_candidate_entities(self,query:str)->List[str]:

		candidates = set()

		existing_nodes = list(self.graph_store.graph.nodes)
		query_lower = query.lower()

		for node in existing_nodes:
			if str(node).lower() in query_lower:
				candidates.add(str(node))

		matches = re.findall(r"\b[A-Z][a-zA-Z0-9_-]+\b", query)

		for m in matches:
			candidates.add(m)

		return list(candidates)


	def retrieve_context(self,query:str,
		k:int = DEFAULT_TOP_K,
		filter_dict:Optional[Dict] = None)->Dict[str,Any]:

		vector_docs: List[Document] = self.vector_store.similarity_search(
			query=query,k=k,
			filter_dict=filter_dict)




		candidate_entities = self._extract_candidate_entities(query)
		graph_facts:List[str] = []

		for entity in candidate_entities:
			facts = self.graph_store.find_relation_for(entity)
			graph_facts.extend(facts)

		unique_facts = list(dict.fromkeys(graph_facts))

		formatted_context = self._format_prompt_context(vector_docs,unique_facts)

		serialized_chunks = [
			{
				"page_content": doc.page_content,
				"metadata": doc.metadata,
				"source": doc.metadata.get("source", "chroma_db"),
				"subject": doc.metadata.get("subject", ""),
				"chunk_id": doc.metadata.get("chunk_id", ""),
			}
			for doc in vector_docs
		]

		return {
            "query": query,
            "vector_documents": vector_docs,
            "chunks": serialized_chunks,
            "graph_facts": unique_facts,
            "graph_triples": unique_facts,
            "entities_detected": candidate_entities,
            "formatted_context": formatted_context
        }


	@staticmethod
	def _format_prompt_context(vector_docs:List[Document],graph_facts:List[str]) -> str:
		sections = []

		if graph_facts:
			facts_block = "\n".join(f"- {fact}" for fact in graph_facts)
			sections.append(f"### RELATIONAL KNOWLEDGE GRAPH FACTS:\n{facts_block}")

		if vector_docs:
			doc_chunks = []

			for idx,doc in enumerate(vector_docs,1):
				src = doc.metadata.get("source", "unknown")
				subj = doc.metadata.get("subject", "")
				header = f"[{src.upper()}" + (f" - {subj}" if subj else "") + "]"
				doc_chunks.append(f"{idx}. {header}\n{doc.page_content.strip()}")
			sections.append("### RELEVANT DOCUMENT EXCERPTS:\n" + "\n\n".join(doc_chunks))

		if not sections:
			return "No relevant past context or graph facts found."

		return "\n\n".join(sections)




