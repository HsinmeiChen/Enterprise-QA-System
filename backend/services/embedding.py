import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def embed_text(text: str) -> list[float]:
    """
    Returns embedding vector for a given text.
    """
    text = (text or "").strip()
    if not text:
        return []

    model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    resp = client.embeddings.create(
        model=model,
        input=text
    )
    return resp.data[0].embedding