""" OVERVIEW:
Maps schema.org Recipe JSON-LD directly into the Recipe model, skipping
the Ollama call entirely for pages with complete, well-formed data.
"""
import re
from typing import Optional

from app.model.recipe import Ingredient, Instruction, Recipe

_UNICODE_FRACTIONS = {
    "¼": "1/4", "½": "1/2", "¾": "3/4", "⅓": "1/3", "⅔": "2/3",
    "⅛": "1/8", "⅜": "3/8", "⅝": "5/8", "⅞": "7/8",
}

_UNITS = {
    "cup", "cups", "tablespoon", "tablespoons", "tbsp", "teaspoon", "teaspoons", "tsp",
    "ounce", "ounces", "oz", "pound", "pounds", "lb", "lbs", "gram", "grams", "g",
    "kilogram", "kilograms", "kg", "milliliter", "milliliters", "ml", "liter", "liters", "l",
    "clove", "cloves", "can", "cans", "package", "packages", "pinch", "pinches", "dash",
    "slice", "slices", "stick", "sticks", "quart", "quarts", "pint", "pints", "gallon", "gallons",
}

_QUANTITY_RE = re.compile(r"^\s*(\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?)\s*")
_UNIT_RE = re.compile(r"^([A-Za-z.]+)\b\.?")
_DURATION_RE = re.compile(r"^P(?:\d+D)?T(?:(\d+)H)?(?:(\d+)M)?$")
_DIGITS_RE = re.compile(r"\d+")


def _normalize_fractions(text: str) -> str:
    for symbol, replacement in _UNICODE_FRACTIONS.items():
        text = re.sub(rf"(\d)\s*{re.escape(symbol)}", rf"\1 {replacement}", text)
        text = text.replace(symbol, replacement)
    return text


def _parse_ingredient(raw: str) -> Ingredient:
    text = _normalize_fractions(raw.strip())

    quantity = None
    match = _QUANTITY_RE.match(text)
    if match:
        quantity = match.group(1).strip()
        text = text[match.end():].strip()

    unit = None
    unit_match = _UNIT_RE.match(text)
    if unit_match and unit_match.group(1).lower().rstrip(".") in _UNITS:
        unit = unit_match.group(1).rstrip(".")
        text = text[unit_match.end():].strip()

    # Whatever couldn't be confidently split (parenthetical sizes, prep notes,
    # "to taste", etc.) stays in the name rather than being discarded.
    name = text.strip(" ,") or raw.strip()
    return Ingredient(quantity=quantity, unit=unit, name=name)


def parse_duration_minutes(value) -> Optional[int]:
    """Parse an ISO 8601 duration (e.g. "PT1H30M") into whole minutes."""
    if not isinstance(value, str):
        return None
    match = _DURATION_RE.match(value.strip())
    if not match:
        return None
    hours, minutes = match.groups()
    if hours is None and minutes is None:
        return None
    return int(hours or 0) * 60 + int(minutes or 0)


def parse_servings(value) -> Optional[int]:
    if isinstance(value, list):
        value = value[0] if value else None
    if not value:
        return None
    match = _DIGITS_RE.search(str(value))
    return int(match.group()) if match else None


def _flatten_instructions(value) -> list[str]:
    steps: list[str] = []

    def walk(node):
        if node is None:
            return
        if isinstance(node, str):
            text = node.strip()
            if text:
                steps.append(text)
        elif isinstance(node, dict):
            if "itemListElement" in node:
                for item in node["itemListElement"]:
                    walk(item)
            else:
                walk(node.get("text") or node.get("name"))
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(value)

    # Some sites put every step in a single HowToStep/string blob.
    if len(steps) == 1 and "\n" in steps[0]:
        steps = [line.strip() for line in steps[0].split("\n") if line.strip()]

    return steps


def map_json_ld_to_recipe(recipe_data: dict) -> Optional[Recipe]:
    """Best-effort direct mapping of JSON-LD recipe data to the Recipe model.
    Returns None when the data is too incomplete to trust, so the caller can
    fall back to the LLM path instead."""
    name = recipe_data.get("name")
    if not isinstance(name, str) or not name.strip():
        return None

    raw_ingredients = recipe_data.get("recipeIngredient") or []
    ingredients = [
        _parse_ingredient(item) for item in raw_ingredients if isinstance(item, str) and item.strip()
    ]
    if not ingredients:
        return None

    instruction_steps = _flatten_instructions(recipe_data.get("recipeInstructions"))
    if not instruction_steps:
        return None
    instructions = [
        Instruction(step_number=i + 1, description=step)
        for i, step in enumerate(instruction_steps)
    ]

    return Recipe(
        name=name.strip(),
        prep_time=parse_duration_minutes(recipe_data.get("prepTime")),
        cook_time=parse_duration_minutes(recipe_data.get("cookTime")),
        servings=parse_servings(recipe_data.get("recipeYield")),
        ingredients=ingredients,
        instructions=instructions,
        source=None,
    )
