""" OVERVIEW:
Step 1: Retrieve webapage from url
Step 2: Parse data to minimize the amount sent to ollama
Step 3: Ollama converts data into Recipe model
"""
import json
import time
import requests
from bs4 import BeautifulSoup
from ollama import chat

from app.model.recipe import Recipe


# TODO: Fix how this reacts based on status code returned, add other reasons it could fail 
# TODO: Look into why ollama is so slow, range =[25,45] secs even with the data parsed to the minimum
# Step 1 - Turn webpage into text or json
def extract_recipe_from_url(url: str): 
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/139.0.0.0 Safari/537.36"
        )
    }
    
    response = requests.get(url, headers=headers)

    if response.status_code == 403:
        return {"error": f"Access denied: {url}"}

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    recipe_data = extract_recipe_from_json_ld(soup)
    print(recipe_data)
    
    return model_recipe(recipe_data) if recipe_data is not None else parse_data(soup)


# Step 2 - Parsing
def extract_recipe_from_json_ld(soup):
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)

            if not isinstance(data, list):
                data = [data]

            for item in data:
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
    print("Needs to be parsed.....")
    return None


# TODO: Optimize prompt (ex: To return less nulls, the data is there, it just isn't reading it correctly)
# Step 3 - Return Recipe Model 
def model_recipe(parsed_data):
    print("\nOllama's Output:")
    start = time.time()
    response = chat(
        model="gemma3:4b",
        messages=[
            {
                "role": "user",
                "content": f"""
                    Extract the recipe information from this webpage and return it using the provided schema.

                    IMPORTANT:
                    - Extract the recipe name exactly as written.
                    - Extract prep time from the recipe metadata.
                    - Extract cook time from the recipe metadata.
                    - Extract servings from the recipe metadata.
                    - Do not calculate or guess prep time, cook time, or servings.
                    - If a value is not available, return null.
                    - Keep ingredients separate even when the same ingredient appears multiple times.
                    - Assign each ingredient to the section where it is used.
                    - Rewrite instructions into concise, clear steps.
                    - Do not copy promotional text, personal stories, or unrelated webpage content.

                    Webpage:
                    {parsed_data}
                """
            }
        ],
        format=Recipe.model_json_schema()
    )
    print(f"Ollama took: {time.time() - start:.2f} seconds\n\n")
    return Recipe.model_validate_json(response.message.content)


# Tests
urls = [
        # 'https://www.allrecipes.com/recipe/15681/squash-casserole-with-cream-of-chicken-soup/',
        'https://therecipecritic.com/white-chicken-enchiladas/'
        # 'https://www.allrecipes.com/recipe/228210/the-best-caramel-apples/',
        # 'https://whiskwhiskers.com/2021/06/01/impossible-beef-and-scallion-dumplings/#recipe',
        # 'https://www.muydelish.com/traditional-mexican-horchata/#recipe',
        # 'https://www.jessicagavin.com/crispy-vegetable-tofu-dumplings/#wprm-recipe-container-36555'
    ]

for url in urls: 
    print('\nNew Recipe Alert!')
    result = extract_recipe_from_url(url)
    print(result)
    