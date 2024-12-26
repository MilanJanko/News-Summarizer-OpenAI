from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.environ.get("OPENAI_API_KEY")

client = OpenAI(
    api_key=api_key,
    organization="org-khIrQu0W6wbUnghDbHaxKxMP",
    base_url="https://api.openai.com/v1/",
    project="proj_tMibWzC7EdboeC6EJHKKosx1",
    timeout=30
)
try:
    response = client.chat.completions.create(
        model="gpt-4",  # Specify the model
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! How can you help me?"}
        ]
    )
    print("Response:", response.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")