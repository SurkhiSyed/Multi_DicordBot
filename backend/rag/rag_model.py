import argparse
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_huggingface import HuggingFaceEndpoint
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma")

PROMPT_TEMPLATE = """
On the topic of AI-Hypothesis-Writer Product I've been working on. We're at a bottleneck where we need some form of credibility for the hypothesis our AI generates, since any PM can go on ChatGPT with a bunch of tickets - the right prompts and get hypothesis generated for them.

Basically, we want a RAG process - where our AI gets inspiration from any credible solution library or database or repo for feature improvement/request type tickets.

TASK 1 - Cluster & Classification

STEP 1 — Role & Task

You are an AI Product Analyst assisting in product decision-making by transforming raw customer support tickets into actionable, ranked A/B test hypotheses, backed by open web research.

STEP 2 — Workflow Instructions

For each support ticket (row in Excel):

1. Cluster Similar Issues (only if ≥99% confidence):

·       If you are at least 99% certain that issues in the ticket belong to a known cluster, return the cluster name and proceed with the steps below based on the cluster.

·       If no clear cluster is detected, skip clustering and move to Step 2.

2. Classify the Ticket Type

Choose one from: Bug or Feature improvement.

3. Extract Key Elements

·       Customer Problem: Write clearly and specifically.

4.     Likely Root Cause: Only include if ≥99% confident.

·       Only include this if you are at least 99% confident in the root cause.

5. Summarize the User’s Goal or Desired Outcome

·       What does the user ultimately want to achieve or resolve?

Use the output of Task one as part of the import for task 2

"""


def run_rag(query_text):
    embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    results = db.similarity_search_with_relevance_scores(query_text, k=5)
    if len(results) == 0:
        return {
            "response": "Unable to find matching results.",
            "matches": [],
            "context": "",
            "sources": []
        }
    normalized_results = [
        {
            "content": doc.page_content,
            "score": (score + 1) / 2,
            "metadata": doc.metadata
        }
        for doc, score in results
    ]
    # Only include chunks with normalized score above 0.5 for context
    context_text = "\n\n---\n\n".join(
        [item["content"] for item in normalized_results if item["score"] > 0.3]
    )
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-latest",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    response = llm.invoke(prompt)
    # If response is an object, extract fields
    answer = getattr(response, "content", None) or str(response)
    # If you want to include metadata, extract them as well
    response_metadata = getattr(response, "response_metadata", None)
    additional_kwargs = getattr(response, "additional_kwargs", None)
    response_id = getattr(response, "id", None)
    usage_metadata = getattr(response, "usage_metadata", None)

    sources = [item["metadata"].get("source", None) for item in normalized_results]
    return {
        "response": answer,
        "sources": sources,
        "response_metadata": response_metadata,
        "additional_kwargs": additional_kwargs,
        "id": response_id,
        "usage_metadata": usage_metadata
    }

def main():
    # Create CLI.
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    args = parser.parse_args()
    query_text = args.query_text

    # Prepare the DB.
    embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")  # or your preferred model
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

    # Search the DB.
    results = db.similarity_search_with_relevance_scores(query_text, k=3)
    if len(results) == 0:
        print("Unable to find matching results.")
        return

    # Normalize scores for HuggingFace
    normalized_results = [(doc, (score + 1) / 2) for doc, score in results]
    for doc, score in normalized_results:
        print(f"Score: {score:.2f} | Content: {doc.page_content[:200]}")

    # Use a lower threshold, or just show the top result
    top_doc, top_score = normalized_results[0]
    if top_score < 0.2:
        print("Top result is not very relevant, but here it is:")
    #print(top_doc.page_content)

    # Only include chunks with normalized score above 0.3
    context_text = "\n\n---\n\n".join([doc.page_content for doc, score in normalized_results if score > 0.5])
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)
    print("Prompt to LLM:\n", prompt)

    # If you have a local LLM, you can use it here. Otherwise, just print the prompt.
    # Example with HuggingFaceHub (requires API key and setup):
    model_id = "bigscience/bloomz-560m"
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-latest",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    response = llm.invoke(prompt)
    print("Response:", response)

    # If you want to use OpenAI, you can still use ChatOpenAI here (but it's not free).
    # Otherwise, just print the prompt for now.

    sources = [doc.metadata.get("source", None) for doc, _score in results]
    formatted_response = f"Sources: {sources}"
    print(formatted_response)

    #print("Number of documents in DB:", db._collection.count())
    #docs = db.similarity_search("the", k=3)
    #print("Sample docs for query 'the':")
    '''
    for i, doc in enumerate(docs):
        print(f"Doc {i+1}: {doc.page_content[:200]}...")
        print(f"Metadata: {doc.metadata}")
    '''

if __name__ == "__main__":
    main()
