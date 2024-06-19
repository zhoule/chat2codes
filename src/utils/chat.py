import argparse
import os
import json
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
    st.title(f"{qdrant_collection_name} GPT")

    openai.api_key = os.environ.get("OPENAI_API_KEY")

    embeddings = OpenAIEmbeddings()

    try:
        client = QdrantClient(url=os.environ.get("QDRANT_URL"), api_key=os.environ.get("QDRANT_API_KEY"))
        db = Qdrant(client=client, collection_name=qdrant_collection_name, embeddings=embeddings)

        if "generated" not in st.session_state:
            st.session_state["generated"] = ["I am ready to help you"]

        if "past" not in st.session_state:
            st.session_state["past"] = ["Hello"]

        # 使用非空的 label 并隐藏它
        user_input = st.text_input(" ", key="user_input", label_visibility="collapsed")

        if user_input:
            output = search_db(db, user_input)
            st.session_state.past.append(user_input)
            st.session_state.generated.append(output)

        # 确保消息显示逻辑正确
        if st.session_state["generated"]:
            for i in range(len(st.session_state["generated"])):
                message(st.session_state["past"][i], is_user=True, key=str(i) + "_user")
                
                # 提取 result 字段内容
                if isinstance(st.session_state["generated"][i], dict):
                    result_content = st.session_state["generated"][i].get('result', '')
                    # 显示 result 内容并支持代码高亮
                    st.code(result_content, language='java')
                else:
                    # 正常输出非字典类型的消息
                    message(st.session_state["generated"][i], key=str(i))
    except Exception as e:
        st.error(f"Error occurred while connecting to Qdrant: {e}")

def search_db(db, query):
    """Search for a response to the query in the Qdrant database."""
    retriever = db.as_retriever()
    retriever.search_kwargs["k"] = 10
    model = ChatOpenAI(model="gpt-3.5-turbo")
    qa = RetrievalQA.from_llm(model, retriever=retriever)
    return qa.invoke(query)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--qdrant_collection_name", type=str, required=True)
    args = parser.parse_args()

    run_chat_app(args.qdrant_collection_name)