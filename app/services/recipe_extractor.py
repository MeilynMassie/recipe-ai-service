# OVERVIEW: Takes an image upload and extracts necessary info for recipe

from ollama import chat

response = chat(
    model="gemma3:4b",
    messages=[
        {
            "role": "user",
            "content": "Describe the recipe in this image.",
            "images": ["../../recipe.jpg"]
        }
    ]
)

print(response.message.content)