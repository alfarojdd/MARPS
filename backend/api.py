import os
from typing import Literal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import ollama
from pydantic import BaseModel

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = "jezero-extractor"
client = ollama.Client(host=OLLAMA_HOST)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class JezeroMissionRequirements(BaseModel):
  human: bool
  origin: str | None
  destination: str | None
  power: bool
  route_preference: Literal["shortest", "fastest"] | None


class PromptRequest(BaseModel):
  prompt: str


@app.post("/parse-mission", response_model=JezeroMissionRequirements)
def parse_endpoint(req: PromptRequest):
  response = client.chat(
      model=MODEL_NAME,
      messages=[{"role": "user", "content": req.prompt}],
      format=JezeroMissionRequirements.model_json_schema(),
  )
  return JezeroMissionRequirements.model_validate_json(response.message.content)