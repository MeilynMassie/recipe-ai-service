from pydantic import BaseModel
from typing import Optional


class Ingredient(BaseModel):
    quantity: Optional[str] = None
    unit: Optional[str] = None
    name: str
    section: Optional[str] = None


class Instruction(BaseModel):
    step_number: int
    description: str


class Source(BaseModel):
    publisher: str
    url: str


class Recipe(BaseModel):
    name: str
    # desciption: Optional[str] = None
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None
    servings: Optional[int] = None
    ingredients: list[Ingredient]
    instructions: list[Instruction]
    source: Optional[Source] = None