import httpx
import json
from config import logger

class PCIMCPClient:
    def __init__(self):
        self.url = "https://www.pciconcursos.com.br/mcp"
        self.client = httpx.AsyncClient()
        self.initialized = False
        self._next_id = 1

    async def _request(self, method: str, params: dict = None):
        if params is None:
            params = {}
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": method,
            "params": params
        }
        self._next_id += 1
        
        try:
            response = await self.client.post(self.url, json=payload, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                logger.error(f"MCP API Error ({method}): {data['error']}")
                return None
            return data.get("result")
        except Exception as e:
            logger.error(f"Failed to call MCP {method}: {e}")
            return None

    async def initialize(self):
        if self.initialized:
            return
        res = await self._request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "telegram-bot", "version": "1.0"}
        })
        if res:
            self.instructions = res.get("instructions", "")
            self.initialized = True
            return self.instructions
        return ""

    async def list_tools(self):
        await self.initialize()
        res = await self._request("tools/list")
        if res and "tools" in res:
            return res["tools"]
        return []

    async def call_tool(self, name: str, arguments: dict):
        await self.initialize()
        res = await self._request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        if res and "content" in res:
            # Usually content is a list of text objects
            texts = [item.get("text", "") for item in res["content"] if item.get("type") == "text"]
            return "\n".join(texts)
        return "Nenhum resultado retornado ou erro na ferramenta."

pci_mcp_client = PCIMCPClient()
