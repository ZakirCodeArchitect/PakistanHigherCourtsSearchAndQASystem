"""
Advanced Embedding Service
Supports multiple embedding models including BGE, OpenAI embeddings, and Sentence Transformers
"""

import os
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Union
from django.conf import settings
import openai
from sentence_transformers import SentenceTransformer
import requests
import json

logger = logging.getLogger(__name__)


class AdvancedEmbeddingService:
    """Advanced embedding service supporting multiple models"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Load .env file
        try:
            from dotenv import load_dotenv
            load_dotenv('.env')
        except Exception:
            pass
            
        self.embedding_model_name = getattr(settings, 'QA_SETTINGS', {}).get('EMBEDDING_MODEL', 'bge-large-en-v1.5')
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Initialize the selected embedding model
        self.embedding_model = None
        self.model_type = None
        self.dimension = None
        
        self._initialize_embedding_model()
    
    def _initialize_embedding_model(self):
        """Initialize the selected embedding model"""
        try:
            if self.embedding_model_name.startswith('text-embedding'):
                # OpenAI embeddings
                self._initialize_openai_embeddings()
            elif self.embedding_model_name.startswith('bge'):
                # BGE embeddings
                self._initialize_bge_embeddings()
            else:
                # Default to Sentence Transformers
                self._initialize_sentence_transformers()
                
            self.logger.info(f"Embedding model initialized: {self.embedding_model_name} (type: {self.model_type}, dim: {self.dimension})")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize embedding model: {str(e)}")
            # Fallback to default
            self._initialize_sentence_transformers()
    
    def _initialize_openai_embeddings(self):
        """Initialize OpenAI embeddings"""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found")
        
        self.model_type = 'openai'
        self.dimension = 1536  # OpenAI text-embedding-ada-002
        self.embedding_model = openai.OpenAI(api_key=self.openai_api_key)
        
        # Update dimension based on model
        if '3-large' in self.embedding_model_name:
            self.dimension = 3072
        elif '3-small' in self.embedding_model_name:
            self.dimension = 1536
    
    def _initialize_bge_embeddings(self):
        """Initialize BGE embeddings"""
        try:
            # Try to load BGE model
            self.embedding_model = SentenceTransformer(f"BAAI/{self.embedding_model_name}")
            self.model_type = 'bge'
            self.dimension = self.embedding_model.get_sentence_embedding_dimension()
            
        except Exception as e:
            self.logger.warning(f"BGE model not available, falling back to Sentence Transformers: {str(e)}")
            self._initialize_sentence_transformers()
    
    def _initialize_sentence_transformers(self):
        """Initialize Sentence Transformers (fallback)"""
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.model_type = 'sentence_transformers'
        self.dimension = 384
    
    def create_embeddings(self, texts: List[str]) -> np.ndarray:
        """Create embeddings for a list of texts"""
        try:
            if self.model_type == 'openai':
                return self._create_openai_embeddings(texts)
            else:
                return self._create_local_embeddings(texts)
                
        except Exception as e:
            self.logger.error(f"Error creating embeddings: {str(e)}")
            # Fallback to simple embeddings
            return self._create_fallback_embeddings(texts)
    
    def create_query_embedding(self, query: str) -> np.ndarray:
        """Create embedding for a single query"""
        try:
            embeddings = self.create_embeddings([query])
            return embeddings[0]
            
        except Exception as e:
            self.logger.error(f"Error creating query embedding: {str(e)}")
            # Return zero vector as fallback
            return np.zeros(self.dimension)
    
    def _create_openai_embeddings(self, texts: List[str]) -> np.ndarray:
        """Create embeddings using OpenAI API"""
        try:
            response = self.embedding_model.embeddings.create(
                model=self.embedding_model_name,
                input=texts
            )
            
            embeddings = [data.embedding for data in response.data]
            return np.array(embeddings)
            
        except Exception as e:
            self.logger.error(f"OpenAI embedding error: {str(e)}")
            raise
    
    def _create_local_embeddings(self, texts: List[str]) -> np.ndarray:
        """Create embeddings using local models (BGE or Sentence Transformers)"""
        try:
            embeddings = self.embedding_model.encode(texts, convert_to_tensor=False)
            return embeddings
            
        except Exception as e:
            self.logger.error(f"Local embedding error: {str(e)}")
            raise
    
    def _create_fallback_embeddings(self, texts: List[str]) -> np.ndarray:
        """Create simple fallback embeddings"""
        # Simple word-based embeddings as fallback
        embeddings = []
        for text in texts:
            # Simple word count vector (normalized)
            words = text.lower().split()
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            # Create vector (pad to dimension)
            vector = np.zeros(self.dimension)
            for i, (word, count) in enumerate(word_counts.items()):
                if i < self.dimension:
                    vector[i] = count
            
            # Normalize
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
            
            embeddings.append(vector)
        
        return np.array(embeddings)
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            # Ensure embeddings are normalized
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0
    
    def batch_create_embeddings(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Create embeddings in batches for large datasets"""
        try:
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_embeddings = self.create_embeddings(batch_texts)
                all_embeddings.append(batch_embeddings)
                
                self.logger.info(f"Processed batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
            
            return np.vstack(all_embeddings)
            
        except Exception as e:
            self.logger.error(f"Error in batch embedding creation: {str(e)}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current embedding model"""
        return {
            'model_name': self.embedding_model_name,
            'model_type': self.model_type,
            'dimension': self.dimension,
            'is_available': self.embedding_model is not None
        }
    
    def test_embedding_quality(self, sample_texts: List[str]) -> Dict[str, Any]:
        """Test the quality of embeddings with sample texts"""
        try:
            embeddings = self.create_embeddings(sample_texts)
            
            # Calculate pairwise similarities
            similarities = []
            for i in range(len(embeddings)):
                for j in range(i + 1, len(embeddings)):
                    sim = self.calculate_similarity(embeddings[i], embeddings[j])
                    similarities.append(sim)
            
            return {
                'embedding_shape': embeddings.shape,
                'average_similarity': np.mean(similarities) if similarities else 0.0,
                'similarity_std': np.std(similarities) if similarities else 0.0,
                'min_similarity': np.min(similarities) if similarities else 0.0,
                'max_similarity': np.max(similarities) if similarities else 0.0,
                'status': 'success'
            }
            
        except Exception as e:
            self.logger.error(f"Error testing embedding quality: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }


class EmbeddingModelManager:
    """Manager for different embedding models"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.models = {
            'sentence_transformers': {
                'name': 'all-MiniLM-L6-v2',
                'dimension': 384,
                'description': 'Fast, lightweight sentence transformer'
            },
            'bge_large': {
                'name': 'bge-large-en-v1.5',
                'dimension': 1024,
                'description': 'High-quality BGE large model'
            },
            'bge_base': {
                'name': 'bge-base-en-v1.5',
                'dimension': 768,
                'description': 'Balanced BGE base model'
            },
            'openai_ada': {
                'name': 'text-embedding-ada-002',
                'dimension': 1536,
                'description': 'OpenAI Ada embedding model'
            },
            'openai_3_small': {
                'name': 'text-embedding-3-small',
                'dimension': 1536,
                'description': 'OpenAI 3 small embedding model'
            },
            'openai_3_large': {
                'name': 'text-embedding-3-large',
                'dimension': 3072,
                'description': 'OpenAI 3 large embedding model'
            }
        }
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available embedding models"""
        return self.models
    
    def get_model_info(self, model_key: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model"""
        return self.models.get(model_key)
    
    def recommend_model(self, use_case: str) -> str:
        """Recommend the best model for a specific use case"""
        recommendations = {
            'fast': 'sentence_transformers',
            'balanced': 'bge_base',
            'high_quality': 'bge_large',
            'openai': 'openai_ada',
            'large_context': 'openai_3_large'
        }
        
        return recommendations.get(use_case, 'sentence_transformers')
    
    def compare_models(self, texts: List[str]) -> Dict[str, Any]:
        """Compare different embedding models on sample texts"""
        results = {}
        
        for model_key, model_info in self.models.items():
            try:
                # Create embedding service with this model
                service = AdvancedEmbeddingService()
                service.embedding_model_name = model_info['name']
                service._initialize_embedding_model()
                
                # Test quality
                quality_result = service.test_embedding_quality(texts)
                results[model_key] = {
                    'model_info': model_info,
                    'quality_test': quality_result
                }
                
            except Exception as e:
                results[model_key] = {
                    'model_info': model_info,
                    'error': str(e)
                }
        
        return results
