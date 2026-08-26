# recipe-ai-service

## Description
Recipe AI Service is a Python-based service that uses a vision-capable LLM to extract structured recipe information from uploaded images. It provides the AI functionality for the main Recipe API.

WebApp: [Recipe API](https://github.com/MeilynMassie/recipe-api)

## General Workflow
recipe.jpg -> Python script -> Vision LLM -> Recipe JSON

## TO-DO List
    - Upload recipe image
    - Extract recipe information using a vision LLM
    - Return structured recipe data
    - Validate extracted recipe data
    - Expose recipe extraction through a FastAPI endpoint
    - Handle extraction errors

## Later Me Problems
    - OCR fallback
    - Handwritten recipe support
    - Multiple image support
    - AI confidence scoring
    - Additional AI features
    - Agentic AI


### Example of Expected JSON Output
```
{
  "name": "Chocolate Chip Cookies",
  "ingredients": [
    {
      "quantity": 2,
      "unit": "cups",
      "name": "flour"
    }
  ],
  "instructions": [
    "Mix ingredients.",
    "Bake at 350°F for 10 minutes."
  ]
}
```