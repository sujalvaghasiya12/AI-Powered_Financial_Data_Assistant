# AI-Powered Financial Data Assistant

An intelligent financial data assistant that helps users query and retrieve insights from financial transaction data using semantic similarity and vector embeddings.

## 🎯 Objective

Build an AI-powered financial data assistant that can understand and answer user queries semantically. The system generates synthetic financial transactions, stores them in a vector database using embeddings, and allows users to ask natural language questions to get relevant transactions or summarized insights.

## 📋 Features

- **AI-Based Data Generation**: Generate synthetic transaction data for multiple users
- **Semantic Search**: Understand natural language queries using vector embeddings
- **Vector Database**: FAISS for efficient similarity search
- **RESTful API**: FastAPI endpoints for search and analysis
- **Multi-User Support**: Isolated data and vector stores per user

## 🏗️ Project Structure

financial-data-assistant/
│
├── data/
│ └── transactions.json # AI-generated dummy financial data
├── embeddings/
│ ├── vector_store.faiss
├── api/
│ ├── app.py # Main API entry point
│ └── routes/
│ └── search.py # Query endpoints
├── services/
│ ├── data_generator.py # AI-based dummy data generator
│ ├── embedding_service.py # Generate embeddings
│ ├── vector_search_service.py # Vector DB operations
│ ├── summarizer_service.py # Basic summarization
├── config/
│ └── db_config.py # Vector DB configuration
├── requirements.txt # Python dependencies
└── README.md


## 📊 Data Model

Each transaction includes the following fields:

json
{
  "id": "txn_101",
  "userId": "user_1",
  "date": "2024-08-10",
  "description": "UPI payment to Swiggy",
  "amount": 520,
  "type": "Debit",
  "category": "Food",
  "balance": 12480
}

Technical Stack

Language: Python 3.8+

Framework: FastAPI

Embedding Model: sentence-transformers/all-MiniLM-L6-v2

Vector Database: FAISS (Facebook AI Similarity Search)

Data Generation: Custom Python generator with realistic patterns


📦 Installation

Clone the repository

bash
git clone <repository-url>
cd financial-data-assistant
Install dependencies

bash
pip install -r requirements.txt

🚀 Quick Start
Run the application

bash
uvicorn api.app:app --reload --port 8000
Access the API

API Documentation: http://localhost:8000/docs

Health Check: http://localhost:8000/health

📝 API Endpoints
🔍 Search Transactions
GET /api/v1/search

Parameters:

query (required): Natural language query

top_k (optional): Number of results (default: 5, max: 200)

Example Queries:

bash
# Basic semantic search
curl "http://localhost:8000/api/v1/search?query=food%20expenses"

# With specific user
curl "http://localhost:8000/api/v1/search?query=shopping&user_id=user_2&top_k=5"
🔧 Utility Endpoints
GET / - API information

GET /health - Health check

GET /rebuild-index - Force rebuild FAISS index

💬 Example Queries
"Show my food expenses"

"Recent shopping transactions"

"Salary deposits this month"

"Entertainment spending"

"Travel expenses"

"Show all UPI transactions above ₹1000"

"What's my biggest expense in August?"

"How much did I spend on food last month?"

🔧 Configuration
Vector Database Config
python

@dataclass
class VectorDBConfig:
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    faiss_index_path: str = "embeddings/vector_store.faiss"
    top_k_results: int = 10

Data Generation Config

python
@dataclass
class DataConfig:
    num_users: int = 3
    min_transactions: int = 100
    max_transactions: int = 200
    data_path: str = "data/transactions.json"

🎨 Features

1. AI-Based Data Generation
Generates 100-200 realistic transactions per user

Maintains proper balance calculations

Uses realistic merchant names and descriptions

Supports multiple transaction categories

2. Semantic Search
Converts transactions to embedding text

Uses cosine similarity for vector search

Supports natural language queries

3. Multi-User Support
Isolated data per user

User-specific filtering

🔍 How It Works
Data Generation → Creates synthetic financial transactions

Embedding Creation → Converts transactions to vector embeddings

Vector Storage → Stores embeddings in FAISS index

Query Processing → Converts user query to embedding

Similarity Search → Finds most similar transactions

Result Processing → Returns relevant transactions



