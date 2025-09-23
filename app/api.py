from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
from search_online import answer_user_query


app = FastAPI(title="GenAI Security Policy Assistant")

# Request model
class QueryRequest(BaseModel):
    question: str
    policy_id: Optional[str] = None  # Optional, if you want to filter internal DB

# Response model
class QueryResponse(BaseModel):
    answer: str
    internal_policies: str
    web_reference: str
    standard: str

# API endpoint
@app.post("/query", response_model=QueryResponse)
def query_policy(req: QueryRequest):
    if not req.question:
        raise HTTPException(status_code=400, detail="Question is required.")
    
    result = answer_user_query(req.question)
    
    return QueryResponse(
        answer=result["answer"],
        internal_policies=result["internal_policies"],
        web_reference=result["web_reference"],
        standard=result["standard"]
    )

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
