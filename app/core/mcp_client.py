import sys
import json
import os
from typing import Dict , List, Any, Optional
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.config import ROOT_DIR as BASE_DIR


class MCPClientManager:

	def __init__(self):
		self._servers:Dict[str,StdioServerParameters] = {}

	def register_server(self,name:str,script_path:Path,env:Optional[Dict[str,str]] = None)->None:
		script_abs = Path(script_path).resolve()

		merged_env = os.environ.copy()
		python_path = f"{BASE_DIR}:{script_abs.parent}:{merged_env.get('PYTHONPATH', '')}"
		merged_env["PYTHONPATH"] = python_path

		if env:
			merged_env.update(env)

		server_params = StdioServerParameters(
			command=sys.executable,
			args=[str(script_abs)],
			env = merged_env
			)

		self._servers[name] = server_params

	async def list_tools(self,server_name:str) -> List[Dict[str,Any]]:
		if server_name not in self._servers:
			raise KeyError(f"Server '{server_name}' is not registered.")


		params = self._servers[server_name]
		async with stdio_client(params) as (read_stream,write_streram):
			async with ClientSession(read_stream,write_streram) as session:
				await session.initialize()
				tools_result = await session.list_tools()

				return [
					{
					    "name": tool.name,
					    "description": tool.description,
					    "inputSchema": tool.input_schema
					}
					for tool in tools_result.tools
					]

	async def call_tool(self,server_name: str,tool_name: str,
        arguments: Optional[Dict[str, Any]] = None) -> Any:

		if server_name not in self._servers:
			raise KeyError(f"Server '{server_name}' is not registered.")

		params = self._servers[server_name]
		async with stdio_client(params) as (read_stream, write_stream):
			async with ClientSession(read_stream, write_stream) as session:
				await session.initialize()
		        
				result = await session.call_tool(
				    name=tool_name,
				    arguments=arguments or {} )
				extracted_data = []

				for content in result.content:
					if hasattr(content,'text'):
						try:
							parsed = json.loads(content.text)
							extracted_data.append(parsed)
						except (json.JSONDecodeError,TypeError):
							extracted_data.append(content.text)
					else:
						extracted_data.append(content)


				if len(extracted_data) == 1:
					return extracted_data[0]
				else:
					return extracted_data

mcp_manager = MCPClientManager()

mcp_manager.register_server(
    name="gmail",
    script_path=BASE_DIR / "connectors" / "gmail_server.py"
)


					




