#!/usr/bin/env python3
"""
Document Management Script for RAG Router Agent

This script is used to add documents to the Qdrant databases.
Run this OUTSIDE of RunAgent to populate your databases.

Usage:
    python manage_documents.py add /path/to/document.pdf products
    python manage_documents.py list
    python manage_documents.py stats
"""

import os
import sys
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Qdrant
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Load environment variables
load_dotenv()

# Collection configurations
COLLECTIONS = {
    "products": {
        "name": "Product Information",
        "collection_name": "products_collection",
        "description": "Product details, specifications, and features"
    },
    "support": {
        "name": "Customer Support & FAQ",
        "collection_name": "support_collection",
        "description": "Customer support information, FAQs, and guides"
    },
    "finance": {
        "name": "Financial Information",
        "collection_name": "finance_collection",
        "description": "Financial data, revenue, costs, and liabilities"
    }
}


class DocumentManager:
    """Manage documents in Qdrant databases"""
    
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.qdrant_url = os.getenv("QDRANT_URL")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        
        if not all([self.openai_api_key, self.qdrant_url, self.qdrant_api_key]):
            raise ValueError("Missing required environment variables: OPENAI_API_KEY, QDRANT_URL, QDRANT_API_KEY")
        
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=self.openai_api_key
        )
        
        self.client = QdrantClient(
            url=self.qdrant_url,
            api_key=self.qdrant_api_key
        )
        
        self._initialize_collections()
    
    def _initialize_collections(self):
        """Initialize Qdrant collections if they don't exist"""
        vector_size = 1536  # OpenAI embedding size
        
        for db_type, config in COLLECTIONS.items():
            try:
                self.client.get_collection(config["collection_name"])
                print(f"✅ Collection '{config['collection_name']}' already exists")
            except Exception:
                # Create collection if it doesn't exist
                self.client.create_collection(
                    collection_name=config["collection_name"],
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
                )
                print(f"✨ Created collection '{config['collection_name']}'")
    
    def add_document(self, file_path: str, db_type: str) -> Dict[str, Any]:
        """Add a PDF document to specified database"""
        
        if db_type not in COLLECTIONS:
            return {
                "success": False,
                "message": f"Invalid database type. Must be one of: {list(COLLECTIONS.keys())}"
            }
        
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"File not found: {file_path}"
            }
        
        if not file_path.lower().endswith('.pdf'):
            return {
                "success": False,
                "message": "Only PDF files are supported"
            }
        
        try:
            print(f"\n📄 Processing document: {file_path}")
            print(f"📊 Target database: {COLLECTIONS[db_type]['name']}")
            
            # Load PDF
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            print(f"✅ Loaded {len(documents)} pages")
            
            # Split into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            texts = text_splitter.split_documents(documents)
            print(f"✅ Split into {len(texts)} chunks")
            
            if texts:
                # Create Qdrant vectorstore
                db = Qdrant(
                    client=self.client,
                    collection_name=COLLECTIONS[db_type]["collection_name"],
                    embeddings=self.embeddings
                )
                
                # Add documents
                print(f"⏳ Adding to Qdrant...")
                db.add_documents(texts)
                
                return {
                    "success": True,
                    "message": f"Successfully added {len(texts)} chunks to {COLLECTIONS[db_type]['name']}",
                    "chunks_added": len(texts),
                    "database": COLLECTIONS[db_type]["name"]
                }
            else:
                return {
                    "success": False,
                    "message": "No text extracted from document"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error processing document: {str(e)}"
            }
    
    def list_collections(self):
        """List all collections and their info"""
        print("\n📚 Qdrant Collections:")
        print("=" * 60)
        
        collections = self.client.get_collections()
        
        for collection in collections.collections:
            info = self.client.get_collection(collection.name)
            print(f"\n📦 {collection.name}")
            print(f"   Vectors: {info.vectors_count}")
            print(f"   Status: {info.status}")
    
    def get_stats(self):
        """Get statistics for all databases"""
        print("\n📊 Database Statistics:")
        print("=" * 60)
        
        for db_type, config in COLLECTIONS.items():
            try:
                info = self.client.get_collection(config["collection_name"])
                print(f"\n{config['name']}")
                print(f"   Collection: {config['collection_name']}")
                print(f"   Documents: {info.vectors_count}")
                print(f"   Description: {config['description']}")
            except Exception as e:
                print(f"\n{config['name']}")
                print(f"   Status: ❌ Not found or error: {str(e)}")


def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print("""
RAG Router Agent - Document Manager

Usage:
    python manage_documents.py add <file_path> <database_type>
    python manage_documents.py list
    python manage_documents.py stats

Database Types:
    - products: Product information, specifications, features
    - support: Customer support, FAQs, troubleshooting
    - finance: Financial data, pricing, revenue reports

Examples:
    python manage_documents.py add product_manual.pdf products
    python manage_documents.py add faq_guide.pdf support
    python manage_documents.py add financial_report.pdf finance
    python manage_documents.py list
    python manage_documents.py stats
        """)
        sys.exit(1)
    
    try:
        manager = DocumentManager()
        
        command = sys.argv[1].lower()
        
        if command == "add":
            if len(sys.argv) != 4:
                print("❌ Usage: python manage_documents.py add <file_path> <database_type>")
                sys.exit(1)
            
            file_path = sys.argv[2]
            db_type = sys.argv[3].lower()
            
            result = manager.add_document(file_path, db_type)
            
            if result["success"]:
                print(f"\n✅ {result['message']}")
                print(f"📊 Chunks added: {result['chunks_added']}")
            else:
                print(f"\n❌ {result['message']}")
                sys.exit(1)
        
        elif command == "list":
            manager.list_collections()
        
        elif command == "stats":
            manager.get_stats()
        
        else:
            print(f"❌ Unknown command: {command}")
            print("Available commands: add, list, stats")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()