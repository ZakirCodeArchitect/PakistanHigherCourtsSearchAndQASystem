"""
Knowledge Retriever Service
Retrieves legal knowledge from PostgreSQL database and integrates with RAG
"""

import logging
from typing import List, Dict, Any, Optional
from django.db import connection
from .rag_service import RAGService

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """Retrieves legal knowledge from the actual crawled database"""
    
    def __init__(self):
        """Initialize knowledge retriever with RAG service"""
        self.rag_service = RAGService()
    
    def search_legal_cases(self, query: str, top_k: int = 5, 
                          court_filter: Optional[str] = None,
                          status_filter: Optional[str] = None,
                          year_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search legal cases using RAG and database filters"""
        
        try:
            # Try RAG search first if available
            if self.rag_service and self.rag_service.pinecone_index:
                logger.info(f"Using RAG search for query: '{query[:50]}...'")
                rag_results = self.rag_service.search_similar_documents(query, top_k)
                
                if rag_results:
                    # Enhance RAG results with additional database information
                    enhanced_results = self._enhance_rag_results(rag_results)
                    logger.info(f"RAG search found {len(enhanced_results)} results")
                    return enhanced_results
                else:
                    logger.info("RAG search returned no results, falling back to database search")
            
            # Fallback to database search
            logger.info(f"Using database search for query: '{query[:50]}...'")
            return self._database_search(query, top_k, court_filter, status_filter, year_filter)
                    
        except Exception as e:
            logger.error(f"Error in knowledge retrieval: {str(e)}")
            return []
    
    def _enhance_rag_results(self, rag_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance RAG results with additional case details from database"""
        enhanced_results = []
        
        for result in rag_results:
            try:
                case_id = result.get('case_id')
                if not case_id:
                    continue
                
                # Get additional case details from database
                case_details = self._get_case_details(case_id)
                if case_details:
                    # Merge RAG result with database details
                    enhanced_result = {**result, **case_details}
                    enhanced_results.append(enhanced_result)
                    
            except Exception as e:
                logger.error(f"Error enhancing RAG result: {str(e)}")
                enhanced_results.append(result)  # Return original result
        
        return enhanced_results
    
    def _get_case_details(self, case_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed case information from database"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        c.id,
                        c.sr_number,
                        c.case_number,
                        c.case_title,
                        c.bench,
                        c.hearing_date,
                        c.status,
                        c.institution_date,
                        ct.name as court_name,
                        cd.case_description,
                        cd.case_stage,
                        cd.short_order,
                        cd.disposed_of_status,
                        cd.case_disposal_date,
                        cd.disposal_bench,
                        cd.advocates_petitioner,
                        cd.advocates_respondent,
                        cd.fir_number,
                        cd.fir_date,
                        cd.police_station,
                        cd.under_section,
                        cd.incident,
                        cd.name_of_accused
                    FROM cases c
                    LEFT JOIN courts ct ON c.court_id = ct.id
                    LEFT JOIN case_details cd ON c.id = cd.case_id
                    WHERE c.id = %s
                """, [case_id])
                
                row = cursor.fetchone()
                if row:
                    return {
                        'case_id': row[0],
                        'sr_number': row[1],
                        'case_number': row[2],
                        'case_title': row[3],
                        'bench': row[4],
                        'hearing_date': row[5],
                        'status': row[6],
                        'institution_date': row[7],
                        'court_name': row[8],
                        'case_description': row[9],
                        'case_stage': row[10],
                        'short_order': row[11],
                        'disposed_of_status': row[12],
                        'case_disposal_date': row[13],
                        'disposal_bench': row[14],
                        'advocates_petitioner': row[15],
                        'advocates_respondent': row[16],
                        'fir_number': row[17],
                        'fir_date': row[18],
                        'police_station': row[19],
                        'under_section': row[20],
                        'incident': row[21],
                        'name_of_accused': row[22]
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error getting case details for case {case_id}: {str(e)}")
            return None
    
    def _database_search(self, query: str, top_k: int, court_filter: Optional[str] = None,
                        status_filter: Optional[str] = None, year_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search QA knowledge base using PostgreSQL full-text search"""
        try:
            with connection.cursor() as cursor:
                # Build the query with filters
                where_conditions = []
                params = []
                
                # Text search conditions in knowledge base
                text_search = """
                    (kb.title ILIKE %s OR 
                     kb.content_text ILIKE %s OR 
                     kb.content_summary ILIKE %s OR
                     kb.case_title ILIKE %s OR
                     kb.case_number ILIKE %s)
                """
                where_conditions.append(text_search)
                params.extend([f'%{query}%'] * 5)
                
                # Court filter
                if court_filter:
                    where_conditions.append("kb.court ILIKE %s")
                    params.append(f'%{court_filter}%')
                
                # Status filter (if we had status in knowledge base)
                # if status_filter:
                #     where_conditions.append("kb.status ILIKE %s")
                #     params.append(f'%{status_filter}%')
                
                # Year filter (if we had year in knowledge base)
                # if year_filter:
                #     where_conditions.append("EXTRACT(YEAR FROM kb.date_decided) = %s")
                #     params.append(year_filter)
                
                # Combine conditions
                where_clause = " AND ".join(where_conditions)
                
                # Main query on knowledge base
                sql = f"""
                    SELECT 
                        kb.id,
                        kb.source_case_id,
                        kb.source_document_id,
                        kb.source_type,
                        kb.title,
                        kb.content_text,
                        kb.content_summary,
                        kb.court,
                        kb.case_number,
                        kb.case_title,
                        kb.judge_name,
                        kb.date_decided,
                        kb.legal_domain,
                        kb.content_quality_score,
                        kb.legal_relevance_score,
                        kb.completeness_score,
                        -- Calculate relevance score
                        CASE 
                            WHEN kb.title ILIKE %s THEN 1.0
                            WHEN kb.case_title ILIKE %s THEN 0.9
                            WHEN kb.content_text ILIKE %s THEN 0.8
                            WHEN kb.content_summary ILIKE %s THEN 0.7
                            WHEN kb.case_number ILIKE %s THEN 0.6
                            ELSE 0.5
                        END as relevance_score
                    FROM qa_knowledge_base kb
                    WHERE {where_clause}
                    ORDER BY relevance_score DESC, kb.content_quality_score DESC
                    LIMIT %s
                """
                
                # Add relevance score parameters
                params.extend([f'%{query}%'] * 5)
                params.append(top_k)
                
                cursor.execute(sql, params)
                
                results = []
                for row in cursor.fetchall():
                    result = {
                        'kb_id': row[0],
                        'case_id': row[1],
                        'document_id': row[2],
                        'source_type': row[3],
                        'title': row[4],
                        'content_text': row[5],
                        'content_summary': row[6],
                        'court_name': row[7],
                        'case_number': row[8],
                        'case_title': row[9],
                        'judge_name': row[10],
                        'date_decided': row[11],
                        'legal_domain': row[12],
                        'content_quality_score': row[13],
                        'legal_relevance_score': row[14],
                        'completeness_score': row[15],
                        'relevance_score': row[16],
                        'score': row[16],  # For compatibility with RAG results
                        'search_method': 'knowledge_base'
                    }
                    results.append(result)
                
                logger.info(f"Knowledge base search found {len(results)} results for query: '{query[:50]}...'")
                return results
                
        except Exception as e:
            logger.error(f"Error in knowledge base search: {str(e)}")
            return []
    
    def get_case_documents(self, case_id: int) -> List[Dict[str, Any]]:
        """Get all documents associated with a case"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        d.id,
                        d.file_name,
                        d.file_path,
                        d.original_url,
                        d.total_pages,
                        cdoc.document_type,
                        cdoc.document_title,
                        cdoc.source_table,
                        dt.page_number,
                        dt.clean_text
                    FROM case_documents cdoc
                    JOIN documents d ON cdoc.document_id = d.id
                    LEFT JOIN document_texts dt ON d.id = dt.document_id
                    WHERE cdoc.case_id = %s
                    ORDER BY d.id, dt.page_number
                """, [case_id])
                
                documents = {}
                for row in cursor.fetchall():
                    doc_id = row[0]
                    if doc_id not in documents:
                        documents[doc_id] = {
                            'document_id': row[0],
                            'file_name': row[1],
                            'file_path': row[2],
                            'original_url': row[3],
                            'total_pages': row[4],
                            'document_type': row[5],
                            'document_title': row[6],
                            'source_table': row[7],
                            'pages': []
                        }
                    
                    if row[8] and row[9]:  # page_number and clean_text
                        documents[doc_id]['pages'].append({
                            'page_number': row[8],
                            'text': row[9]
                        })
                
                return list(documents.values())
                
        except Exception as e:
            logger.error(f"Error getting documents for case {case_id}: {str(e)}")
            return []
    
    def get_case_orders(self, case_id: int) -> List[Dict[str, Any]]:
        """Get all orders for a case"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        sr_number,
                        hearing_date,
                        bench,
                        list_type,
                        case_stage,
                        short_order,
                        disposal_date,
                        view_link
                    FROM orders_data
                    WHERE case_id = %s
                    ORDER BY hearing_date DESC
                """, [case_id])
                
                orders = []
                for row in cursor.fetchall():
                    order = {
                        'sr_number': row[0],
                        'hearing_date': row[1],
                        'bench': row[2],
                        'list_type': row[3],
                        'case_stage': row[4],
                        'short_order': row[5],
                        'disposal_date': row[6],
                        'view_link': row[7]
                    }
                    orders.append(order)
                
                return orders
                
        except Exception as e:
            logger.error(f"Error getting orders for case {case_id}: {str(e)}")
            return []
    
    def get_case_comments(self, case_id: int) -> List[Dict[str, Any]]:
        """Get all comments for a case"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        compliance_date,
                        case_no,
                        case_title,
                        doc_type,
                        parties,
                        description,
                        view_link
                    FROM comments_data
                    WHERE case_id = %s
                    ORDER BY compliance_date DESC
                """, [case_id])
                
                comments = []
                for row in cursor.fetchall():
                    comment = {
                        'compliance_date': row[0],
                        'case_no': row[1],
                        'case_title': row[2],
                        'doc_type': row[3],
                        'parties': row[4],
                        'description': row[5],
                        'view_link': row[6]
                    }
                    comments.append(comment)
                
                return comments
                
        except Exception as e:
            logger.error(f"Error getting comments for case {case_id}: {str(e)}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with connection.cursor() as cursor:
                # Get case count
                cursor.execute("SELECT COUNT(*) FROM cases")
                total_cases = cursor.fetchone()[0]
                
                # Get document count
                cursor.execute("SELECT COUNT(*) FROM documents")
                total_documents = cursor.fetchone()[0]
                
                # Get court distribution
                cursor.execute("""
                    SELECT ct.name, COUNT(c.id) 
                    FROM cases c 
                    LEFT JOIN courts ct ON c.court_id = ct.id 
                    GROUP BY ct.name 
                    ORDER BY COUNT(c.id) DESC
                """)
                court_distribution = dict(cursor.fetchall())
                
                # Get status distribution
                cursor.execute("""
                    SELECT status, COUNT(*) 
                    FROM cases 
                    WHERE status IS NOT NULL 
                    GROUP BY status 
                    ORDER BY COUNT(*) DESC
                """)
                status_distribution = dict(cursor.fetchall())
                
            return {
                'total_cases': total_cases,
                'total_documents': total_documents,
                'court_distribution': court_distribution,
                'status_distribution': status_distribution,
                'rag_status': {'enabled': False, 'reason': 'dependency_issues'}
            }
                
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {
                'total_cases': 0,
                'total_documents': 0,
                'court_distribution': {},
                'status_distribution': {},
                'rag_status': {'enabled': False, 'reason': 'dependency_issues'}
            }