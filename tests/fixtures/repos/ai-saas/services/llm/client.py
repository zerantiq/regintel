from openai import OpenAI

client = OpenAI()


def summarize_customer(email: str, request_text: str) -> str:
    return client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": f"{email}: {request_text}"}],
    ).choices[0].message.content
