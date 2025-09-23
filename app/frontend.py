import streamlit as st
from search_online import answer_user_query
# from your_module import answer_user_query

st.title("GenAI Security Policy Assistant")

question = st.text_input("Enter your question about company policies:")

if st.button("Ask"):
    if question.strip():
        with st.spinner("Checking policies..."):
            result = answer_user_query(question)
        
        st.subheader("Answer:")
        st.write(result["answer"])
        
        st.subheader("Internal Policies Used:")
        st.write(result["internal_policies"])
        
        st.subheader("Web Reference Text:")
        st.write(result["web_reference"])
        
        st.subheader("Standard Extracted:")
        st.write(result["standard"])
    else:
        st.warning("Please enter a question!")
