# OVERVIEW: Takes an image upload and extracts necessary info for recipe

from ollama import chat

img_base_path = "../static/img/recipe"

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