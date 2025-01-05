from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from dictionary_db import DictionaryDB
from test_indobert import translate_text, detect_context

app = FastAPI(
    title="HumanizeIndo API",
    description="API for making Indonesian text more human-like and conversational",
    version="1.0.0"
)

class HumanizeRequest(BaseModel):
    text: str = Field(..., description="The formal Indonesian text to be humanized")
    style: Optional[str] = Field(
        None, 
        description="The desired style: 'casual' (friendly, informal) or 'personal' (polite, semi-formal). If not specified, will be auto-detected."
    )
    preserve_case: Optional[bool] = Field(
        False,
        description="Whether to preserve the original text casing"
    )

class HumanizeResponse(BaseModel):
    original_text: str = Field(..., description="The original input text")
    humanized_text: str = Field(..., description="The humanized version of the text")
    detected_style: str = Field(..., description="The detected or forced style used")
    word_changes: List[dict] = Field(
        ..., 
        description="List of significant word transformations applied"
    )

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    app.state.db = DictionaryDB()
    if not app.state.db.connect():
        raise Exception("Failed to connect to MongoDB database")

@app.get("/")
async def root():
    """API root endpoint with basic information"""
    return {
        "name": "HumanizeIndo API",
        "version": "1.0.0",
        "description": "Make Indonesian text more human-like and conversational",
        "endpoints": {
            "/humanize": "POST - Convert formal text to human-like text",
            "/detect-style": "GET - Detect the style of a text",
            "/docs": "GET - API documentation"
        }
    }

@app.post("/humanize", response_model=HumanizeResponse)
async def humanize(request: HumanizeRequest):
    """
    Convert formal Indonesian text to a more human-like, conversational form.
    
    - Detects or uses specified style (casual/personal)
    - Applies appropriate word transformations
    - Maintains natural flow and context
    """
    try:
        # Get style (either specified or detected)
        style = request.style if request.style else detect_context(request.text, app.state.db)
        
        # Track word changes for transparency
        original_words = request.text.split()
        
        # Translate/humanize the text
        humanized = translate_text(request.text, app.state.db)
        humanized_words = humanized.split()
        
        # Track significant word changes
        word_changes = []
        for orig, human in zip(original_words, humanized_words):
            if orig.lower() != human.lower():
                word_changes.append({
                    "original": orig,
                    "humanized": human,
                    "position": len(word_changes)
                })
        
        return HumanizeResponse(
            original_text=request.text,
            humanized_text=humanized,
            detected_style=style,
            word_changes=word_changes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/detect-style")
async def detect_style(text: str):
    """
    Detect whether the text is casual, personal, or formal in style.
    """
    try:
        style = detect_context(text, app.state.db)
        return {
            "text": text,
            "detected_style": style,
            "confidence": "high" if len(text.split()) > 5 else "medium"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 