"""
Vector Indexing Service
Handles semantic indexing using FAISS and sentence transformers
"""

import os
import hashlib
import numpy as np
import faiss
import pickle
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import time

from sentence_transformers import SentenceTransformer
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction

from ..models import VectorIndex, DocumentChunk, IndexingLog
from apps.cases.models import UnifiedCaseView, Case

logger = logging.getLogger(__name__)


class VectorIndexingService:
    """Service for creating and managing vector indexes"""
    
    def __init__(self, config_name: str = "default"):
        self.config_name = config_name
        self.model = None
        self.index = None
        self.vector_index = None
        self.chunk_mappings = {}  # chunk_id -> index_position
        self.index_to_chunk_mapping = []  # List to map FAISS index positions to chunk IDs
        self.faiss_index = None  # Cached FAISS index
        self.last_index_update = None  # Track when index was last updated
        self.config = {
            'chunk_size': 512,
            'chunk_overlap': 50,
            'embedding_model': 'all-MiniLM-L6-v2',
            'batch_size': 32
        }
        
    def initialize_model(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the sentence transformer model"""
        try:
            if self.model is None:
                logger.info(f"Loading sentence transformer model: {model_name}")
                self.model = SentenceTransformer(model_name)
                logger.info(f"Model loaded successfully. Dimension: {self.model.get_sentence_embedding_dimension()}")
            return True
        except Exception as e:
            logger.error(f"Error loading model {model_name}: {str(e)}")
            return False
    
    def create_chunks(self, case_id: int, case_data: Dict) -> List[DocumentChunk]:
        """Create document chunks from case data"""
        try:
            # Check if chunks already exist for this case
            existing_chunks = DocumentChunk.objects.filter(case_id=case_id)
            if existing_chunks.exists():
                logger.info(f"Chunks already exist for case {case_id}, skipping chunk creation")
                return list(existing_chunks)
            
            chunks = []
            content = case_data.get('combined_content', '') or case_data.get('pdf_content', '')
            
            if not content:
                logger.warning(f"No content found for case {case_id}")
                return chunks
            
            # Split content into chunks
            chunk_size = self.config.get('chunk_size', 512)
            chunk_overlap = self.config.get('chunk_overlap', 50)
            
            # Simple text splitting (in production, use more sophisticated chunking)
            words = content.split()
            chunk_count = 0
            
            for i in range(0, len(words), chunk_size - chunk_overlap):
                chunk_words = words[i:i + chunk_size]
                chunk_text = ' '.join(chunk_words)
                
                if len(chunk_text.strip()) < 10:  # Skip very short chunks
                    continue
                
                # Generate unique chunk ID
                chunk_id = hashlib.sha256(f"{case_id}_{chunk_count}_{chunk_text}".encode()).hexdigest()
                
                # Check if chunk already exists
                if DocumentChunk.objects.filter(chunk_id=chunk_id).exists():
                    logger.warning(f"Chunk {chunk_id} already exists, skipping")
                    chunk_count += 1
                    continue
                
                # Create chunk
                chunk = DocumentChunk.objects.create(
                    chunk_id=chunk_id,
                    case_id=case_id,
                    document_id=case_data.get('document_id', None),
                    chunk_text=chunk_text,
                    chunk_index=chunk_count,
                    token_count=len(chunk_words),
                    start_char=0,  # Will be calculated properly in production
                    end_char=len(chunk_text),
                    page_number=None,  # Will be set when PDF processing is available
                )
                
                chunks.append(chunk)
                chunk_count += 1
                
                # Limit chunks per case to avoid memory issues
                if chunk_count >= 50:
                    logger.warning(f"Reached chunk limit for case {case_id}")
                    break
            
            logger.info(f"Created {len(chunks)} chunks for case {case_id}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error creating chunks for case {case_id}: {str(e)}")
            return []
    
    def create_embeddings(self, chunks: List[DocumentChunk], batch_size: int = 32) -> List[np.ndarray]:
        """Create embeddings for text chunks"""
        if not self.model:
            logger.error("Model not initialized")
            return []
        
        try:
            embeddings = []
            chunk_texts = [chunk.chunk_text for chunk in chunks]
            
            # Process in batches
            for i in range(0, len(chunk_texts), batch_size):
                batch_texts = chunk_texts[i:i + batch_size]
                batch_embeddings = self.model.encode(batch_texts, show_progress_bar=False)
                embeddings.extend(batch_embeddings)
                
                logger.info(f"Processed batch {i//batch_size + 1}/{(len(chunk_texts) + batch_size - 1)//batch_size}")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error creating embeddings: {str(e)}")
            return []
    
    def build_faiss_index(self, embeddings: List[np.ndarray], chunks: List[DocumentChunk], index_name: str = "legal_cases") -> Optional[faiss.Index]:
        """Build FAISS index from embeddings and maintain chunk mapping"""
        if not embeddings or not chunks:
            logger.error("No embeddings or chunks provided")
            return None
        
        if len(embeddings) != len(chunks):
            logger.error(f"Mismatch between embeddings ({len(embeddings)}) and chunks ({len(chunks)})")
            return None
        
        try:
            # Convert to numpy array
            embeddings_array = np.array(embeddings).astype('float32')
            dimension = embeddings_array.shape[1]
            
            # Create FAISS index
            index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
            
            # Add vectors to index
            index.add(embeddings_array)
            
            # Create mapping from FAISS index position to chunk ID
            self.index_to_chunk_mapping = [chunk.chunk_id for chunk in chunks]
            
            logger.info(f"Built FAISS index with {len(embeddings)} vectors of dimension {dimension}")
            return index
            
        except Exception as e:
            logger.error(f"Error building FAISS index: {str(e)}")
            return None
    
    def save_index(self, index: faiss.Index, index_name: str, model_name: str) -> bool:
        """Save FAISS index to file and database"""
        try:
            # Create index directory
            index_dir = os.path.join(settings.BASE_DIR, 'data', 'indexes')
            os.makedirs(index_dir, exist_ok=True)
            
            # Save FAISS index
            index_file_path = os.path.join(index_dir, f"{index_name}.faiss")
            faiss.write_index(index, index_file_path)
            
            # Get file size
            index_file_size = os.path.getsize(index_file_path)
            
            # Save mapping to file
            mapping_file_path = os.path.join(index_dir, f"{index_name}_mapping.pkl")
            with open(mapping_file_path, 'wb') as f:
                pickle.dump(self.index_to_chunk_mapping, f)
            
            # Save to database
            vector_index, created = VectorIndex.objects.get_or_create(
                index_name=index_name,
                defaults={
                    'index_type': 'faiss',
                    'embedding_model': model_name,
                    'embedding_dimension': index.d,
                    'index_file_path': index_file_path,
                    'index_file_size': index_file_size,
                    'total_vectors': index.ntotal,
                    'is_built': True,
                    'version': '1.0',
                    'model_version': '1.0'
                }
            )
            
            if not created:
                # Update existing index
                vector_index.embedding_model = model_name
                vector_index.embedding_dimension = index.d
                vector_index.index_file_path = index_file_path
                vector_index.index_file_size = index_file_size
                vector_index.total_vectors = index.ntotal
                vector_index.is_built = True
                vector_index.updated_at = timezone.now()
                vector_index.save()
            
            logger.info(f"Saved FAISS index to {index_file_path} ({index_file_size} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Error saving index: {str(e)}")
            return False
    
    def build_vector_index(self, force: bool = False) -> Dict[str, any]:
        """Build complete vector index for all cases"""
        start_time = time.time()
        stats = {
            'cases_processed': 0,
            'chunks_created': 0,
            'embeddings_created': 0,
            'index_built': False,
            'errors': []
        }
        
        try:
            # Initialize model
            if not self.initialize_model():
                stats['errors'].append("Failed to initialize model")
                return stats
            
            # Get real cases from database
            
            if force:
                # Process all cases
                cases_to_process = UnifiedCaseView.objects.all()
            else:
                # Only process cases that don't have chunks
                existing_case_ids = set(DocumentChunk.objects.values_list('case_id', flat=True))
                cases_to_process = UnifiedCaseView.objects.exclude(case_id__in=existing_case_ids)
            
            total_cases = cases_to_process.count()
            logger.info(f"Processing {total_cases} cases for vector indexing")
            
            if total_cases == 0:
                logger.info("No cases to process for vector indexing")
                stats['index_built'] = True  # Mark as successful even if no cases
                return stats
            
            all_chunks = []
            all_embeddings = []
            
            # Process each case
            for i, unified_view in enumerate(cases_to_process):
                try:
                    logger.info(f"Processing case {i+1}/{total_cases}: {unified_view.case.case_number}")
                    
                    # Prepare comprehensive case data
                    case_data = {
                        'id': unified_view.case.id,
                        'case_number': unified_view.case.case_number or '',
                        'case_title': unified_view.case.case_title or '',
                        'status': unified_view.case.status or '',
                        'bench': unified_view.case.bench or '',
                        'pdf_content': '',
                        'combined_content': ''
                    }
                    
                    # Extract PDF content
                    if unified_view.pdf_content_summary and 'complete_pdf_content' in unified_view.pdf_content_summary:
                        case_data['pdf_content'] = unified_view.pdf_content_summary['complete_pdf_content']
                    elif unified_view.pdf_content_summary and 'cleaned_pdf_content' in unified_view.pdf_content_summary:
                        case_data['pdf_content'] = unified_view.pdf_content_summary['cleaned_pdf_content']
                    
                    # Build comprehensive content from ALL available data
                    content_parts = []
                    
                    # Add case metadata
                    if case_data['case_number']:
                        content_parts.append(f"Case Number: {case_data['case_number']}")
                    if case_data['case_title']:
                        content_parts.append(f"Case Title: {case_data['case_title']}")
                    if case_data['status']:
                        content_parts.append(f"Status: {case_data['status']}")
                    if case_data['bench']:
                        content_parts.append(f"Bench: {case_data['bench']}")
                    
                    # Add PDF content if available
                    if case_data['pdf_content']:
                        content_parts.append(f"PDF Content: {case_data['pdf_content']}")
                    
                    # Add case metadata from JSON field
                    if unified_view.case_metadata:
                        metadata_content = []
                        for key, value in unified_view.case_metadata.items():
                            if value and str(value).strip():
                                metadata_content.append(f"{key}: {value}")
                        if metadata_content:
                            content_parts.append(f"Case Metadata: {' | '.join(metadata_content)}")
                    
                    # Add related data from case relationships
                    # Orders data
                    orders_data = unified_view.case.orders_data.all()
                    if orders_data:
                        orders_content = []
                        for order in orders_data[:5]:  # Limit to first 5 orders
                            order_text = f"Order {order.sr_number}: {order.short_order}"
                            if order.case_stage:
                                order_text += f" - Stage: {order.case_stage}"
                            if order.list_type:
                                order_text += f" - Type: {order.list_type}"
                            orders_content.append(order_text)
                        if orders_content:
                            content_parts.append(f"Orders: {' | '.join(orders_content)}")
                    
                    # Comments data
                    comments_data = unified_view.case.comments_data.all()
                    if comments_data:
                        comments_content = []
                        for comment in comments_data[:5]:  # Limit to first 5 comments
                            comment_text = f"Comment {comment.compliance_date}: {comment.description}"
                            if comment.parties:
                                comment_text += f" - Parties: {comment.parties}"
                            comments_content.append(comment_text)
                        if comments_content:
                            content_parts.append(f"Comments: {' | '.join(comments_content)}")
                    
                    # Parties data
                    parties_data = unified_view.case.parties_detail_data.all()
                    if parties_data:
                        parties_content = []
                        for party in parties_data[:10]:  # Limit to first 10 parties
                            party_text = f"{party.party_side}: {party.party_name}"
                            parties_content.append(party_text)
                        if parties_content:
                            content_parts.append(f"Parties: {' | '.join(parties_content)}")
                    
                    # Case CMS data
                    case_cms_data = unified_view.case.case_cms_data.all()
                    if case_cms_data:
                        cms_content = []
                        for cms in case_cms_data[:5]:  # Limit to first 5 CMS entries
                            cms_text = f"CMS {cms.sr_number}: {cms.cm} - {cms.order_passed}"
                            if cms.description:
                                cms_text += f" - {cms.description}"
                            cms_content.append(cms_text)
                        if cms_content:
                            content_parts.append(f"Case CMS: {' | '.join(cms_content)}")
                    
                    # Combine all content
                    case_data['combined_content'] = ' '.join(content_parts)
                    
                    if not case_data['combined_content'].strip():
                        logger.warning(f"No content found for case {unified_view.case.case_number}")
                        continue
                    
                    # Create chunks
                    chunks = self.create_chunks(case_data['id'], case_data)
                    if not chunks:
                        continue
                    
                    # Create embeddings
                    embeddings = self.create_embeddings(chunks)
                    if not embeddings:
                        continue
                    
                    # Update chunk embeddings
                    for chunk, embedding in zip(chunks, embeddings):
                        chunk.is_embedded = True
                        chunk.embedding_hash = hashlib.sha256(
                            f"{self.model.get_sentence_embedding_dimension()}:{chunk.chunk_text}".encode()
                        ).hexdigest()
                        chunk.save()
                    
                    all_chunks.extend(chunks)
                    all_embeddings.extend(embeddings)
                    stats['cases_processed'] += 1
                    stats['chunks_created'] += len(chunks)
                    stats['embeddings_created'] += len(embeddings)
                    
                except Exception as e:
                    error_msg = f"Error processing case {unified_view.case.case_number}: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
            
            # Build FAISS index
            if all_embeddings:
                index = self.build_faiss_index(all_embeddings, all_chunks)
                if index:
                    success = self.save_index(index, "legal_cases_vector", self.model.get_sentence_embedding_dimension())
                    if success:
                        stats['index_built'] = True
                        logger.info("Vector index built successfully")
                    else:
                        stats['errors'].append("Failed to save index")
                else:
                    stats['errors'].append("Failed to build FAISS index")
            else:
                logger.warning("No embeddings created, skipping index building")
                stats['index_built'] = True  # Mark as successful even if no embeddings
            
            # Log processing time
            processing_time = time.time() - start_time
            stats['processing_time'] = processing_time
            
            # Create indexing log
            IndexingLog.objects.create(
                operation_type='build',
                index_type='vector',
                documents_processed=stats['cases_processed'],
                chunks_processed=stats['chunks_created'],
                vectors_created=stats['embeddings_created'],
                processing_time=processing_time,
                is_successful=stats['index_built'],
                error_message='; '.join(stats['errors']) if stats['errors'] else '',
                config_version='1.0',
                model_version='1.0',
                completed_at=timezone.now()
            )
            
            logger.info(f"Vector indexing completed: {stats['cases_processed']} cases, {stats['chunks_created']} chunks, {stats['embeddings_created']} embeddings")
            return stats
            
        except Exception as e:
            error_msg = f"Error in vector indexing: {str(e)}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
            return stats
    
    def _load_cached_index(self):
        """Load and cache the FAISS index and mapping"""
        try:
            # Check if we need to reload the index
            vector_index = VectorIndex.objects.filter(index_name="legal_cases_vector", is_active=True).first()
            if not vector_index or not vector_index.is_built:
                logger.error("No active vector index found")
                return False
            
            # Check if index has been updated since last load
            if (self.faiss_index is not None and 
                self.last_index_update is not None and 
                self.last_index_update >= vector_index.updated_at):
                logger.debug("Using cached FAISS index")
                return True
            
            logger.info("Loading FAISS index from disk...")
            start_time = time.time()
            
            # Load FAISS index
            self.faiss_index = faiss.read_index(vector_index.index_file_path)
            
            # Load mapping
            index_dir = os.path.dirname(vector_index.index_file_path)
            mapping_file_path = os.path.join(index_dir, "legal_cases_vector_mapping.pkl")
            
            try:
                with open(mapping_file_path, 'rb') as f:
                    self.index_to_chunk_mapping = pickle.load(f)
                logger.info(f"Loaded mapping with {len(self.index_to_chunk_mapping)} entries")
            except FileNotFoundError:
                logger.error("Mapping file not found, falling back to old method")
                self.index_to_chunk_mapping = []
            
            # Update timestamp
            self.last_index_update = vector_index.updated_at
            
            load_time = time.time() - start_time
            logger.info(f"FAISS index loaded in {load_time:.2f} seconds")
            return True
            
        except Exception as e:
            logger.error(f"Error loading cached index: {str(e)}")
            return False

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, any]]:
        """Search for similar documents"""
        try:
            # Initialize model if needed
            if not self.model:
                if not self.initialize_model():
                    return []
            
            # Load cached index
            if not self._load_cached_index():
                return []
            
            # Create query embedding
            query_embedding = self.model.encode([query])
            
            # Search using cached index
            scores, indices = self.faiss_index.search(query_embedding, top_k)
            
            # Get results
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx != -1:  # Valid result
                    try:
                        # Use mapping to get chunk ID
                        if self.index_to_chunk_mapping and idx < len(self.index_to_chunk_mapping):
                            chunk_id = self.index_to_chunk_mapping[int(idx)]
                            chunk = DocumentChunk.objects.get(chunk_id=chunk_id)
                        else:
                            # Fallback to old method
                            chunk_idx = int(idx)
                            chunk = DocumentChunk.objects.filter(is_embedded=True).order_by('id')[chunk_idx]
                        
                        # Get case information
                        case = Case.objects.get(id=chunk.case_id)
                        
                        results.append({
                            'rank': i + 1,
                            'similarity': float(score),
                            'case_id': chunk.case_id,
                            'case_number': case.case_number,
                            'case_title': case.case_title,
                            'court': case.court.name if case.court else '',
                            'status': case.status,
                            'parties': '',  # Will be populated from related data if needed
                            'institution_date': case.institution_date,
                            'disposal_date': None,  # Not available in Case model
                            'chunk_text': chunk.chunk_text[:200] + "..." if len(chunk.chunk_text) > 200 else chunk.chunk_text,
                            'chunk_index': chunk.chunk_index,
                            'page_number': chunk.page_number
                        })
                    except (IndexError, DocumentChunk.DoesNotExist, UnifiedCaseView.DoesNotExist) as e:
                        logger.warning(f"Chunk at index {idx} not found: {str(e)}")
                        continue
            
            return results
            
        except Exception as e:
            logger.error(f"Error in vector search: {str(e)}")
            return []
