from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv
from pathlib import Path
import os
from ingest import load_documents_from_folder, chunk_text
from langchain_pinecone import PineconeVectorStore 
from langchain_openai import OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI

load_dotenv(override=True)

client = OpenAI()
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
pinecone_api_key = os.getenv("PINECONE_API_KEY")

pine = Pinecone(api_key=pinecone_api_key)
index = pine.Index("policies")

embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=512)
# Instantiate the Pinecone vector store (not the class itself)
vector_store = PineconeVectorStore(index_name="policies", embedding=embeddings,text_key="text")
retriever = vector_store.as_retriever(search_kwargs={"k": 5})

def embed_query(query: str):
    """Generate embedding vector for the query string."""
    response = client.embeddings.create(
        input=query,
        model="text-embedding-3-small", dimensions=512
    )
    return response.data[0].embedding

def retrieve_context(question: str, top_k: int = 5):
    """Retrieve top_k relevant chunks from Pinecone for the given question."""
    query_vec = embed_query(question)
    results = index.query(vector=query_vec, top_k=top_k, include_metadata=True)
    
    # Extract text chunks + metadata
    contexts = []
    for match in results["matches"]:
        contexts.append({
            "id": match["id"],
            "score": match["score"],
            "source": match["metadata"].get("source"),
            "text": match["metadata"].get("text")
        })
    return contexts


def ingest_document(docPath: str):
    documents = load_documents_from_folder(docPath)
    
    for name, content in documents.items():
        chunks = chunk_text(content) 
        # Create embeddings for all chunks in one call
        resp = client.embeddings.create(
            input=chunks,
            model="text-embedding-3-small",
            dimensions=512,
        )

        vectors = []
        for i, (chunk, d) in enumerate(zip(chunks, resp.data)):
            emb = d.embedding
            chunk_id = f"{Path(name).stem}_chunk_{i}"
            vectors.append((chunk_id, emb, {"source": name, "chunk": i, "text": chunk}))
           
            index.upsert(vectors=vectors)
        
def fetch_internal_policies(user_query: str) -> str:
    docs_result = retriever.get_relevant_documents(user_query)  # OLD method works for now

    # OR if you must use new API:
    # docs_result = retriever.invoke({"query": user_query})
    # docs = docs_result.get("documents", docs_result)

    # Step 2: extract plain text
    internal_text = "\n".join([d.page_content for d in docs_result if d.page_content])
    return internal_text

if __name__ == "__main__":
    ingest_document("..\\input_policies")
