# OVERVIEW: FASTAPI Stuff
from fastapi import FastAPI
from pydantic import BaseModel

from app.service.url_recipe_extractor import extract_recipe_from_url

app = FastAPI(title="Recipe AI Service")

class RecipeUrlRequest(BaseModel):
    url: str


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.post("/extract/url")
def extract_url(request: RecipeUrlRequest):
    print(f"URL: {request.url}")
    return extract_recipe_from_url(request.url)
