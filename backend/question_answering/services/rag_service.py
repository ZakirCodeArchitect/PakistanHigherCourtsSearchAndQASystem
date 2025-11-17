"""
RAG (Retrieval-Augmented Generation) Service
Integrates Pinecone vector database with sentence transformers for semantic search
"""

import os
import logging
import hashlib
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
from django.conf import settings
from django.db import connection

logger = logging.getLogger(__name__)


class RAGService:
    """Retrieval-Augmented Generation service using Pinecone and sentence transformers"""
    
    def __init__(self):
        """Initialize RAG service with Pinecone and sentence transformers"""
        self.embedding_model = None
        self.pinecone_client = None
        self.pinecone_index = None
        self.embedding_dimension = 384  # Default for all-MiniLM-L6-v2
        
        # Initialize components
        self._initialize_embedding_model()
        self._initialize_pinecone()
    
    def _initialize_embedding_model(self):
        """Initialize sentence transformer model for embeddings"""
        try:
            model_name = "all-MiniLM-L6-v2"
            logger.info(f"Loading sentence transformer model: {model_name}")
            self.embedding_model = SentenceTransformer(model_name)
            self.embedding_dimension = self.embedding_model.get_sentence_embedding_dimension()
            logger.info(f"Embedding model loaded successfully. Dimension: {self.embedding_dimension}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {str(e)}")
            self.embedding_model = None
    
    def _initialize_pinecone(self):
        """Initialize Pinecone vector database"""
        try:
            api_key = os.getenv("PINECONE_API_KEY")
            
            if not api_key:
                logger.warning("PINECONE_API_KEY not found. Vector search will be disabled.")
                return
            
            # Initialize Pinecone client (new API)
            self.pinecone_client = Pinecone(api_key=api_key)
            
            index_name = getattr(settings, 'PINECONE_INDEX_NAME', 'legal-cases-index')
            existing_indexes = self.pinecone_client.list_indexes()
            index_names = [idx.name for idx in existing_indexes]
            
            if index_name not in index_names:
                logger.info(f"Creating Pinecone index: {index_name}")
                from pinecone import ServerlessSpec
                self.pinecone_client.create_index(
                    name=index_name,
                    dimension=self.embedding_dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
            
            self.pinecone_index = self.pinecone_client.Index(index_name)
            logger.info(f"Pinecone index '{index_name}' initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {str(e)}")
            self.pinecone_index = None
            self.pinecone_client = None
    
    def _sanitize_metadata_value(self, value: Any):
        """Ensure metadata values conform to Pinecone requirements."""
        if value is None:
            return None
        if isinstance(value, (str, bool)):
            return value
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, list):
            sanitized = []
            for item in value:
                coerced = self._sanitize_metadata_value(item)
                if coerced is None:
                    continue
                if isinstance(coerced, list):
                    sanitized.extend(coerced)
                elif isinstance(coerced, (int, float, bool)):
                    sanitized.append(str(coerced))
                else:
                    sanitized.append(coerced)
            return sanitized if sanitized else None
        if isinstance(value, dict):
            parts = []
            for key, val in value.items():
                coerced = self._sanitize_metadata_value(val)
                if coerced is None:
                    continue
                if isinstance(coerced, list):
                    parts.append(f"{key}: {', '.join(str(item) for item in coerced)}")
                else:
                    parts.append(f"{key}: {coerced}")
            return ", ".join(parts) if parts else None
        return str(value)
    
    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """Create embeddings for a list of texts"""
        if not self.embedding_model:
            logger.error("Embedding model not initialized")
            return np.array([])
        
        try:
            embeddings = self.embedding_model.encode(texts, convert_to_tensor=False)
            return embeddings
        except Exception as e:
            logger.error(f"Error creating embeddings: {str(e)}")
            return np.array([])
    
    def create_query_embedding(self, query: str) -> np.ndarray:
        """Create embedding for a single query"""
        if not self.embedding_model:
            logger.error("Embedding model not initialized")
            return np.array([])
        
        try:
            embedding = self.embedding_model.encode([query], convert_to_tensor=False)
            return embedding[0]
        except Exception as e:
            logger.error(f"Error creating query embedding: {str(e)}")
            return np.array([])
    
    def search_similar_documents(self, query: str, top_k: int = 5, filter_dict: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Search for similar documents using Pinecone"""
        if not self.pinecone_index:
            logger.warning("Pinecone index not available. Falling back to database search.")
            return self._fallback_database_search(query, top_k)
        
        try:
            # Create query embedding
            query_embedding = self.create_query_embedding(query)
            if query_embedding.size == 0:
                return self._fallback_database_search(query, top_k)
            
            # Search Pinecone
            search_results = self.pinecone_index.query(
                vector=query_embedding.tolist(),
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict
            )
            
            # Process results
            results = []
            for match in search_results['matches']:
                result = {
                    'id': match['id'],
                    'score': match['score'],
                    'metadata': match.get('metadata', {}),
                    'content': match.get('metadata', {}).get('content', ''),
                    'case_id': match.get('metadata', {}).get('case_id'),
                    'document_id': match.get('metadata', {}).get('document_id'),
                    'content_type': match.get('metadata', {}).get('content_type', 'unknown')
                }
                results.append(result)
            
            logger.info(f"Found {len(results)} similar documents for query: '{query[:50]}...'")
            return results
            
        except Exception as e:
            logger.error(f"Error searching Pinecone: {str(e)}")
            return self._fallback_database_search(query, top_k)
    
    def _fallback_database_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Fallback to database search when Pinecone is not available"""
        try:
            # Use PostgreSQL full-text search as fallback
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        c.id as case_id,
                        c.case_number,
                        c.case_title,
                        c.status,
                        c.bench,
                        cd.case_description,
                        dt.clean_text as document_text
                    FROM cases c
                    LEFT JOIN case_details cd ON c.id = cd.case_id
                    LEFT JOIN case_documents cdoc ON c.id = cdoc.case_id
                    LEFT JOIN documents d ON cdoc.document_id = d.id
                    LEFT JOIN document_texts dt ON d.id = dt.document_id
                    WHERE 
                        c.case_title ILIKE %s OR
                        c.case_number ILIKE %s OR
                        cd.case_description ILIKE %s OR
                        dt.clean_text ILIKE %s
                    ORDER BY 
                        CASE 
                            WHEN c.case_title ILIKE %s THEN 1
                            WHEN c.case_number ILIKE %s THEN 2
                            WHEN cd.case_description ILIKE %s THEN 3
                            ELSE 4
                        END
                    LIMIT %s
                """, [f'%{query}%'] * 7 + [top_k])
                
                results = []
                for row in cursor.fetchall():
                    result = {
                        'case_id': row[0],
                        'case_number': row[1],
                        'case_title': row[2],
                        'status': row[3],
                        'bench': row[4],
                        'case_description': row[5],
                        'document_text': row[6],
                        'score': 0.8,  # Default score for database results
                        'content_type': 'case_metadata'
                    }
                    results.append(result)
                
                logger.info(f"Database fallback found {len(results)} results for query: '{query[:50]}...'")
                return results
                
        except Exception as e:
            logger.error(f"Error in database fallback search: {str(e)}")
            return []
    
    def _generate_doc_id(self, case_id: Optional[int], content_type: str, content: str,
                         document_id: Optional[int] = None, custom_id: Optional[str] = None) -> str:
        """Generate a deterministic document ID for indexing"""
        if custom_id:
            return custom_id
        
        base_parts = [
            f"case{case_id}" if case_id is not None else "case_unknown",
            content_type or "metadata"
        ]
        if document_id is not None:
            base_parts.append(f"doc{document_id}")
        
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
        base_parts.append(content_hash)
        return "_".join(base_parts)
    
    def index_document(self, case_id: int, content: str, content_type: str = "case_metadata", 
                      document_id: Optional[int] = None, metadata: Optional[Dict] = None,
                      doc_id: Optional[str] = None) -> bool:
        """Index a document in Pinecone"""
        if not self.pinecone_index:
            logger.warning("Pinecone index not available. Cannot index document.")
            return False
        
        try:
            # Create embedding
            embedding = self.create_query_embedding(content)
            if embedding.size == 0:
                logger.error(f"Failed to create embedding for case {case_id}")
                return False
            
            # Prepare metadata
            snippet = content[:2000]
            doc_metadata = {
                'content_type': content_type,
                'text': content[:1000],
                'content': snippet,
                'created_at': str(datetime.now())
            }

            if case_id is not None:
                doc_metadata['case_id'] = case_id
            if document_id is not None:
                doc_metadata['document_id'] = str(document_id)
            
            if metadata:
                doc_metadata.update({k: v for k, v in metadata.items() if v is not None})

            # Sanitize metadata values
            sanitized_metadata: Dict[str, Any] = {}
            for key, value in doc_metadata.items():
                sanitized = self._sanitize_metadata_value(value)
                if sanitized in (None, []):
                    continue
                sanitized_metadata[key] = sanitized
            
            if not sanitized_metadata:
                logger.warning("Skipping document indexing due to empty metadata after sanitization")
                return False
            
            # Create unique ID
            doc_id = self._generate_doc_id(case_id, content_type, content, document_id=document_id, custom_id=doc_id)
            
            # Upsert to Pinecone
            self.pinecone_index.upsert(
                vectors=[{
                    'id': doc_id,
                    'values': embedding.tolist(),
                    'metadata': sanitized_metadata
                }]
            )
            
            logger.info(f"Successfully indexed document {doc_id} for case {case_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing document for case {case_id}: {str(e)}")
            return False
    
    def batch_index_documents(self, documents: List[Dict[str, Any]], batch_size: int = 100) -> Dict[str, int]:
        """Batch index multiple documents"""
        if not self.pinecone_index:
            logger.warning("Pinecone index not available. Cannot batch index documents.")
            return {'success': 0, 'failed': len(documents)}
        
        success_count = 0
        failed_count = 0
        
        try:
            # Process in batches
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                vectors = []
                
                for doc in batch:
                    try:
                        # Create embedding
                        embedding = self.create_query_embedding(doc['content'])
                        if embedding.size == 0:
                            failed_count += 1
                            continue
                        
                        # Prepare metadata
                        snippet = doc['content'][:2000]
                        doc_metadata = {
                            'content_type': doc.get('content_type', 'case_metadata'),
                            'text': doc['content'][:1000],
                            'content': snippet,
                            'created_at': str(datetime.now())
                        }
                        
                        case_id = doc.get('case_id')
                        if case_id is not None:
                            doc_metadata['case_id'] = case_id
                        if 'document_id' in doc and doc['document_id'] is not None:
                            doc_metadata['document_id'] = str(doc['document_id'])
                        
                        metadata = doc.get('metadata')
                        if metadata:
                            for key, value in metadata.items():
                                if value is not None:
                                    doc_metadata[key] = value
                        
                        # Sanitize metadata
                        sanitized_metadata: Dict[str, Any] = {}
                        for key, value in doc_metadata.items():
                            sanitized = self._sanitize_metadata_value(value)
                            if sanitized in (None, []):
                                continue
                            sanitized_metadata[key] = sanitized

                        if not sanitized_metadata:
                            failed_count += 1
                            continue
                        
                        # Create unique ID
                        doc_id = self._generate_doc_id(
                            doc.get('case_id'),
                            doc.get('content_type', 'metadata'),
                            doc['content'],
                            document_id=doc.get('document_id'),
                            custom_id=doc.get('id') or doc.get('doc_id')
                        )
                        
                        vectors.append({
                            'id': doc_id,
                            'values': embedding.tolist(),
                            'metadata': sanitized_metadata
                        })
                        
                    except Exception as e:
                        logger.error(f"Error preparing document for indexing: {str(e)}")
                        failed_count += 1
                
                # Upsert batch
                if vectors:
                    self.pinecone_index.upsert(vectors=vectors)
                    success_count += len(vectors)
                
                logger.info(f"Processed batch {i//batch_size + 1}: {len(vectors)} documents indexed")
            
            logger.info(f"Batch indexing completed: {success_count} success, {failed_count} failed")
            return {'success': success_count, 'failed': failed_count}
            
        except Exception as e:
            logger.error(f"Error in batch indexing: {str(e)}")
            return {'success': success_count, 'failed': len(documents) - success_count}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get RAG system status"""
        return {
            'embedding_model': {
                'enabled': self.embedding_model is not None,
                'model_name': 'all-MiniLM-L6-v2' if self.embedding_model else 'disabled',
                'dimension': self.embedding_dimension
            },
            'pinecone': {
                'enabled': self.pinecone_index is not None,
                'index_name': getattr(settings, 'PINECONE_INDEX_NAME', 'legal-cases-index'),
                'api_key_configured': bool(os.getenv("PINECONE_API_KEY"))
            },
            'rag_status': 'fully_operational' if (self.embedding_model and self.pinecone_index) else 'limited'
        }
