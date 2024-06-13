import argparse
import os
from langchain_qdrant import Qdrant
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
import openai
import streamlit as st
from streamlit_chat import message
from qdrant_client import QdrantClient

def run_chat_app(qdrant_collection_name):
    """Run the chat application using the Streamlit framework."""
    # Set the title for the Streamlit app
    st.title(f"{qdrant_collection_name} GPT")

    # Set the OpenAI API key from the environment variable
    openai.api_key = os.environ.get("OPENAI_API_KEY")

    # Create an instance of OpenAIEmbeddings
    embeddings = OpenAIEmbeddings()

    try:
        # Create an instance of Qdrant with the specified collection name
        client = QdrantClient(url=os.environ.get("QDRANT_URL"), api_key=os.environ.get("QDRANT_API_KEY"))
        db = Qdrant(client=client, collection_name=qdrant_collection_name, embeddings=embeddings)

        # Initialize the session state for generated responses and past inputs
        if "generated" not in st.session_state:
            st.session_state["generated"] = ["I am ready to help you"]

        if "past" not in st.session_state:
            st.session_state["past"] = ["Hello"]

        # Get the user's input from the text input field
        user_input = get_text()

        # If there is user input, search for a response using the search_db function
        if user_input:
            output = search_db(db, user_input)
            st.session_state.past.append(user_input)
            st.session_state.generated.append(output)

        # If there are generated responses, display the conversation using Streamlit messages
        if st.session_state["generated"]:
            for i in range(len(st.session_state["generated"])):
                message(st.session_state["past"][i], is_user=True, key=str(i) + "_user")
                message(st.session_state["generated"][i], key=str(i))
    except Exception as e:
        st.error(f"Error occurred while connecting to Qdrant: {e}")

def generate_response(prompt):
    """
    Generate a response using OpenAI's ChatCompletion API and the specified prompt.
    """
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}]
    )
    response = completion.choices[0].message.content
    return response

def get_text():
    """Create a Streamlit input field and return the user's input."""
    input_text = st.text_input("", key="input")
    return input_text

def search_db(db, query):
    """Search for a response to the query in the Qdrant database."""
    # Create a retriever from the Qdrant instance
    retriever = db.as_retriever()
    # Set the search parameters for the retriever
    retriever.search_kwargs["k"] = 10
    # Create a ChatOpenAI model instance
    model = ChatOpenAI(model="gpt-3.5-turbo")
    # Create a RetrievalQA instance from the model and retriever
    qa = RetrievalQA.from_llm(model, retriever=retriever)
    # Return the result of the query
    return qa.invoke(query)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--qdrant_collection_name", type=str, required=True)
    args = parser.parse_args()

    run_chat_app(args.qdrant_collection_name)
