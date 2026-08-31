import requests
from bs4 import BeautifulSoup
from ollama import chat

from app.model.recipe import Recipe


def extract_text_from_url(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/139.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    return soup.get_text(" ", strip=True)


def extract_recipe_with_llm(text: str):
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
                    {text}
                """
            }
        ],
        format=Recipe.model_json_schema()
    )

    recipe = Recipe.model_validate_json(response.message.content)

    print(recipe)


url = "https://therecipecritic.com/white-chicken-enchiladas/"

text = extract_text_from_url(url)

recipe = extract_recipe_with_llm(text)

print(recipe)