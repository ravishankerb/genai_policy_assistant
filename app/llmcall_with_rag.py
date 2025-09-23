
from openai import OpenAI
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
load_dotenv(override=True)

client = OpenAI()
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# def build_prompt(question: str, contexts: list):
#     """Format retrieved contexts into a prompt for the LLM."""
#     context_text = "\n\n".join(
#         [f"[{c['source']}] {c['text']}" for c in contexts]
#     )
#     return f"""
# You are a strict Security Policy Assistant.
# Use ONLY the provided sources. If unsure, say "I don't know".

# CONTEXT:
# {context_text}

# QUESTION: {question}

# Respond in JSON:
# {{
#  "answer": string,
#  "citations": [{{"source": string, "excerpt": string}}],
#  "recommendation": string
# }}
# """

# def query_llm(prompt: str):
#     """Send the RAG prompt to OpenAI LLM."""
#     response = client.chat.completions.create(
#         model="gpt-4o-mini",   # or gpt-4o
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0
#     )
#     return response.choices[0].message.content

def extract_reference_standard(user_query: str) -> str:
    prompt = PromptTemplate(
        input_variables=["question"],
        template="""Extract the reference standard, policy, or regulation mentioned in this question.
Return only the standard name, no extra words.

Question: {question}

Answer:"""
    )
    msg = HumanMessage(content=prompt.format(question=user_query))
    response = llm.invoke([msg])
    standard_name = response.content  
    #standard_name = llm.predict(prompt.format(question=user_query))
    return standard_name.strip()

