""" OVERVIEW:
Takes an image upload and extracts necessary info for recipe
"""
from ollama import chat

# TODO: Fix the whole shabang
# def extract_recipe_from_image(url: str) -> str:
def extract_recipe_from_image():
    img_base_path = "app/static/img/recipe"

    response = chat(
        model="gemma3:4b",
        messages=[
            {
                "role": "user",
                "content": "Describe the recipe in these images. Include how many images you read at the end.",
                "images": [f"{img_base_path}/recipe.jpg", f"{img_base_path}/recipe2.jpg"],
            }
        ]
    )

    print(response.message.content)


extract_recipe_from_image()