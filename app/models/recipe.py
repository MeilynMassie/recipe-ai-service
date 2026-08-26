from pydantic import BaseModel
from typing import Optional


class Ingredient(BaseModel):
    quantity: Optional[str] = None
    unit: Optional[str] = None
    name: str


class Recipe(BaseModel):
    name: str
    description: Optional[str] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    servings: Optional[str] = None
    ingredients: list[Ingredient]
    instructions: list[str]