import json
import re 
from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx

from app.config import OLLAMA_MODEL,OLLAMA_BASE_URL,LLM_TEMPERATURE

class OllamaClient:

	def __init__(self,base_url:str = OLLAMA_BASE_URL,
		model_name:str = OLLAMA_MODEL,
		temperature:float = LLM_TEMPERATURE):

		self.base_url = base_url
		self.model_name = model_name
		self.temperature = temperature

	async def chat_stream(self,messages:List[Dict[str,str]],
		temperature:float = None)-> AsyncGenerator[str,None]:

		temp = self.temperature if temperature is None else temperature

		payload = {
		    "model": self.model_name,
		    "messages": messages,
		    "stream": True,
		    "options": {
		        "temperature": temp,
		        "num_ctx": 4096
		    }
		}

		async with httpx.AsyncClient(timeout=60) as client:
			async with client.stream('POST',f"{self.base_url}/api/chat",json=payload) as stream:
				async for chunk in stream.aiter_lines():
					if not chunk :
						continue
					try:
						data = json.loads(chunk)
						token = data.get('message',{}).get('content','')
						if token:
							yield token
					except (json.JSONDecodeError , KeyError):
						continue

	async def extract_triples(self,text:str)->List[Dict[str,str]]:
		clean_text = text.strip()
		if not clean_text:
			return []

		prompt = (
		"You are an information extraction system. Extract key relational triples from the text.\n"
		"Valid types: Person, Email, Project, Tool, Topic, Default.\n"
		"Return ONLY a valid JSON list of objects without explanations or markdown backticks.\n\n"
		"Example format:\n"
		'[{"source": "Sarah", "source_type": "Person", "relation": "DISCUSSES", "target": "Synapse", "target_type": "Project"}]\n\n'
		f"TEXT:\n{clean_text}\n\n"
		"JSON:"
		)

		payload = {
		    "model": self.model_name,
		    "prompt": prompt,
		    "stream": False,
		    "options": {
		        "temperature": 0.0,
		        "num_ctx": 2048
		    }
		}

		try:
			async with httpx.AsyncClient(timeout=45.0) as client:
				res = await client.post(f"{self.base_url}/api/generate", json=payload)
				res.raise_for_status()
				raw_text = res.json().get("response", "").strip()

			cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text, flags=re.MULTILINE).strip()
			parsed = json.loads(cleaned)

			if isinstance(parsed, list):
				valid_triples = []
				for item in parsed:
					if isinstance(item, dict) and "source" in item and "relation" in item and "target" in item:
						valid_triples.append({
						    "source": str(item["source"]).strip(),
						    "relation": str(item["relation"]).strip().upper().replace(" ", "_"),
						    "target": str(item["target"]).strip(),
						    "source_type": str(item.get("source_type", "Default")).strip().title(),
						    "target_type": str(item.get("target_type", "Default")).strip().title(),
						})
				return valid_triples

		except Exception:
			return []

	async def decide_gmail_tool_call(self, user_message: str) -> Optional[Dict[str, Any]]:
		"""
		Determines whether the LLM needs to call the Gmail MCP `search_emails` tool
		to answer `user_message`, and constructs the optimal Gmail search query
		(e.g. `label:INBOX is:unread`, `from:Sarah`, `label:INBOX`).
		Returns None if no Gmail tool call is needed.
		"""
		text = (user_message or "").strip()
		if not text:
			return None

		q_lower = text.lower()

		# Fast gate: if the prompt is a simple greeting or has no email/inbox/message/sender intent, skip tool call
		email_intent_pattern = re.compile(
			r"\b(email|emails|e-mail|inbox|unread|mail|mails|message|messages|gmail|sender|sent me|from\s+[a-z0-9_.-]+|check\s+my\s+mail|check\s+my\s+inbox|recent\s+threads|action\s+items|updates\s+from)\b",
			re.IGNORECASE,
		)
		if not email_intent_pattern.search(q_lower):
			return None

		# Construct smart default Gmail query from the user's natural language request
		wants_unread = bool(
			re.search(r"\b(unread|unseen|not\s+read|new\s+email|new\s+emails|new\s+message|new\s+messages)\b", q_lower)
		)
		default_query = "label:INBOX is:unread" if wants_unread else "label:INBOX"

		from_match = re.search(r"\bfrom\s+([a-zA-Z0-9_.@-]+)", text, re.IGNORECASE)
		if from_match:
			sender_term = from_match.group(1).strip("?.!,")
			if sender_term.lower() not in {"my", "the", "recent", "inbox", "gmail", "email", "emails"}:
				default_query = f"from:{sender_term} is:unread" if wants_unread else f"from:{sender_term}"

		# Ask the local LLM whether to invoke `search_emails` and what Gmail query to pass
		tool_prompt = (
			"You are a tool-calling router for a personal AI assistant with access to a Gmail MCP tool:\n"
			"Tool Name: search_emails\n"
			"Arguments: {\"query\": \"<Gmail search query like 'label:INBOX', 'label:INBOX is:unread', 'from:Name'>\", \"max_results\": 5}\n\n"
			"Decide if the user's message requires calling `search_emails` to check or fetch their emails.\n"
			"Return ONLY valid JSON without markdown backticks in this exact format:\n"
			"{\"call_tool\": true, \"query\": \"label:INBOX is:unread\", \"max_results\": 5}\n"
			"or if no email check is needed:\n"
			"{\"call_tool\": false}\n\n"
			f"USER MESSAGE: {text}\n"
			"JSON:"
		)

		payload = {
			"model": self.model_name,
			"prompt": tool_prompt,
			"stream": False,
			"options": {
				"temperature": 0.0,
				"num_ctx": 1024,
			},
		}

		try:
			async with httpx.AsyncClient(timeout=8.0) as client:
				res = await client.post(f"{self.base_url}/api/generate", json=payload)
				res.raise_for_status()
				raw_text = res.json().get("response", "").strip()

			cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text, flags=re.MULTILINE).strip()
			match = re.search(r"\{.*\}", cleaned, re.DOTALL)
			if match:
				cleaned = match.group(0)
			parsed = json.loads(cleaned)

			if isinstance(parsed, dict):
				if parsed.get("call_tool") is False:
					return None
				llm_query = str(parsed.get("query") or default_query).strip()
				if wants_unread and "is:unread" not in llm_query.lower():
					llm_query = f"{llm_query} is:unread".strip()
				max_res = int(parsed.get("max_results") or 5)
				max_res = max(1, min(max_res, 10))
				return {
					"tool": "search_emails",
					"query": llm_query or default_query,
					"max_results": max_res,
				}
		except Exception:
			pass

		# Fallback when email intent matched but LLM router timed out or returned non-JSON
		return {
			"tool": "search_emails",
			"query": default_query,
			"max_results": 5,
		}

	async def close(self):
		pass
