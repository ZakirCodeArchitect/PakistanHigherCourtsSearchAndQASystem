import os
import hashlib
import requests
import fitz  # PyMuPDF
import re
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
import time

from ..models import Document, CaseDocument, DocumentText, Case, OrdersData, CommentsData, JudgementData

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Handles PDF downloading, text extraction, and cleaning"""
    
    def __init__(self, download_dir: str = None):
        self.download_dir = download_dir or os.path.join(settings.BASE_DIR, 'data', 'pdfs')
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Text cleaning patterns
        self.header_footer_patterns = [
            r'Page \d+ of \d+',
            r'^\d+$',  # Page numbers
            r'^[A-Z\s]+ COURT$',  # Court headers
            r'^.*\d{4}.*$',  # Date headers
        ]
        
        self.watermark_patterns = [
            r'CONFIDENTIAL',
            r'DRAFT',
            r'COPY',
            r'ORIGINAL',
        ]
    
    def download_pdf(self, url: str, case_number: str = None) -> Optional[Document]:
        """Download PDF and create Document record"""
        try:
            # Generate filename from URL
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename or not filename.endswith('.pdf'):
                filename = f"document_{int(time.time())}.pdf"
            
            # Create file path
            file_path = os.path.join(self.download_dir, filename)
            
            # Check if file already exists
            if os.path.exists(file_path):
                logger.info(f"File already exists: {file_path}")
                return self._get_existing_document(file_path, url)
            
            # Download file
            logger.info(f"Downloading PDF from: {url}")
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Save file
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Calculate file metadata
            file_size = os.path.getsize(file_path)
            sha256_hash = self._calculate_sha256(file_path)
            
            # Check if document with same hash already exists
            existing_doc = Document.objects.filter(sha256_hash=sha256_hash).first()
            if existing_doc:
                logger.info(f"Document with same hash already exists: {existing_doc.file_name}")
                os.remove(file_path)  # Remove duplicate
                return existing_doc
            
            # Create Document record
            document = Document.objects.create(
                file_path=file_path,
                file_name=filename,
                file_size=file_size,
                sha256_hash=sha256_hash,
                original_url=url,
                is_downloaded=True
            )
            
            logger.info(f"Successfully downloaded and created document: {document.id}")
            return document
            
        except Exception as e:
            logger.error(f"Error downloading PDF from {url}: {str(e)}")
            # Create Document record with error
            document = Document.objects.create(
                file_path="",
                file_name=os.path.basename(urlparse(url).path) or "unknown.pdf",
                file_size=0,
                sha256_hash="",
                original_url=url,
                is_downloaded=False,
                download_error=str(e)
            )
            return document
    
    def extract_text_from_pdf(self, document: Document) -> bool:
        """Extract text from PDF using PyMuPDF with OCR fallback"""
        try:
            if not document.is_downloaded or not os.path.exists(document.file_path):
                logger.error(f"Document not downloaded or file missing: {document.file_path}")
                return False
            
            logger.info(f"Extracting text from: {document.file_name}")
            
            # Open PDF
            pdf_document = fitz.open(document.file_path)
            total_pages = len(pdf_document)
            
            # Update document with page count
            document.total_pages = total_pages
            document.save()
            
            # Extract text from each page
            for page_num in range(total_pages):
                page = pdf_document[page_num]
                start_time = time.time()
                
                # Try text extraction first
                text = page.get_text()
                extraction_method = 'pymupdf'
                confidence_score = self._calculate_pymupdf_confidence(text)
                needs_ocr = False
                
                # Check if text extraction was successful
                if not text or len(text.strip()) < 50:  # Threshold for minimal text
                    logger.warning(f"Page {page_num + 1} has insufficient text, attempting OCR")
                    needs_ocr = True
                    text, confidence_score = self._extract_with_ocr(page)
                    extraction_method = 'ocr'
                
                processing_time = time.time() - start_time
                
                # Create or update DocumentText record
                doc_text, created = DocumentText.objects.get_or_create(
                    document=document,
                    page_number=page_num + 1,
                    defaults={
                        'raw_text': text,
                        'extraction_method': extraction_method,
                        'confidence_score': confidence_score,
                        'processing_time': processing_time,
                        'has_text': bool(text and len(text.strip()) > 0),
                        'needs_ocr': needs_ocr
                    }
                )
                
                # Update existing record if it already exists
                if not created:
                    doc_text.raw_text = text
                    doc_text.extraction_method = extraction_method
                    doc_text.confidence_score = confidence_score
                    doc_text.processing_time = processing_time
                    doc_text.has_text = bool(text and len(text.strip()) > 0)
                    doc_text.needs_ocr = needs_ocr
                    doc_text.save()
            
            pdf_document.close()
            
            # Mark document as processed
            document.is_processed = True
            document.save()
            
            logger.info(f"Successfully extracted text from {total_pages} pages")
            return True
            
        except Exception as e:
            logger.error(f"Error extracting text from {document.file_name}: {str(e)}")
            document.processing_error = str(e)
            document.save()
            return False
    
    def _calculate_pymupdf_confidence(self, text: str) -> float:
        """Calculate confidence score for PyMuPDF extraction"""
        if not text:
            return 0.0
        
        # Simple heuristics for confidence scoring
        confidence = 1.0
        
        # Reduce confidence for very short text
        if len(text.strip()) < 100:
            confidence *= 0.7
        
        # Reduce confidence for text with many special characters
        special_char_ratio = len([c for c in text if not c.isalnum() and not c.isspace()]) / len(text)
        if special_char_ratio > 0.3:
            confidence *= 0.8
        
        # Reduce confidence for text with many numbers (might be scanned)
        digit_ratio = len([c for c in text if c.isdigit()]) / len(text)
        if digit_ratio > 0.2:
            confidence *= 0.9
        
        # Increase confidence for text with proper sentence structure
        sentences = text.split('.')
        if len(sentences) > 2:
            confidence *= 1.1
        
        return min(confidence, 1.0)
    
    def _extract_with_ocr(self, page) -> tuple[str, float]:
        """Extract text using OCR with confidence score"""
        try:
            # Convert page to image
            pix = page.get_pixmap()
            img_data = pix.tobytes("png")
            
            # Use pytesseract for OCR
            import pytesseract
            from PIL import Image
            import io
            
            # Convert bytes to PIL Image
            img = Image.open(io.BytesIO(img_data))
            
            # Extract text with confidence scores
            ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            
            # Combine text and calculate average confidence
            text_parts = []
            confidences = []
            
            for i, conf in enumerate(ocr_data['conf']):
                if conf > 0:  # Only include text with confidence > 0
                    text_parts.append(ocr_data['text'][i])
                    confidences.append(conf)
            
            text = ' '.join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Normalize confidence to 0-1 range
            normalized_confidence = avg_confidence / 100.0
            
            return text, normalized_confidence
            
        except Exception as e:
            logger.warning(f"OCR extraction failed: {str(e)}")
            return "", 0.0
    
    def clean_text(self, document: Document) -> bool:
        """Clean extracted text by removing headers, footers, watermarks, etc."""
        try:
            logger.info(f"Cleaning text for: {document.file_name}")
            
            document_texts = DocumentText.objects.filter(document=document)
            
            for doc_text in document_texts:
                clean_text = self._clean_single_page_text(doc_text.raw_text)
                
                doc_text.clean_text = clean_text
                doc_text.is_cleaned = True
                doc_text.save()
            
            # Mark document as cleaned
            document.is_cleaned = True
            document.save()
            
            logger.info(f"Successfully cleaned text for {document.file_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning text for {document.file_name}: {str(e)}")
            return False
    
    def _clean_single_page_text(self, text: str) -> str:
        """Clean text from a single page"""
        if not text:
            return ""
        
        # Remove headers and footers
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Skip header/footer patterns
            if any(re.match(pattern, line, re.IGNORECASE) for pattern in self.header_footer_patterns):
                continue
            
            # Remove watermarks
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in self.watermark_patterns):
                continue
            
            cleaned_lines.append(line)
        
        # Join lines and clean up
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Fix hyphenated words
        cleaned_text = self._fix_hyphenated_words(cleaned_text)
        
        # Normalize whitespace
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        
        # Normalize Unicode
        cleaned_text = cleaned_text.encode('utf-8', errors='ignore').decode('utf-8')
        
        return cleaned_text.strip()
    
    def _fix_hyphenated_words(self, text: str) -> str:
        """Fix hyphenated words at line breaks"""
        # Pattern to match hyphenated words at line breaks
        pattern = r'(\w+)-\s*\n\s*(\w+)'
        
        def replace_hyphenated(match):
            return match.group(1) + match.group(2)
        
        return re.sub(pattern, replace_hyphenated, text)
    
    def _calculate_sha256(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _get_existing_document(self, file_path: str, url: str) -> Optional[Document]:
        """Get existing document by file path or create new one"""
        existing = Document.objects.filter(file_path=file_path).first()
        if existing:
            return existing
        
        # Create new document record for existing file
        file_size = os.path.getsize(file_path)
        sha256_hash = self._calculate_sha256(file_path)
        
        return Document.objects.create(
            file_path=file_path,
            file_name=os.path.basename(file_path),
            file_size=file_size,
            sha256_hash=sha256_hash,
            original_url=url,
            is_downloaded=True
        )


class PDFLinkExtractor:
    """Extract PDF links from case data and create Document records"""
    
    def __init__(self):
        self.pdf_processor = PDFProcessor()
    
    def extract_pdf_links_from_cases(self, limit: int = None) -> Dict[str, int]:
        """Extract PDF links from all cases and create Document records"""
        stats = {
            'total_cases_processed': 0,
            'total_pdfs_found': 0,
            'total_documents_created': 0,
            'total_case_documents_created': 0,
            'errors': 0
        }
        
        # Process orders_data
        orders_stats = self._extract_from_orders_data(limit)
        stats.update(orders_stats)
        
        # Process comments_data
        comments_stats = self._extract_from_comments_data(limit)
        for key in stats:
            if key in comments_stats:
                stats[key] += comments_stats[key]
        
        # Process judgement_data
        judgement_stats = self._extract_from_judgement_data(limit)
        for key in stats:
            if key in judgement_stats:
                stats[key] += judgement_stats[key]
        
        return stats
    
    def _extract_from_orders_data(self, limit: int = None) -> Dict[str, int]:
        """Extract PDF links from orders_data table"""
        stats = {
            'total_cases_processed': 0,
            'total_pdfs_found': 0,
            'total_documents_created': 0,
            'total_case_documents_created': 0,
            'errors': 0
        }
        
        queryset = OrdersData.objects.filter(view_link__isnull=False).exclude(view_link=[])
        
        for order in queryset:
            try:
                stats['total_cases_processed'] += 1
                
                if not order.view_link:
                    continue
                
                for link_index, link_obj in enumerate(order.view_link):
                    if not isinstance(link_obj, dict):
                        continue
                    
                    href = link_obj.get('href', '')
                    if not href or not href.lower().endswith('.pdf'):
                        continue
                    
                    stats['total_pdfs_found'] += 1
                    
                    # Download PDF
                    document = self.pdf_processor.download_pdf(href, order.case.case_number)
                    if document and document.is_downloaded:
                        stats['total_documents_created'] += 1
                        
                        # Create CaseDocument relationship
                        case_doc, created = CaseDocument.objects.get_or_create(
                            case=order.case,
                            document=document,
                            source_table='orders_data',
                            source_row_id=order.id,
                            source_link_index=link_index,
                            defaults={
                                'document_type': 'order',
                                'document_title': link_obj.get('title', '') or link_obj.get('text', '')
                            }
                        )
                        
                        if created:
                            stats['total_case_documents_created'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing order {order.id}: {str(e)}")
                stats['errors'] += 1
        
        return stats
    
    def _extract_from_comments_data(self, limit: int = None) -> Dict[str, int]:
        """Extract PDF links from comments_data table"""
        stats = {
            'total_cases_processed': 0,
            'total_pdfs_found': 0,
            'total_documents_created': 0,
            'total_case_documents_created': 0,
            'errors': 0
        }
        
        queryset = CommentsData.objects.filter(view_link__isnull=False).exclude(view_link=[])
        
        for comment in queryset:
            try:
                stats['total_cases_processed'] += 1
                
                if not comment.view_link:
                    continue
                
                for link_index, link_obj in enumerate(comment.view_link):
                    if not isinstance(link_obj, dict):
                        continue
                    
                    href = link_obj.get('href', '')
                    if not href or not href.lower().endswith('.pdf'):
                        continue
                    
                    stats['total_pdfs_found'] += 1
                    
                    # Download PDF
                    document = self.pdf_processor.download_pdf(href, comment.case.case_number)
                    if document and document.is_downloaded:
                        stats['total_documents_created'] += 1
                        
                        # Create CaseDocument relationship
                        case_doc, created = CaseDocument.objects.get_or_create(
                            case=comment.case,
                            document=document,
                            source_table='comments_data',
                            source_row_id=comment.id,
                            source_link_index=link_index,
                            defaults={
                                'document_type': 'comment',
                                'document_title': link_obj.get('title', '') or link_obj.get('text', '')
                            }
                        )
                        
                        if created:
                            stats['total_case_documents_created'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing comment {comment.id}: {str(e)}")
                stats['errors'] += 1
        
        return stats
    
    def _extract_from_judgement_data(self, limit: int = None) -> Dict[str, int]:
        """Extract PDF links from judgement_data table"""
        stats = {
            'total_cases_processed': 0,
            'total_pdfs_found': 0,
            'total_documents_created': 0,
            'total_case_documents_created': 0,
            'errors': 0
        }
        
        queryset = JudgementData.objects.filter(pdf_url__isnull=False).exclude(pdf_url='')
        
        for judgement in queryset:
            try:
                stats['total_cases_processed'] += 1
                
                if not judgement.pdf_url:
                    continue
                
                # Check if it's a PDF URL
                if not judgement.pdf_url.lower().endswith('.pdf'):
                    continue
                
                stats['total_pdfs_found'] += 1
                
                # Download PDF
                document = self.pdf_processor.download_pdf(judgement.pdf_url, judgement.case.case_number)
                if document and document.is_downloaded:
                    stats['total_documents_created'] += 1
                    
                    # Create CaseDocument relationship
                    case_doc, created = CaseDocument.objects.get_or_create(
                        case=judgement.case,
                        document=document,
                        source_table='judgement_data',
                        source_row_id=judgement.id,
                        source_link_index=0,  # Only one PDF per judgement
                        defaults={
                            'document_type': 'judgement',
                            'document_title': judgement.pdf_filename or 'Judgement PDF'
                        }
                    )
                    
                    if created:
                        stats['total_case_documents_created'] += 1
                
            except Exception as e:
                logger.error(f"Error processing judgement {judgement.id}: {str(e)}")
                stats['errors'] += 1
        
        return stats
