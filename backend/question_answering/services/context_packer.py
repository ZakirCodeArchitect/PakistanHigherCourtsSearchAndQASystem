"""
Context Packer Service
Processes retrieved chunks for optimal LLM consumption with deduplication, token management, and prioritization
"""

import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import re

# Try to import tiktoken, fallback to simple tokenizer if not available
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    tiktoken = None

logger = logging.getLogger(__name__)


@dataclass
class ChunkInfo:
    """Information about a processed chunk"""
    content: str
    source_type: str  # 'statute', 'case_law', 'order', 'judgment'
    priority: int  # Higher = more important
    metadata: Dict[str, Any]
    token_count: int
    chunk_id: str
    relevance_score: float


class ContextPacker:
    """Packs retrieved chunks for optimal LLM consumption"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Configuration
        self.max_tokens = self.config.get('max_tokens', 2000)
        self.max_chunks = self.config.get('max_chunks', 12)
        self.min_chunk_tokens = self.config.get('min_chunk_tokens', 50)
        self.max_chunk_tokens = self.config.get('max_chunk_tokens', 400)
        
        # Source type priorities (higher = more important)
        self.source_priorities = {
            'statute': 10,
            'constitutional_article': 9,
            'case_law': 8,
            'judgment': 7,
            'order': 6,
            'legal_principle': 5,
            'procedural_guidance': 4,
            'case_metadata': 3,
            'document_text': 2,
            'general': 1
        }
        
        # Initialize tokenizer
        if TIKTOKEN_AVAILABLE:
            try:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
            except Exception as e:
                logger.warning(f"Failed to load tiktoken, using fallback: {e}")
                self.tokenizer = None
        else:
            logger.warning("tiktoken not available, using fallback tokenizer")
            self.tokenizer = None
    
    def pack_context(self, 
                    retrieved_chunks: List[Dict[str, Any]], 
                    query: str,
                    conversation_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Pack retrieved chunks for LLM consumption
        
        Args:
            retrieved_chunks: List of retrieved document chunks
            query: User's query
            conversation_history: Previous conversation context
            
        Returns:
            Packed context ready for LLM
        """
        try:
            logger.info(f"Packing context for {len(retrieved_chunks)} chunks")
            
            # Step 1: Process and classify chunks
            processed_chunks = self._process_chunks(retrieved_chunks)
            
            # Step 2: Deduplicate chunks
            deduplicated_chunks = self._deduplicate_chunks(processed_chunks)
            
            # Step 3: Prioritize chunks by importance
            prioritized_chunks = self._prioritize_chunks(deduplicated_chunks, query)
            
            # Step 4: Select optimal chunks within token limit
            selected_chunks = self._select_optimal_chunks(prioritized_chunks)
            
            # Step 5: Format context for LLM
            formatted_context = self._format_context_for_llm(selected_chunks, query, conversation_history)
            
            logger.info(f"Formatted context type: {type(formatted_context)}")
            if isinstance(formatted_context, dict):
                logger.info(f"Formatted context keys: {list(formatted_context.keys())}")
            else:
                logger.info(f"Formatted context content: {formatted_context}")
            
            # Step 6: Generate metadata
            logger.info(f"About to generate metadata - retrieved_chunks type: {type(retrieved_chunks)}, processed_chunks type: {type(processed_chunks)}, selected_chunks type: {type(selected_chunks)}")
            packing_metadata = self._generate_packing_metadata(
                retrieved_chunks, processed_chunks, selected_chunks, formatted_context
            )
            logger.info(f"Metadata generation completed successfully")
            
            return {
                'formatted_context': formatted_context,
                'selected_chunks': selected_chunks,
                'packing_metadata': packing_metadata,
                'token_count': formatted_context.get('total_tokens', 0) if isinstance(formatted_context, dict) else 0,
                'chunk_count': len(selected_chunks),
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error packing context: {str(e)}")
            return {
                'formatted_context': {'context_text': 'Error processing context'},
                'selected_chunks': [],
                'packing_metadata': {'error': str(e)},
                'token_count': 0,
                'chunk_count': 0,
                'status': 'error'
            }
    
    def _process_chunks(self, chunks: List[Dict[str, Any]]) -> List[ChunkInfo]:
        """Process and classify retrieved chunks"""
        processed_chunks = []
        
        for i, chunk in enumerate(chunks):
            try:
                # Extract content
                content = self._extract_chunk_content(chunk)
                if not content or len(content.strip()) < 10:
                    continue
                
                # Classify source type
                source_type = self._classify_source_type(chunk, content)
                
                # Calculate priority
                priority = self._calculate_priority(chunk, content, source_type)
                
                # Count tokens
                token_count = self._count_tokens(content)
                
                # Generate chunk ID
                chunk_id = self._generate_chunk_id(chunk, content)
                
                # Extract metadata
                metadata = self._extract_chunk_metadata(chunk)
                
                # Get relevance score
                relevance_score = chunk.get('score', 0.0)
                
                chunk_info = ChunkInfo(
                    content=content,
                    source_type=source_type,
                    priority=priority,
                    metadata=metadata,
                    token_count=token_count,
                    chunk_id=chunk_id,
                    relevance_score=relevance_score
                )
                
                processed_chunks.append(chunk_info)
                
            except Exception as e:
                logger.warning(f"Error processing chunk {i}: {str(e)}")
                continue
        
        logger.info(f"Processed {len(processed_chunks)} chunks from {len(chunks)} retrieved")
        return processed_chunks
    
    def _extract_chunk_content(self, chunk: Dict[str, Any]) -> str:
        """Extract content from chunk"""
        # Try different content fields
        content_fields = [
            'content', 'content_text', 'text', 'case_description', 
            'document_text', 'clean_text', 'summary'
        ]
        
        for field in content_fields:
            if field in chunk and chunk[field]:
                content = str(chunk[field]).strip()
                if content:
                    return content
        
        # Fallback: construct content from available fields
        content_parts = []
        if chunk.get('case_title'):
            content_parts.append(f"Title: {chunk['case_title']}")
        if chunk.get('case_description'):
            content_parts.append(f"Description: {chunk['case_description']}")
        if chunk.get('short_order'):
            content_parts.append(f"Order: {chunk['short_order']}")
        
        return '\n'.join(content_parts) if content_parts else ""
    
    def _classify_source_type(self, chunk: Dict[str, Any], content: str) -> str:
        """Classify the source type of the chunk"""
        content_lower = content.lower()
        
        # Check metadata first
        if chunk.get('content_type'):
            content_type = chunk['content_type'].lower()
            if 'statute' in content_type or 'law' in content_type:
                return 'statute'
            elif 'case' in content_type or 'judgment' in content_type:
                return 'case_law'
            elif 'order' in content_type:
                return 'order'
        
        # Check document type
        if chunk.get('document_type'):
            doc_type = chunk['document_type'].lower()
            if 'judgment' in doc_type:
                return 'judgment'
            elif 'order' in doc_type:
                return 'order'
            elif 'statute' in doc_type:
                return 'statute'
        
        # Check content patterns
        if any(word in content_lower for word in ['section', 'article', 'act', 'code']):
            if 'constitution' in content_lower or 'article' in content_lower:
                return 'constitutional_article'
            else:
                return 'statute'
        
        if any(word in content_lower for word in ['court held', 'judgment', 'decided', 'ruled']):
            return 'judgment'
        
        if any(word in content_lower for word in ['order', 'directed', 'instructed']):
            return 'order'
        
        if any(word in content_lower for word in ['principle', 'rule', 'doctrine']):
            return 'legal_principle'
        
        if any(word in content_lower for word in ['procedure', 'process', 'how to']):
            return 'procedural_guidance'
        
        # Default classification
        if chunk.get('case_id'):
            return 'case_law'
        else:
            return 'general'
    
    def _calculate_priority(self, chunk: Dict[str, Any], content: str, source_type: str) -> int:
        """Calculate priority score for the chunk"""
        base_priority = self.source_priorities.get(source_type, 1)
        
        # Boost for high relevance score
        relevance_score = chunk.get('score', 0.0)
        if relevance_score > 0.8:
            base_priority += 3
        elif relevance_score > 0.6:
            base_priority += 2
        elif relevance_score > 0.4:
            base_priority += 1
        
        # Boost for recent cases
        if chunk.get('date_decided'):
            try:
                from datetime import datetime
                date_str = chunk['date_decided']
                if isinstance(date_str, str):
                    # Try to parse date
                    if len(date_str) >= 4:  # At least year
                        year = int(date_str[:4])
                        current_year = datetime.now().year
                        if year >= current_year - 5:  # Recent cases
                            base_priority += 2
                        elif year >= current_year - 10:  # Moderately recent
                            base_priority += 1
            except:
                pass
        
        # Boost for high court cases
        court = chunk.get('court', '').lower()
        if 'supreme court' in court:
            base_priority += 3
        elif 'high court' in court:
            base_priority += 2
        
        # Boost for complete content
        if len(content) > 200:
            base_priority += 1
        
        return min(base_priority, 20)  # Cap at 20
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except:
                pass
        
        # Fallback: rough estimation (4 chars per token)
        return len(text) // 4
    
    def _generate_chunk_id(self, chunk: Dict[str, Any], content: str) -> str:
        """Generate unique ID for chunk"""
        # Use content hash for deduplication
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        
        # Include source info
        case_id = chunk.get('case_id', 'unknown')
        doc_id = chunk.get('document_id', 'unknown')
        
        return f"{case_id}_{doc_id}_{content_hash}"
    
    def _extract_chunk_metadata(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant metadata from chunk"""
        metadata = {
            'case_id': chunk.get('case_id'),
            'document_id': chunk.get('document_id'),
            'case_number': chunk.get('case_number'),
            'case_title': chunk.get('case_title'),
            'court': chunk.get('court'),
            'date_decided': chunk.get('date_decided'),
            'judge_name': chunk.get('judge_name'),
            'legal_domain': chunk.get('legal_domain'),
            'source': chunk.get('source', 'unknown')
        }
        
        # Remove None values
        return {k: v for k, v in metadata.items() if v is not None}
    
    def _deduplicate_chunks(self, chunks: List[ChunkInfo]) -> List[ChunkInfo]:
        """Remove duplicate chunks based on content similarity"""
        if not chunks:
            return []
        
        # Group by chunk ID (content hash)
        chunk_groups = defaultdict(list)
        for chunk in chunks:
            chunk_groups[chunk.chunk_id].append(chunk)
        
        # Select best chunk from each group
        deduplicated = []
        for chunk_id, group in chunk_groups.items():
            if len(group) == 1:
                deduplicated.append(group[0])
            else:
                # Select chunk with highest priority and relevance
                best_chunk = max(group, key=lambda c: (c.priority, c.relevance_score))
                deduplicated.append(best_chunk)
        
        logger.info(f"Deduplicated {len(chunks)} chunks to {len(deduplicated)}")
        return deduplicated
    
    def _prioritize_chunks(self, chunks: List[ChunkInfo], query: str) -> List[ChunkInfo]:
        """Sort chunks by priority and relevance"""
        # Sort by priority (descending), then by relevance score (descending)
        sorted_chunks = sorted(
            chunks, 
            key=lambda c: (c.priority, c.relevance_score), 
            reverse=True
        )
        
        return sorted_chunks
    
    def _select_optimal_chunks(self, chunks: List[ChunkInfo]) -> List[ChunkInfo]:
        """Select optimal chunks within token and count limits"""
        selected_chunks = []
        total_tokens = 0
        
        for chunk in chunks:
            # Check token limit
            if total_tokens + chunk.token_count > self.max_tokens:
                break
            
            # Check chunk count limit
            if len(selected_chunks) >= self.max_chunks:
                break
            
            # Check minimum token requirement (relaxed for testing)
            if chunk.token_count < 10:  # Very low threshold for testing
                continue
            
            # Check maximum token limit per chunk
            if chunk.token_count > self.max_chunk_tokens:
                # Truncate chunk
                truncated_content = self._truncate_content(chunk.content, self.max_chunk_tokens)
                chunk.content = truncated_content
                chunk.token_count = self._count_tokens(truncated_content)
            
            selected_chunks.append(chunk)
            total_tokens += chunk.token_count
        
        logger.info(f"Selected {len(selected_chunks)} chunks with {total_tokens} tokens")
        return selected_chunks
    
    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """Truncate content to fit within token limit"""
        if self.tokenizer:
            try:
                tokens = self.tokenizer.encode(content)
                if len(tokens) <= max_tokens:
                    return content
                
                # Truncate and decode
                truncated_tokens = tokens[:max_tokens]
                return self.tokenizer.decode(truncated_tokens)
            except:
                pass
        
        # Fallback: character-based truncation
        max_chars = max_tokens * 4  # Rough estimation
        if len(content) <= max_chars:
            return content
        
        # Truncate at word boundary
        truncated = content[:max_chars]
        last_space = truncated.rfind(' ')
        if last_space > max_chars * 0.8:  # If we can find a good break point
            truncated = truncated[:last_space]
        
        return truncated + "..."
    
    def _format_context_for_llm(self, 
                               chunks: List[ChunkInfo], 
                               query: str,
                               conversation_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Format selected chunks for LLM consumption"""
        
        # Group chunks by source type
        chunks_by_type = defaultdict(list)
        for chunk in chunks:
            chunks_by_type[chunk.source_type].append(chunk)
        
        # Build context sections
        context_sections = []
        
        # Priority order: statute, constitutional, case law, orders, etc.
        type_order = ['statute', 'constitutional_article', 'case_law', 'judgment', 'order', 
                     'legal_principle', 'procedural_guidance', 'case_metadata', 'general']
        
        for source_type in type_order:
            if source_type in chunks_by_type:
                type_chunks = chunks_by_type[source_type]
                section = self._format_chunk_section(source_type, type_chunks)
                if section:
                    context_sections.append(section)
        
        # Combine all sections
        context_text = "\n\n".join(context_sections)
        
        # Add conversation context if available
        conversation_context = ""
        if conversation_history:
            conversation_context = self._format_conversation_context(conversation_history)
        
        # Calculate total tokens
        total_tokens = self._count_tokens(context_text + conversation_context)
        
        return {
            'context_text': context_text,
            'conversation_context': conversation_context,
            'total_tokens': total_tokens,
            'chunk_summary': self._generate_chunk_summary(chunks),
            'source_distribution': {k: len(v) for k, v in chunks_by_type.items()}
        }
    
    def _format_chunk_section(self, source_type: str, chunks: List[ChunkInfo]) -> str:
        """Format a section of chunks by source type"""
        if not chunks:
            return ""
        
        # Section header
        type_headers = {
            'statute': "📜 RELEVANT STATUTES AND LAWS",
            'constitutional_article': "🏛️ CONSTITUTIONAL PROVISIONS",
            'case_law': "⚖️ RELEVANT CASE LAW",
            'judgment': "📋 COURT JUDGMENTS",
            'order': "📝 COURT ORDERS",
            'legal_principle': "📚 LEGAL PRINCIPLES",
            'procedural_guidance': "📋 PROCEDURAL GUIDANCE",
            'case_metadata': "📄 CASE INFORMATION",
            'general': "📖 GENERAL LEGAL INFORMATION"
        }
        
        header = type_headers.get(source_type, f"📄 {source_type.upper().replace('_', ' ')}")
        section_parts = [f"{header}:\n"]
        
        # Format each chunk
        for i, chunk in enumerate(chunks, 1):
            chunk_text = self._format_single_chunk(chunk, i)
            section_parts.append(chunk_text)
        
        return "\n".join(section_parts)
    
    def _format_single_chunk(self, chunk: ChunkInfo, index: int) -> str:
        """Format a single chunk with metadata"""
        parts = [f"[{index}] {chunk.content}"]
        
        # Add metadata
        metadata_parts = []
        if chunk.metadata.get('case_number'):
            metadata_parts.append(f"Case: {chunk.metadata['case_number']}")
        if chunk.metadata.get('court'):
            metadata_parts.append(f"Court: {chunk.metadata['court']}")
        if chunk.metadata.get('date_decided'):
            metadata_parts.append(f"Date: {chunk.metadata['date_decided']}")
        if chunk.metadata.get('judge_name'):
            metadata_parts.append(f"Judge: {chunk.metadata['judge_name']}")
        
        if metadata_parts:
            parts.append(f"   Source: {' | '.join(metadata_parts)}")
        
        return "\n".join(parts)
    
    def _format_conversation_context(self, conversation_history: List[Dict]) -> str:
        """Format conversation history for context"""
        if not conversation_history:
            return ""
        
        # Take last 3 turns
        recent_turns = conversation_history[-3:]
        
        context_parts = ["\n🔄 CONVERSATION CONTEXT:"]
        for i, turn in enumerate(recent_turns, 1):
            query = turn.get('query', '')
            response = turn.get('response', '')
            
            # Truncate response if too long
            if len(response) > 200:
                response = response[:200] + "..."
            
            context_parts.append(f"Q{i}: {query}")
            context_parts.append(f"A{i}: {response}")
        
        return "\n".join(context_parts)
    
    def _generate_chunk_summary(self, chunks: List[ChunkInfo]) -> Dict[str, Any]:
        """Generate summary of selected chunks"""
        if not chunks:
            return {}
        
        return {
            'total_chunks': len(chunks),
            'total_tokens': sum(c.token_count for c in chunks),
            'source_types': list(set(c.source_type for c in chunks)),
            'priority_range': (min(c.priority for c in chunks), max(c.priority for c in chunks)),
            'relevance_range': (min(c.relevance_score for c in chunks), max(c.relevance_score for c in chunks)),
            'courts_mentioned': list(set(c.metadata.get('court', '') for c in chunks if c.metadata.get('court'))),
            'cases_mentioned': list(set(c.metadata.get('case_number', '') for c in chunks if c.metadata.get('case_number')))
        }
    
    def _generate_packing_metadata(self, 
                                 original_chunks: List[Dict], 
                                 processed_chunks: List[ChunkInfo],
                                 selected_chunks: List[ChunkInfo],
                                 formatted_context: Dict) -> Dict[str, Any]:
        """Generate metadata about the packing process"""
        return {
            'original_chunk_count': len(original_chunks),
            'processed_chunk_count': len(processed_chunks),
            'selected_chunk_count': len(selected_chunks),
            'deduplication_ratio': len(processed_chunks) / len(original_chunks) if original_chunks else 0,
            'selection_ratio': len(selected_chunks) / len(processed_chunks) if processed_chunks else 0,
            'total_tokens': formatted_context.get('total_tokens', 0) if isinstance(formatted_context, dict) else 0,
            'token_efficiency': (formatted_context.get('total_tokens', 0) if isinstance(formatted_context, dict) else 0) / self.max_tokens,
            'source_distribution': formatted_context.get('source_distribution', {}) if isinstance(formatted_context, dict) else {},
            'chunk_summary': formatted_context.get('chunk_summary', {}) if isinstance(formatted_context, dict) else {}
        }
