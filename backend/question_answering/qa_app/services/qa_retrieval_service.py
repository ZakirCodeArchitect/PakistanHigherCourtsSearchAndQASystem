"""
QA Retrieval Service
Implements two-stage retrieval with cross-encoder reranking for Question-Answering
"""

import os
import logging
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer, CrossEncoder
from pinecone import Pinecone
import hashlib
import pickle
import os
from django.conf import settings

logger = logging.getLogger(__name__)


class QARetrievalService:
    """
    Advanced QA Retrieval Service implementing two-stage retrieval:
    1. Initial broad semantic retrieval (top-30)
    2. Cross-encoder reranking for quality (top-8-12)
    """
    
    def __init__(self):
        """Initialize QA retrieval service with two-stage retrieval"""
        self.embedding_model = None
        self.cross_encoder = None
        self.pinecone_client = None
        self.pinecone_index = None
        self.embedding_dimension = 384  # all-MiniLM-L6-v2
        
        # QA-specific configuration
        self.config = {
            'initial_retrieval_k': 30,      # Stage 1: Broad retrieval
            'final_retrieval_k': 12,        # Stage 2: Quality reranking
            'min_rerank_k': 8,              # Minimum results after reranking
            'semantic_weight': 0.7,         # Weight for semantic similarity
            'qa_relevance_weight': 0.3,     # Weight for QA-specific relevance
            'diversity_threshold': 0.8,     # MMR diversity threshold
            'cross_encoder_model': 'cross-encoder/ms-marco-MiniLM-L-6-v2'
        }
        
        # Embedding cache for performance optimization
        self.embedding_cache = {}
        self.cache_dir = getattr(settings, 'EMBEDDING_CACHE_DIR', '/tmp/qa_embeddings_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize components
        self._initialize_embedding_model()
        self._initialize_cross_encoder()
        self._initialize_pinecone()
    
    def _initialize_embedding_model(self):
        """Initialize sentence transformer for semantic search"""
        try:
            model_name = "all-MiniLM-L6-v2"
            logger.info(f"Loading QA embedding model: {model_name}")
            self.embedding_model = SentenceTransformer(model_name)
            self.embedding_dimension = self.embedding_model.get_sentence_embedding_dimension()
            logger.info(f"QA embedding model loaded. Dimension: {self.embedding_dimension}")
        except Exception as e:
            logger.error(f"Failed to load QA embedding model: {str(e)}")
            self.embedding_model = None
    
    def _initialize_cross_encoder(self):
        """Initialize cross-encoder for quality reranking"""
        try:
            model_name = self.config['cross_encoder_model']
            logger.info(f"Loading QA cross-encoder: {model_name}")
            self.cross_encoder = CrossEncoder(model_name)
            logger.info("QA cross-encoder loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load QA cross-encoder: {str(e)}")
            self.cross_encoder = None
    
    def _initialize_pinecone(self):
        """Initialize Pinecone for vector storage"""
        try:
            api_key = os.getenv("PINECONE_API_KEY")
            
            if not api_key:
                logger.warning("PINECONE_API_KEY not found. QA retrieval will use fallback methods.")
                return
            
            self.pinecone_client = Pinecone(api_key=api_key)
            
            # Use QA-specific index
            index_name = "qa-legal-knowledge"
            if index_name in self.pinecone_client.list_indexes().names():
                self.pinecone_index = self.pinecone_client.Index(index_name)
                logger.info(f"Connected to QA Pinecone index: {index_name}")
            else:
                logger.warning(f"QA Pinecone index '{index_name}' not found")
                
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone for QA: {str(e)}")
            self.pinecone_client = None
            self.pinecone_index = None
    
    def _get_text_hash(self, text: str) -> str:
        """Generate hash for text to use as cache key"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _get_cached_embeddings(self, texts: List[str]) -> Tuple[List[np.ndarray], List[str]]:
        """Get cached embeddings for texts, return (embeddings, uncached_texts)"""
        cached_embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            text_hash = self._get_text_hash(text)
            cache_file = os.path.join(self.cache_dir, f"{text_hash}.pkl")
            
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'rb') as f:
                        embedding = pickle.load(f)
                    cached_embeddings.append((i, embedding))
                except Exception as e:
                    logger.warning(f"Failed to load cached embedding: {str(e)}")
                    uncached_texts.append(text)
                    uncached_indices.append(i)
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        return cached_embeddings, uncached_texts, uncached_indices
    
    def _cache_embeddings(self, texts: List[str], embeddings: np.ndarray) -> None:
        """Cache embeddings for texts"""
        for text, embedding in zip(texts, embeddings):
            text_hash = self._get_text_hash(text)
            cache_file = os.path.join(self.cache_dir, f"{text_hash}.pkl")
            
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(embedding, f)
            except Exception as e:
                logger.warning(f"Failed to cache embedding: {str(e)}")
    
    def _get_embeddings_with_cache(self, texts: List[str]) -> np.ndarray:
        """Get embeddings with caching support"""
        if not self.embedding_model:
            return np.array([])
        
        # Get cached embeddings
        cached_embeddings, uncached_texts, uncached_indices = self._get_cached_embeddings(texts)
        
        # Generate embeddings for uncached texts
        if uncached_texts:
            logger.info(f"Generating embeddings for {len(uncached_texts)} uncached texts")
            new_embeddings = self.embedding_model.encode(uncached_texts, batch_size=32, show_progress_bar=False)
            self._cache_embeddings(uncached_texts, new_embeddings)
        else:
            new_embeddings = np.array([])
        
        # Combine cached and new embeddings in correct order
        all_embeddings = np.zeros((len(texts), self.embedding_dimension))
        
        # Fill in cached embeddings
        for i, embedding in cached_embeddings:
            all_embeddings[i] = embedding
        
        # Fill in new embeddings
        for i, embedding in zip(uncached_indices, new_embeddings):
            all_embeddings[i] = embedding
        
        cache_hit_rate = len(cached_embeddings) / len(texts) * 100
        logger.info(f"Embedding cache hit rate: {cache_hit_rate:.1f}% ({len(cached_embeddings)}/{len(texts)})")
        
        return all_embeddings
    
    def retrieve_for_qa(self, 
                       query: str, 
                       top_k: int = 10,
                       legal_domain: Optional[str] = None,
                       case_type: Optional[str] = None,
                       court_filter: Optional[str] = None,
                       year_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Two-stage retrieval optimized for QA:
        1. Initial broad semantic retrieval (top-30)
        2. Cross-encoder reranking for quality (top-8-12)
        
        Args:
            query: User's question
            top_k: Final number of results to return
            legal_domain: Filter by legal domain (criminal, civil, etc.)
            case_type: Filter by case type (judgment, order, decree)
            court_filter: Filter by court
            year_filter: Filter by year
            
        Returns:
            List of ranked results optimized for QA context
        """
        try:
            logger.info(f"Starting QA retrieval for query: '{query[:50]}...'")
            start_time = datetime.now()
            
            # Stage 1: Initial broad semantic retrieval
            initial_results = self._initial_semantic_retrieval(
                query, 
                self.config['initial_retrieval_k'],
                legal_domain, case_type, court_filter, year_filter
            )
            
            if not initial_results:
                logger.warning("No results from initial semantic retrieval")
                return []
            
            logger.info(f"Stage 1: Retrieved {len(initial_results)} initial results")
            
            # Stage 2: Cross-encoder reranking for quality
            if self.cross_encoder and len(initial_results) > 1:
                reranked_results = self._cross_encoder_reranking(
                    query, initial_results, min(top_k, self.config['final_retrieval_k'])
                )
                logger.info(f"Stage 2: Reranked to {len(reranked_results)} high-quality results")
            else:
                # Fallback: Use initial results with simple ranking
                reranked_results = initial_results[:top_k]
                logger.info("Using initial results (cross-encoder not available)")
            
            # Stage 3: Apply diversity control (MMR)
            final_results = self._apply_diversity_control(reranked_results, top_k)
            
            # Add QA-specific metadata
            for i, result in enumerate(final_results):
                result['qa_rank'] = i + 1
                result['qa_relevance_score'] = result.get('score', 0.0)
                result['retrieval_method'] = 'two_stage_qa'
                result['retrieval_time'] = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"QA retrieval completed: {len(final_results)} results in {result['retrieval_time']:.3f}s")
            return final_results
            
        except Exception as e:
            logger.error(f"Error in QA retrieval: {str(e)}")
            return []
    
    def _initial_semantic_retrieval(self, 
                                  query: str, 
                                  top_k: int,
                                  legal_domain: Optional[str] = None,
                                  case_type: Optional[str] = None,
                                  court_filter: Optional[str] = None,
                                  year_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Stage 1: Initial broad semantic retrieval"""
        try:
            if not self.pinecone_index or not self.embedding_model:
                logger.warning("Pinecone or embedding model not available, using fallback")
                return self._fallback_retrieval(query, top_k, legal_domain, case_type, court_filter, year_filter)
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0]
            
            # Prepare filters for Pinecone (using actual metadata fields)
            pinecone_filters = {}
            if legal_domain:
                # Skip legal_domain filtering as it's not in current metadata
                logger.warning(f"Legal domain filtering not available in current metadata: {legal_domain}")
                # Don't add to pinecone_filters to avoid filtering
            if case_type:
                # Map case_type to available fields - use status as proxy
                if case_type.lower() in ['pending', 'decided']:
                    pinecone_filters['status'] = case_type.title()
                else:
                    logger.warning(f"Case type filtering not available in current metadata: {case_type}")
            if court_filter:
                pinecone_filters['court'] = court_filter
            if year_filter:
                # Map year_filter to institution_date - Pinecone expects numeric values
                # For now, skip year filtering as it requires date parsing
                logger.warning(f"Year filtering not implemented for Pinecone: {year_filter}")
            
            # Search Pinecone
            search_params = {
                'vector': query_embedding.tolist(),
                'top_k': top_k,
                'include_metadata': True
            }
            
            if pinecone_filters:
                search_params['filter'] = pinecone_filters
            
            search_results = self.pinecone_index.query(**search_params)
            
            # Process results
            results = []
            for match in search_results.matches:
                metadata = match.metadata
                result = {
                    'id': match.id,
                    'score': match.score,
                    'text': metadata.get('text', ''),
                    'metadata': metadata,
                    'retrieval_stage': 'initial_semantic',
                    'source': 'Pinecone',
                    'file_name': metadata.get('file_name', 'Unknown'),
                    'case_title': metadata.get('case_title', 'Unknown'),
                    'case_number': metadata.get('case_number', 'Unknown')
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in initial semantic retrieval: {str(e)}")
            return self._fallback_retrieval(query, top_k)
    
    def _cross_encoder_reranking(self, 
                               query: str, 
                               initial_results: List[Dict[str, Any]], 
                               top_k: int) -> List[Dict[str, Any]]:
        """Stage 2: Cross-encoder reranking for quality"""
        try:
            if not self.cross_encoder or len(initial_results) <= 1:
                return initial_results[:top_k]
            
            # Prepare query-document pairs
            pairs = []
            for result in initial_results:
                text = result.get('text', '')
                if text:
                    pairs.append((query, text))
                else:
                    pairs.append((query, ''))
            
            # Get cross-encoder scores
            rerank_scores = self.cross_encoder.predict(pairs)
            
            # Combine with initial scores
            for i, result in enumerate(initial_results):
                initial_score = result.get('score', 0.0)
                rerank_score = float(rerank_scores[i])
                
                # Weighted combination: 70% cross-encoder + 30% initial
                combined_score = (
                    self.config['semantic_weight'] * rerank_score +
                    (1 - self.config['semantic_weight']) * initial_score
                )
                
                result['rerank_score'] = rerank_score
                result['combined_score'] = combined_score
                result['retrieval_stage'] = 'cross_encoder_reranked'
                # Preserve source information
                if 'source' not in result:
                    result['source'] = 'Pinecone'
            
            # Sort by combined score
            reranked_results = sorted(initial_results, key=lambda x: x['combined_score'], reverse=True)
            
            # Return top-k results
            return reranked_results[:top_k]
            
        except Exception as e:
            logger.error(f"Error in cross-encoder reranking: {str(e)}")
            return initial_results[:top_k]
    
    def _apply_diversity_control(self, 
                               results: List[Dict[str, Any]], 
                               top_k: int) -> List[Dict[str, Any]]:
        """Apply Maximal Marginal Relevance (MMR) for diversity"""
        try:
            if len(results) <= 1:
                return results
            
            # Simple diversity control: avoid very similar results
            diverse_results = []
            used_texts = set()
            
            for result in results:
                text = result.get('text', '').lower()
                
                # Check for similarity with already selected results
                is_similar = False
                for used_text in used_texts:
                    # Simple similarity check (can be improved with embeddings)
                    text_words = set(text.split())
                    used_words = set(used_text.split())
                    intersection = text_words & used_words
                    union = text_words | used_words
                    
                    # Avoid division by zero
                    if len(union) > 0:
                        similarity = len(intersection) / len(union)
                        if similarity > self.config['diversity_threshold']:
                            is_similar = True
                            break
                
                if not is_similar:
                    diverse_results.append(result)
                    used_texts.add(text)
                    
                    if len(diverse_results) >= top_k:
                        break
            
            # If we don't have enough diverse results, add the best remaining ones
            if len(diverse_results) < top_k:
                for result in results:
                    if result not in diverse_results:
                        diverse_results.append(result)
                        if len(diverse_results) >= top_k:
                            break
            
            return diverse_results
            
        except Exception as e:
            logger.error(f"Error in diversity control: {str(e)}")
            return results[:top_k]
    
    def _fallback_retrieval(self, query: str, top_k: int,
                          legal_domain: Optional[str] = None,
                          case_type: Optional[str] = None,
                          court_filter: Optional[str] = None,
                          year_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fallback retrieval when Pinecone is not available"""
        try:
            logger.info("Using fallback retrieval with database and embeddings")
            
            # Step 1: Try to get results from existing QA knowledge base
            qa_results = self._retrieve_from_qa_knowledge_base(
                query, top_k, legal_domain, case_type, court_filter, year_filter
            )
            if qa_results:
                logger.info(f"Fallback retrieval found {len(qa_results)} results from QA knowledge base")
                return qa_results
            
            # Step 2: Try to get results from database with embeddings
            db_results = self._retrieve_from_database_with_embeddings(
                query, top_k, legal_domain, case_type, court_filter, year_filter
            )
            if db_results:
                logger.info(f"Fallback retrieval found {len(db_results)} results from database")
                return db_results
            
            # Step 3: Try simple database search as last resort
            simple_results = self._retrieve_from_database_simple(
                query, top_k, legal_domain, case_type, court_filter, year_filter
            )
            if simple_results:
                logger.info(f"Fallback retrieval found {len(simple_results)} results from simple database search")
                return simple_results
            
            logger.warning("Fallback retrieval found no results")
            return []
            
        except Exception as e:
            logger.error(f"Error in fallback retrieval: {str(e)}")
            return []
    
    def _retrieve_from_qa_knowledge_base(self, query: str, top_k: int, 
                                       legal_domain: Optional[str] = None,
                                       case_type: Optional[str] = None,
                                       court_filter: Optional[str] = None,
                                       year_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve from existing QA knowledge base with filters"""
        try:
            from qa_app.models import QAKnowledgeBase
            
            # Build filter conditions using correct field names
            filters = {'content_text__icontains': query}
            
            if legal_domain:
                filters['legal_domain'] = legal_domain
            if court_filter:
                filters['court'] = court_filter
            if year_filter:
                filters['date_decided__year'] = year_filter
            
            # Search in QA knowledge base with filters
            qa_docs = QAKnowledgeBase.objects.filter(**filters).order_by('-legal_relevance_score')[:top_k]
            
            results = []
            if qa_docs and self.embedding_model:
                # OPTIMIZATION: Batch embedding generation for QA docs
                import time
                batch_start = time.time()
                
                # Prepare texts for batch embedding
                texts_for_embedding = [doc.content_text[:1000] for doc in qa_docs]
                
                # Generate query embedding
                query_embedding = self.embedding_model.encode([query])[0]
                
                # Generate all document embeddings in one batch with caching
                doc_embeddings = self._get_embeddings_with_cache(texts_for_embedding)
                
                # Vectorized similarity calculation
                query_norm = np.linalg.norm(query_embedding)
                doc_norms = np.linalg.norm(doc_embeddings, axis=1)
                similarities = np.dot(doc_embeddings, query_embedding) / (doc_norms * query_norm)
                
                batch_time = time.time() - batch_start
                logger.info(f"QA KB batch embedding time: {batch_time:.3f}s ({len(qa_docs)} documents)")
                
                # Build results with pre-calculated similarities
                for i, doc in enumerate(qa_docs):
                    result = {
                        'id': f"qa_doc_{doc.id}",
                        'score': float(similarities[i]),
                        'text': doc.content_text,
                        'metadata': {
                            'source': 'qa_knowledge_base',
                            'legal_domain': doc.legal_domain,
                            'source_type': doc.source_type,
                            'court': doc.court,
                            'year': doc.date_decided.year if doc.date_decided else None,
                            'legal_relevance_score': doc.legal_relevance_score,
                            'citations': doc.citations,
                            'content_quality_score': doc.content_quality_score
                        },
                        'retrieval_stage': 'fallback_qa_kb'
                    }
                    results.append(result)
            else:
                # Fallback for when embedding model is not available
                for doc in qa_docs:
                    result = {
                        'id': f"qa_doc_{doc.id}",
                        'score': 0.5,  # Default score
                        'text': doc.content_text,
                        'metadata': {
                            'source': 'qa_knowledge_base',
                            'legal_domain': doc.legal_domain,
                            'source_type': doc.source_type,
                            'court': doc.court,
                            'year': doc.date_decided.year if doc.date_decided else None,
                            'legal_relevance_score': doc.legal_relevance_score,
                            'citations': doc.citations,
                            'content_quality_score': doc.content_quality_score
                        },
                        'retrieval_stage': 'fallback_qa_kb'
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving from QA knowledge base: {str(e)}")
            return []
    
    def _retrieve_from_database_with_embeddings(self, query: str, top_k: int,
                                              legal_domain: Optional[str] = None,
                                              case_type: Optional[str] = None,
                                              court_filter: Optional[str] = None,
                                              year_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve from database with embedding similarity and filters - OPTIMIZED"""
        try:
            from django.db import connection
            import time
            
            start_time = time.time()
            
            # Build SQL query with filters
            where_conditions = ["dt.clean_text IS NOT NULL", "LENGTH(dt.clean_text) > 100"]
            params = []
            
            if legal_domain:
                where_conditions.append("legal_domain = %s")
                params.append(legal_domain)
            if case_type:
                where_conditions.append("case_type = %s")
                params.append(case_type)
            if court_filter:
                where_conditions.append("court = %s")
                params.append(court_filter)
            if year_filter:
                where_conditions.append("year = %s")
                params.append(year_filter)
            
            sql = f"""
                SELECT dt.id, dt.clean_text, d.file_name
                FROM document_texts dt
                JOIN documents d ON dt.document_id = d.id
                WHERE {' AND '.join(where_conditions)}
                LIMIT 100
            """
            
            # Get documents from database
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
            
            if not rows:
                return []
            
            db_time = time.time() - start_time
            logger.info(f"Database query time: {db_time:.3f}s")
            
            # Generate query embedding
            if not self.embedding_model:
                return []
            
            embedding_start = time.time()
            query_embedding = self.embedding_model.encode([query])[0]
            query_embedding_time = time.time() - embedding_start
            logger.info(f"Query embedding time: {query_embedding_time:.3f}s")
            
            # OPTIMIZATION 1: Batch embedding generation
            batch_start = time.time()
            texts_for_embedding = [row[1][:1000] for row in rows]  # Limit text for embedding
            
            # Generate all document embeddings in one batch with caching
            doc_embeddings = self._get_embeddings_with_cache(texts_for_embedding)
            batch_time = time.time() - batch_start
            logger.info(f"Batch embedding generation time: {batch_time:.3f}s ({len(texts_for_embedding)} documents)")
            
            # OPTIMIZATION 2: Vectorized similarity calculation
            similarity_start = time.time()
            query_norm = np.linalg.norm(query_embedding)
            doc_norms = np.linalg.norm(doc_embeddings, axis=1)
            
            # Calculate all similarities at once
            similarities = np.dot(doc_embeddings, query_embedding) / (doc_norms * query_norm)
            similarity_time = time.time() - similarity_start
            logger.info(f"Vectorized similarity calculation time: {similarity_time:.3f}s")
            
            # Build results
            results = []
            for i, row in enumerate(rows):
                doc_id, text, file_name = row
                
                result = {
                    'id': f"db_doc_{doc_id}",
                    'score': float(similarities[i]),
                    'text': text[:2000],  # Limit text for results
                    'metadata': {
                        'source': 'database',
                        'file_name': file_name,
                        'document_id': doc_id
                    },
                    'retrieval_stage': 'fallback_db_embedding'
                }
                results.append(result)
            
            # Sort by similarity and return top-k
            results.sort(key=lambda x: x['score'], reverse=True)
            
            total_time = time.time() - start_time
            logger.info(f"Total optimized embedding retrieval time: {total_time:.3f}s")
            
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error retrieving from database with embeddings: {str(e)}")
            return []
    
    def _retrieve_from_database_simple(self, query: str, top_k: int,
                                      legal_domain: Optional[str] = None,
                                      case_type: Optional[str] = None,
                                      court_filter: Optional[str] = None,
                                      year_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Simple database search as last resort with filters"""
        try:
            from django.db import connection
            
            # Build filter conditions
            where_conditions = ["(case_text ILIKE %s OR case_title ILIKE %s)"]
            params = [f'%{query}%', f'%{query}%']
            
            if legal_domain:
                where_conditions.append("legal_domain = %s")
                params.append(legal_domain)
            if case_type:
                where_conditions.append("case_type = %s")
                params.append(case_type)
            if court_filter:
                where_conditions.append("court = %s")
                params.append(court_filter)
            if year_filter:
                where_conditions.append("year = %s")
                params.append(year_filter)
            
            # Add ordering and limit parameters
            params.extend([f'%{query}%', f'%{query}%', top_k])
            
            sql = f"""
                SELECT dt.id, dt.clean_text, d.file_name
                FROM document_texts dt
                JOIN documents d ON dt.document_id = d.id
                WHERE dt.clean_text ILIKE %s OR d.file_name ILIKE %s
                ORDER BY 
                    CASE 
                        WHEN dt.clean_text ILIKE %s THEN 1
                        WHEN d.file_name ILIKE %s THEN 2
                        ELSE 3
                    END
                LIMIT %s
            """
            
            # Simple text search in database
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
            
            results = []
            for row in rows:
                doc_id, text, file_name = row
                
                # Simple relevance scoring based on text match
                text_lower = text.lower() if text else ""
                query_lower = query.lower()
                match_count = text_lower.count(query_lower)
                relevance_score = min(match_count / 10.0, 1.0)  # Normalize to 0-1
                
                result = {
                    'id': f"db_simple_{doc_id}",
                    'score': relevance_score,
                    'text': text[:2000] if text else "",
                    'metadata': {
                        'source': 'database_simple',
                        'file_name': file_name,
                        'document_id': doc_id,
                        'match_count': match_count
                    },
                    'retrieval_stage': 'fallback_db_simple'
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in simple database retrieval: {str(e)}")
            return []
    
    def get_qa_retrieval_stats(self) -> Dict[str, Any]:
        """Get statistics about QA retrieval performance"""
        return {
            'embedding_model_loaded': self.embedding_model is not None,
            'cross_encoder_loaded': self.cross_encoder is not None,
            'pinecone_connected': self.pinecone_index is not None,
            'embedding_dimension': self.embedding_dimension,
            'config': self.config,
            'retrieval_method': 'two_stage_qa_retrieval'
        }
