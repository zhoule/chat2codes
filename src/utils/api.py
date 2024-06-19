# api.py

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import time
from langchain_qdrant import Qdrant
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
import openai
from qdrant_client import QdrantClient
import asyncio
import json
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

# Load environment variables
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: list[Message]
    temperature: float = 1.0
    max_tokens: int = 1000

async def generate_streaming_response(db, messages):
    retriever = db.as_retriever()
    retriever.search_kwargs["k"] = 10
    model = ChatOpenAI(model="gpt-4o")
    qa = RetrievalQA.from_llm(model, retriever=retriever)

    # Extract the last user message and use previous messages as context
    last_user_message = None
    context = ""
    for message in messages:
        if message.role == "user":
            last_user_message = message.content
        context += f"{message.role}: {message.content}\n"

    if last_user_message is None:
        raise HTTPException(status_code=400, detail="No user message found in the request")

    # Add a prompt to instruct the model to respond in Chinese
    prompt = f"{context}\n助手，请用中文回答以下问题：\n{last_user_message}"

    # Execute the query and start streaming results
    print(prompt)
    result = qa.invoke(prompt)
    
    # Simulate streaming response
    for chunk in result['result']:
        data = {
            "choices": [
                {
                    "delta": {"role": "assistant", "content": chunk},
                    "finish_reason": None,
                    "index": 0
                }
            ],
            "created": int(time.time()),
            "id": "chatcmpl-123",
            "model": "gpt-4o",
            "object": "chat.completion.chunk"
        }
        yield f"data: {json.dumps(data)}\n\n"
        await asyncio.sleep(0.1)  # Simulate delay between chunks

@app.post("/v1/chat/completions")
async def chat(request: ChatRequest):
    try:
        if not request.messages:
            raise HTTPException(status_code=400, detail="Messages list is empty")

        # Assuming the collection name is provided in the environment or hardcoded
        qdrant_collection_name = os.getenv("QDRANT_COLLECTION_NAME", "your-collection-name")

        embeddings = OpenAIEmbeddings()
        client = QdrantClient(url=os.environ.get("QDRANT_URL"), api_key=os.environ.get("QDRANT_API_KEY"))
        db = Qdrant(client=client, collection_name=qdrant_collection_name, embeddings=embeddings)

        return StreamingResponse(generate_streaming_response(db, request.messages), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
