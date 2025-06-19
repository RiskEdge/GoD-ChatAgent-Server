from fastapi import WebSocket
from langchain.callbacks.base import AsyncCallbackHandler

# from typing import List
from typing import List, Dict, Any, Optional
from uuid import UUID

class ConnectionManager:
    """Class defining socket events"""
    def __init__(self):
        """init method, keeping track of connections."""
        self.active_connections = []
        
    async def connect(self, websocket: WebSocket):
        """connect event"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
    async def send_message(self, message: str, websocket: WebSocket):
        """send message event"""
        await websocket.send_text(message)
        
    async def receive_message(self, websocket: WebSocket):
        """receive message event"""
        return await websocket.receive_text()
        
    def disconnect(self, websocket: WebSocket):
        """disconnect event"""
        self.active_connections.remove(websocket)
        
class WebSocketCallbackHandler(AsyncCallbackHandler):
    def __init__(self, websocket: WebSocket, manager: ConnectionManager):
        self.websocket = websocket
        self.manager = manager
        
    async def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[Any]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        # Optional: Send a message to the client indicating the start of processing
        # await self.manager.send_message("Chat model processing started.", self.websocket)
        return None
    
    async def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        # Optional: Send a message to the client indicating the start of processing
        # await self.manager.send_message("Chat model processing started.", self.websocket)
        return None
        
    async def on_llm_new_token(self, token: str, **kwargs):
        """Send each new token to the client"""
        await self.manager.send_message(token, self.websocket)
        
    async def on_llm_end(self, reponse, **kwargs):
        """Signal the end of response."""
        await self.manager.send_message("[END]", self.websocket)