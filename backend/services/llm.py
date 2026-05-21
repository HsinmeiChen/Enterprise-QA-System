import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def answer_with_context(question: str, context: str) -> str:
    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a document question-answering assistant. "
                    "Answer ONLY based on the provided context. "
                    "Do not make up information. "
                    "First understand the context, then answer in your own words. "
                    "Avoid copying long sentences directly from the context unless a technical term is necessary. "
                    "Keep the answer concise, clear, and natural."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Context:\n{context}\n\n"
                    f"Question:\n{question}\n\n"
                    "Instructions:\n"
                    "1. Answer only from the context.\n"
                    "2. Paraphrase instead of copying.\n"
                    "3. If the context is insufficient, say so clearly.\n"
                    "4. Give a short, direct answer first, then add 1-2 sentences of explanation if needed.\n\n"
                    "Answer:"
                ),
            },
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()
