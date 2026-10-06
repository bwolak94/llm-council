"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio

from . import storage
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage1_stream_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings
from .config import get_council_models, get_chairman_model, set_council_models, set_chairman_model, AVAILABLE_MODELS
from .openrouter import query_model

app = FastAPI(title="LLM Council API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str
    criteria: Optional[List[str]] = None


class UpdateConfigRequest(BaseModel):
    """Request to update runtime council configuration."""
    council_models: List[str]
    chairman_model: str


class RetryModelRequest(BaseModel):
    """Request to retry a single failed model from Stage 1."""
    model: str


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/config")
async def get_config():
    """Get current council configuration."""
    return {
        "council_models": get_council_models(),
        "chairman_model": get_chairman_model(),
        "available_models": AVAILABLE_MODELS,
    }


@app.put("/api/config")
async def update_config(request: UpdateConfigRequest):
    """Update council configuration at runtime."""
    if len(request.council_models) < 2:
        raise HTTPException(status_code=400, detail="At least 2 council models required")
    set_council_models(request.council_models)
    set_chairman_model(request.chairman_model)
    return {
        "council_models": request.council_models,
        "chairman_model": request.chairman_model,
    }


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Run the 3-stage council process
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content,
        request.criteria
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result,
        metadata.get("aggregate_rankings")
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            # Add user message
            storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Stream individual model responses as they arrive
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = []
            failed_models = []
            async for event in stage1_stream_responses(request.content):
                if event["type"] == "model_complete":
                    stage1_results.append(event["data"])
                    yield f"data: {json.dumps({'type': 'stage1_model_complete', 'data': event['data']})}\n\n"
                else:
                    failed_models.append(event["model"])
            yield f"data: {json.dumps({'type': 'stage1_complete', 'failed_models': failed_models})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results, request.criteria)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(request.content, stage1_results, stage2_results)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result,
                aggregate_rankings
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/analytics")
async def get_analytics():
    """
    Aggregate ranking data across all conversations for performance analytics.
    Only counts messages that have persisted aggregate_rankings.
    """
    conversations = storage.list_conversations()

    model_data: Dict[str, Dict[str, Any]] = {}

    for conv_meta in conversations:
        conv = storage.get_conversation(conv_meta["id"])
        if conv is None:
            continue
        for msg in conv["messages"]:
            if msg.get("role") != "assistant":
                continue
            rankings = msg.get("aggregate_rankings")
            if not rankings:
                continue
            # The first entry in aggregate_rankings is the winner for this conversation
            winner = rankings[0]["model"] if rankings else None
            for entry in rankings:
                model = entry["model"]
                if model not in model_data:
                    model_data[model] = {
                        "appearances": 0,
                        "rank_sum": 0.0,
                        "wins": 0,
                    }
                model_data[model]["appearances"] += 1
                model_data[model]["rank_sum"] += entry["average_rank"]
                if model == winner:
                    model_data[model]["wins"] += 1

    result = []
    for model, data in model_data.items():
        n = data["appearances"]
        result.append({
            "model": model,
            "appearances": n,
            "average_rank": round(data["rank_sum"] / n, 2),
            "wins": data["wins"],
            "win_rate": round(data["wins"] / n, 2),
        })

    result.sort(key=lambda x: x["average_rank"])

    return {
        "models": result,
        "total_conversations": len(conversations),
    }


@app.post("/api/conversations/{conversation_id}/retry-model")
async def retry_model(conversation_id: str, request: RetryModelRequest):
    """
    Retry a single failed model from Stage 1.
    Returns the model's response without re-running the full council process.
    """
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Find the last user message to know what to ask
    user_messages = [m for m in conversation["messages"] if m["role"] == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message found in conversation")

    user_query = user_messages[-1]["content"]
    messages = [{"role": "user", "content": user_query}]

    response = await query_model(request.model, messages)
    if response is None:
        raise HTTPException(status_code=502, detail=f"Model {request.model} failed to respond")

    return {
        "model": request.model,
        "response": response.get('content', ''),
        "usage": response.get('usage'),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
