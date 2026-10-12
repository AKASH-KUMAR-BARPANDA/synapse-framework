import hashlib
from typing import List, Dict,Any,Optional
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentChunker:

	def __init__(self,chunk_size:int=500,chunk_overlap:int=60):
		self.chunk_size = chunk_size
		self.chunk_overlap = chunk_overlap

		self.splitter = RecursiveCharacterTextSplitter(
			chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
            length_function=len,
			)

	@staticmethod
	def _generate_chunk_id(source:str, parent_id:str, index:int):
		seed = f"{source}:{parent_id}:{index}"
		return hashlib.sha256(seed.encode('utf-8')).hexdigest()[:16]

	def chunk_text(self,text:str,source:str='text',
		metadata:Optional[Dict[str,Any]]=None,
		parent_id:Optional[str] = None)->List[Document]:

		clean_text = text.strip()
		if not clean_text:
			return []
		base_meta = metadata.copy() if metadata else {}
		base_meta["source"] = source
		doc_id = parent_id or hashlib.md5(clean_text[:128].encode()).hexdigest()[:12]

		raw_chunks = self.splitter.split_text(clean_text)
		documents = []

		for idx, chunk in enumerate(raw_chunks):
			chunk_meta = {
			    **base_meta,
			    "parent_id": doc_id,
			    "chunk_index": idx,
			    "chunk_id": self._generate_chunk_id(source, doc_id, idx)
			}
			documents.append(Document(page_content=chunk, metadata=chunk_meta))

		return documents


	def chunk_email(self,email_data:Dict[str,Any])->List[Document]:
		email_id = str(email_data.get("id", ""))
		subject = email_data.get("subject", "No Subject").strip()
		sender = (email_data.get("from") or email_data.get("sender") or "Unknown Sender").strip()
		recipients = email_data.get("to", "Me").strip()
		date_str = email_data.get("date", "").strip()
		body = email_data.get("body", "").strip()
		is_unread = bool(email_data.get("is_unread", False))
		read_tag = "UNREAD" if is_unread else "READ"

		if not body and not subject:
			return []

		header_context = f"[EMAIL | {read_tag}] Subject: {subject} | From: {sender} | To: {recipients}"
		full_text = f"{header_context}\nDate: {date_str}\n\n{body}"

		base_meta = {
		    "source": "gmail",
		    "email_id": email_id,
		    "subject": subject,
		    "sender": sender,
		    "recipients": recipients,
		    "date": date_str,
		    "is_unread": is_unread,
		    "type": "Email"
		}

		raw_chunks = self.splitter.split_text(full_text)
		documents = []

		for idx, chunk in enumerate(raw_chunks):
			chunk_meta = {
			    **base_meta,
			    "chunk_index": idx,
			    "chunk_id": self._generate_chunk_id("gmail", email_id, idx)
			}
			documents.append(Document(page_content=chunk, metadata=chunk_meta))

		return documents

	def chunk_chat_turn(self,user_message: str,assistant_response: str,
		session_id: str,turn_index: int) -> List[Document]:

		content = f"User: {user_message.strip()}\nAssistant: {assistant_response.strip()}"
		base_meta = {
		    "source": "chat_history",
		    "session_id": session_id,
		    "turn_index": turn_index,
		    "type": "Conversation"
		}

		return self.chunk_text(
			text=content,
			source="chat_history",
			metadata=base_meta,
			parent_id=f"{session_id}_{turn_index}"
		)








