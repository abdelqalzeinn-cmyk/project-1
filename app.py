from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import cohere
import os
import logging
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Cohere client
try:
    cohere_api_key = os.getenv("COHERE_API_KEY")
    if not cohere_api_key:
        raise ValueError("COHERE_API_KEY environment variable not set")
    
    co = cohere.Client(api_key=cohere_api_key)
    logger.info("Cohere client initialized successfully")
    
except Exception as e:
    logger.error(f"Error initializing Cohere client: {str(e)}")
    co = None

# Create necessary directories
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
(static_dir / "js").mkdir(exist_ok=True)

# Initialize FastAPI
app = FastAPI()

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Explicitly expose all headers
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"Error serving root page: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Error loading the application"}
        )

@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify API is working"""
    return {
        "status": "Server is running",
        "model_loaded": co is not None
    }

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    if not co:
        raise HTTPException(
            status_code=500,
            detail="Cohere client not initialized. Please check the server logs."
        )
    
    # Initialize recent_history with an empty list to avoid UnboundLocalError
    recent_history = []
    
    try:
        data = await request.json()
        user_message = data.get("message", "").strip()
        history = data.get("history", [])
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Keep only the last 5 messages for context
        recent_history = history[-5:] if len(history) > 5 else history
        
        # Prepare the chat history in the correct format for Cohere
        formatted_history = [
            {"role": "USER" if msg["role"] == "user" else "CHATBOT", "message": msg.get("content", msg.get("message", ""))}
            for msg in recent_history
            if msg.get("role") in ["user", "assistant"]
        ]
        
        # Call Cohere's chat endpoint with the correct parameters
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    co.chat,
                    model="command-a-03-2025",  # Using the latest command model
                    message=user_message,
                    chat_history=formatted_history,
                    temperature=0.7,
                    max_tokens=1000
                ),
                timeout=15  # Reduced timeout to 15 seconds
            )
            
            # Extract the response text
            ai_response = response.text
            
            return {
                "response": ai_response,
                "history": recent_history + [
                    {"role": "user", "message": user_message},
                    {"role": "assistant", "message": ai_response}
                ][-5:]  # Keep the history limited to 5 exchanges
            }
            
        except asyncio.TimeoutError:
            logger.error("Request to Cohere API timed out")
            return {
                "response": "I'm sorry, the AI service is taking too long to respond. Please try again in a moment.",
                "history": recent_history
            }
            
    except HTTPException as http_exc:
        logger.error(f"HTTP Exception: {str(http_exc)}")
        return {
            "response": f"Error: {http_exc.detail}",
            "history": recent_history
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "response": "I'm having trouble connecting to the AI service. Please try again later.",
            "history": recent_history
        }

# Only run this if the file is executed directly (not imported)
if __name__ == "__main__":
    import uvicorn
    # Get port from environment variable or default to 8001
    port = int(os.getenv("PORT", 8001))
    # Run the server
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )