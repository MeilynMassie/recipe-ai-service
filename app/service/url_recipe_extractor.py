""" OVERVIEW:
Step 1: Retrieve webapage from url
Step 2: Parse data to minimize the amount sent to ollama
Step 3: Ollama converts data into Recipe model
"""
import json
import logging
import re
import time
from enum import Enum
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from ollama import chat

from app.model.recipe import Recipe, Source
from app.service.json_ld_mapper import map_json_ld_to_recipe, parse_duration_minutes, parse_servings

# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = (5, 15)
MAX_RETRIES = 2
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
BOT_CHALLENGE_MARKERS = (
    "just a moment",
    "verify you are human",
    "checking your browser",
    "enable javascript and cookies",
)


class ExtractionErrorType(str, Enum):
    BLOCKED = "blocked"
    NOT_FOUND = "not_found"
    UNREACHABLE = "unreachable"
    TIMEOUT = "timeout"
    HTTP_ERROR = "http_error"
    NO_RECIPE_DATA = "no_recipe_data"


class RecipeExtractionError(Exception):
    def __init__(self, error_type: ExtractionErrorType, message: str):
        self.error_type = error_type
        self.message = message
        super().__init__(message)


def _fetch(url: str, headers: dict) -> requests.Response:
    last_error = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.Timeout as e:
            last_error = RecipeExtractionError(ExtractionErrorType.TIMEOUT, f"Timed out fetching {url}")
        except requests.exceptions.ConnectionError as e:
            raise RecipeExtractionError(ExtractionErrorType.UNREACHABLE, f"Could not connect to {url}") from e
        except requests.exceptions.RequestException as e:
            raise RecipeExtractionError(ExtractionErrorType.HTTP_ERROR, f"Request to {url} failed: {e}") from e
        else:
            if response.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
                continue
            return response

        if attempt < MAX_RETRIES:
            time.sleep(2 ** attempt)

    raise last_error


def _build_source(url: str) -> Source:
    domain = urlparse(url).netloc
    if domain.startswith("www."):
        domain = domain[4:]
    return Source(publisher=domain or url, url=url)


# Step 1 - Turn webpage into text or json
def extract_recipe_from_url(url: str):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/139.0.0.0 Safari/537.36"
        )
    }

    response = _fetch(url, headers)

    if response.status_code == 403:
        raise RecipeExtractionError(ExtractionErrorType.BLOCKED, f"Access denied: {url}")
    if response.status_code == 404:
        raise RecipeExtractionError(ExtractionErrorType.NOT_FOUND, f"Page not found: {url}")

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise RecipeExtractionError(
            ExtractionErrorType.HTTP_ERROR, f"{url} returned status {response.status_code}"
        ) from e

    if any(marker in response.text[:2000].lower() for marker in BOT_CHALLENGE_MARKERS):
        raise RecipeExtractionError(ExtractionErrorType.BLOCKED, f"Bot-challenge page detected: {url}")

    soup = BeautifulSoup(response.text, "html.parser")
    recipe_data = extract_recipe_from_json_ld(soup)

    if recipe_data is not None:
        mapped = map_json_ld_to_recipe(recipe_data)
        recipe = mapped if mapped is not None else model_recipe(recipe_data)
    else:
        recipe = parse_data(soup)
        if recipe is None:
            raise RecipeExtractionError(ExtractionErrorType.NO_RECIPE_DATA, f"No recipe data found on {url}")

    recipe.source = _build_source(url)
    return recipe


# Step 2 - Parsing based on popular HTML structures such as JSON LD and @graph
def extract_recipe_from_json_ld(soup):
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)

            if not isinstance(data, list):
                data = [data]

            # Some sites (commonly via WordPress SEO plugins) wrap everything
            # in a top-level "@graph" array instead of a flat list.
            items = []
            for entry in data:
                if isinstance(entry, dict) and "@graph" in entry:
                    items.extend(entry["@graph"])
                else:
                    items.append(entry)

            for item in items:
                if not isinstance(item, dict):
                    continue
                recipe_type = item.get("@type", [])

                if isinstance(recipe_type, str):
                    recipe_type = [recipe_type]
            
                if "Recipe" in recipe_type:
                    return {
                        "name": item.get("name"),
                        "recipeIngredient": item.get("recipeIngredient"),
                        "recipeInstructions": item.get("recipeInstructions"),
                        "recipeYield": item.get("recipeYield"),
                        "prepTime": item.get("prepTime"),
                        "cookTime": item.get("cookTime"),
                    }
        except (json.JSONDecodeError, TypeError):
            continue
    return None


# TODO: Add logic to parse text
def parse_data(data):
    logger.info("No JSON-LD recipe found; raw-HTML parsing not yet implemented")
    return None


def _strip_html(value):
    """Recursively strip HTML tags/entities out of the JSON-LD fields we send
    to Ollama, so the model isn't spending tokens (and time) on markup."""
    if isinstance(value, str):
        text = BeautifulSoup(value, "html.parser").get_text(separator=" ")
        return re.sub(r"\s+", " ", text).strip()
    if isinstance(value, list):
        return [_strip_html(item) for item in value]
    if isinstance(value, dict):
        return {key: _strip_html(item) for key, item in value.items()}
    return value


# Step 3 - Return Recipe Model
def model_recipe(parsed_data):
    source_data = parsed_data if isinstance(parsed_data, dict) else {}
    prep_time = parse_duration_minutes(source_data.get("prepTime"))
    cook_time = parse_duration_minutes(source_data.get("cookTime"))
    servings = parse_servings(source_data.get("recipeYield"))

    parsed_data = _strip_html(parsed_data)
    logger.info("Calling Ollama to extract recipe")
    start = time.time()
    response = chat(
        model="gemma3:4b",
        keep_alive="30m",
        options={
            "num_ctx": 4096,
            "num_predict": 800,
            "temperature": 0,
        },
        messages=[
            {
                "role": "user",
                "content": f"""
                    Extract the recipe information from this webpage and return it using the provided schema.

                    IMPORTANT:
                    - Extract the recipe name exactly as written.
                    - Keep ingredients separate even when the same ingredient appears multiple times.
                    - Assign each ingredient to the section where it is used.
                    - Rewrite instructions into concise, clear steps.
                    - Do not copy promotional text, personal stories, or unrelated webpage content.
                    - Leave prep_time, cook_time, and servings as null; they are filled in separately.

                    Webpage:
                    {parsed_data}
                """
            }
        ],
        format=Recipe.model_json_schema()
    )
    logger.info(f"Ollama took {time.time() - start:.2f} seconds")
    recipe = Recipe.model_validate_json(response.message.content)

    if prep_time is not None:
        recipe.prep_time = prep_time
    if cook_time is not None:
        recipe.cook_time = cook_time
    if servings is not None:
        recipe.servings = servings

    return recipe


# Tests
if __name__ == "__main__":
    urls = [
        'https://www.allrecipes.com/recipe/15681/squash-casserole-with-cream-of-chicken-soup/',
        'https://therecipecritic.com/white-chicken-enchiladas/',
        'https://www.allrecipes.com/recipe/228210/the-best-caramel-apples/',
        # 'https://whiskwhiskers.com/2021/06/01/impossible-beef-and-scallion-dumplings/#recipe',
        # 'https://www.muydelish.com/traditional-mexican-horchata/#recipe', #BLOCKED 
        # 'https://www.jessicagavin.com/crispy-vegetable-tofu-dumplings/#wprm-recipe-container-36555'
    ]

    for url in urls:
        print('\nNew Recipe Alert!')
        result = extract_recipe_from_url(url)
        print(result)
    