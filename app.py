# importing dependencies

import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import faiss
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from htmlTemplates import css, bot_template, user_template
from langchain.embeddings import OpenAIEmbeddings

openai_api_key=''

# creating custom template to guide llm model
custom_template = """Given the following conversation and a follow up question, 
rephrase the follow up question to be a standalone question.If you don't know the answer, just say that you don't know,
 don't try to make up an answer
Chat History:
{chat_history}
Follow Up Input: {question}
Standalone question:"""

CUSTOM_QUESTION_PROMPT = PromptTemplate.from_template(custom_template)


# extracting text from pdf
def get_pdf_text(docs):
    text=""
    for pdf in docs:
        pdf_reader=PdfReader(pdf)
        for page in pdf_reader.pages:
            text+=page.extract_text()
    return text


# converting text to chunks
def get_chunks(raw_text):
    text_splitter=CharacterTextSplitter(separator="\n",
                                        chunk_size=1000,
                                        chunk_overlap=200)   
    chunks=text_splitter.split_text(raw_text)
    return chunks



# using all-LLM embeddings model and faiss to get vectorstore
def get_vectorstore(chunks):
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    vectorstore=faiss.FAISS.from_texts(texts=chunks,embedding=embeddings)
    return vectorstore



# generating conversation chain  
def get_conversationchain(vectorstore):
    from langchain.chat_models import ChatOpenAI
    llm = ChatOpenAI(model_name='gpt-3.5-turbo',openai_api_key=openai_api_key,temperature=0.2)


    memory = ConversationBufferMemory(memory_key='chat_history', # using conversation buffer memory to hold past information
                                      return_messages=True,
                                      output_key='answer') 
    

    conversation_chain = ConversationalRetrievalChain.from_llm(
                                llm=llm,
                                retriever=vectorstore.as_retriever(),
                                condense_question_prompt=CUSTOM_QUESTION_PROMPT,
                                memory=memory)
    return conversation_chain



# generating response from user queries and displaying them accordingly
def handle_question(question):
    response = st.session_state.conversation({'question': question})
    st.session_state.chat_history = response["chat_history"]
    
    # Display the chat messages with most recent question and answer at the top
    for i in range(len(st.session_state.chat_history) - 1, -1, -2):
        answer_msg = st.session_state.chat_history[i]
        question_msg = st.session_state.chat_history[i - 1]
        
        # Display question
        st.write(user_template.replace("{{MSG}}", question_msg.content), unsafe_allow_html=True)
        
        # Display answer
        st.write(bot_template.replace("{{MSG}}", answer_msg.content), unsafe_allow_html=True)

       

def main():
    
    st.set_page_config(page_title="Chat with PDFs", page_icon=":books:")
    st.write(css, unsafe_allow_html=True)

    # Initialize conversation only once
    if "conversation" not in st.session_state or not callable(st.session_state.conversation):
        st.session_state.conversation = None

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None
    
    st.header("Chat with multiple PDFs :books:")
    
    # Display the question input box and handle the question
    question = st.text_input("Ask question from your document:")
    if st.button("Submit"):  # Process the question when the button is clicked
        handle_question(question)

    with st.sidebar:
        st.subheader("Your documents")
        docs = st.file_uploader("Upload your PDF here and click on 'Process'", accept_multiple_files=True)
        if st.button("Process"):
            with st.spinner("Processing"):
                # Get the pdf
                raw_text = get_pdf_text(docs)
                
                # Get the text chunks
                text_chunks = get_chunks(raw_text)
                
                # Create vectorstore
                vectorstore = get_vectorstore(text_chunks)
                
                # Create conversation chain
                st.session_state.conversation = get_conversationchain(vectorstore)


if __name__ == '__main__':
    main()