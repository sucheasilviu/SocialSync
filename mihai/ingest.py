import os
import shutil
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

load_dotenv(dotenv_path="./.env")

DATA_PATH = "./data_raw"
DB_PATH = "./chroma_db"

def ingest_data():
    print("🔄 SOCIALSYNC: Ingesting Data (Smart Chunking)...")

    if os.path.exists(DB_PATH):
        shutil.rmtree(DB_PATH)

    loader = DirectoryLoader(DATA_PATH, glob="./*.txt", loader_cls=TextLoader)
    documents = loader.load()
    
    if not documents:
        print("⚠️ No documents found.")
        return

    # FIX: Larger chunk size + Specific Separator
    # This ensures "Tribe" + "Next Question" stay in the SAME chunk.
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["------------------------------------------------", "\n\n"],
        chunk_size=800, # Increased to ensure the whole question fits
        chunk_overlap=50
    )
    chunks = text_splitter.split_documents(documents)
    
    print(f"🧩 Memory divided into {len(chunks)} blocks.")

    print("💾 Saving to Local DB...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings, 
        persist_directory=DB_PATH
    )
    
    print("✅ SOCIALSYNC: Ready.")

if __name__ == "__main__":
    ingest_data()