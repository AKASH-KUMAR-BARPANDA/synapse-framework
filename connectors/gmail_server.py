
from typing import List,Dict,Any
from mcp.server.mcpserver import MCPServer
from base import GoogleServiceManager


gmail_server = MCPServer('GmailConnector')
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]



@gmail_server.tool()
def search_emails(query:str='label:INBOX',max_results:int = 5)->List[Dict[str,Any]]:
	google_auth_manager = GoogleServiceManager()
	service  = google_auth_manager.get_service('gmail','v1',GMAIL_SCOPES)
	response = service.users().messages().list(
		userId='me',
		q=query,
		maxResults = max_results
		).execute()

	messages_meta = response.get('messages',[])
	if not messages_meta:
		return []

	extracted_messages = []

	for meta in messages_meta:
		msg = service.users().messages().get(
			userId = 'me',
			id = meta['id'],
			format='full'
		).execute()

		payload = msg.get('payload',{})
		headers = payload.get('headers',[])
		label_ids = msg.get('labelIds', []) or []
		is_unread = 'UNREAD' in label_ids

		subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
		sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "Unknown Sender")
		recipient = next((h["value"] for h in headers if h["name"].lower() == "to"), "Me")
		date = next((h["value"] for h in headers if h["name"].lower() == "date"), "")

		body_text = GoogleServiceManager.decode_mime_body(payload)
		snippet = msg.get("snippet", "")

		extracted_messages.append({
            "id": msg["id"],
            "subject": subject,
            "sender": sender,
            "to": recipient,
            "date": date,
            "is_unread": is_unread,
            "labels": label_ids,
            "snippet": snippet,
            "body": (body_text.strip() or snippet.strip())
        })

	return extracted_messages




if __name__ == "__main__":
    gmail_server.run()


