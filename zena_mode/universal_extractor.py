# -*- coding: utf-8 -*-
"""
universal_extractor.py - Universal Text Extractor for RAG
Extracts from: PDFs, Images, Screenshots, UI elements
Optimized for production RAG pipelines
"""
import logging
import re
import hashlib
import time
import threading
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass, field
from .chunker import TextChunker, ChunkerConfig
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
import sys
import os
# Add root to path for utils import if needed, or use relative import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import safe_print

try:
    import fitz  # PyMuPDF
    import pytesseract
    from PIL import Image
    import cv2
    import numpy as np
except ImportError as e:
    raise ImportError(
        f"Missing dependencies: {e}\n"
        "Install: pip install pymupdf pytesseract pillow opencv-python numpy"
    )

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Supported document types."""
    PDF = "pdf"
    IMAGE = "image"
    SCREENSHOT = "screenshot"
    UNKNOWN = "unknown"


@dataclass
class ProcessingStats:
    """Thread-safe statistics tracking."""
    total_pages: int = 0
    text_pages: int = 0
    ocr_pages: int = 0
    image_files: int = 0
    failed_pages: int = 0
    total_chunks: int = 0
    preprocessing_applied: int = 0
    start_time: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def increment(self, category: str, count: int = 1):
        with self._lock:
            current = getattr(self, category, 0)
            setattr(self, category, current + count)
    
    def summary(self) -> str:
        elapsed = time.time() - self.start_time
        return (
            f"Pages: {self.total_pages} | Text: {self.text_pages} | "
            f"OCR: {self.ocr_pages} | Images: {self.image_files} | "
            f"Preprocessed: {self.preprocessing_applied} | "
            f"Failed: {self.failed_pages} | Chunks: {self.total_chunks} | "
            f"Time: {elapsed:.2f}s"
        )


@dataclass
class ExtractedChunk:
    """RAG-ready chunk with unique ID and metadata."""
    text: str
    metadata: Dict[str, any] = field(default_factory=dict)
    chunk_id: Optional[str] = None
    
    def __post_init__(self):
        """Generate deterministic ID if not provided."""
        if not self.chunk_id:
            source = self.metadata.get('source', '')
            page = self.metadata.get('page', 0)
            content_sample = self.text[:50]
            unique_str = f"{source}_{page}_{content_sample}"
            self.chunk_id = hashlib.md5(unique_str.encode()).hexdigest()


class ImagePreprocessor:
    """
    Advanced image preprocessing for better OCR accuracy.
    Handles screenshots, UI elements, low-contrast images.
    """
    
    @staticmethod
    def detect_preprocessing_needs(img: np.ndarray) -> Dict[str, bool]:
        """Analyze image to determine which preprocessing steps are needed."""
        needs = {
            'denoise': False,
            'contrast': False,
            'binarize': False,
            'deskew': False,
            'scale': False
        }
        
        # Convert to grayscale for analysis
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        
        # Check contrast (standard deviation of pixel values)
        contrast = gray.std()
        if contrast < 50:
            needs['contrast'] = True
            needs['binarize'] = True
        
        # Check image size (upscale small images)
        height, width = gray.shape
        if height < 1000 or width < 1000:
            needs['scale'] = True
        
        # Check for noise (variance in small regions)
        if contrast > 70:
            needs['denoise'] = True
        
        return needs
    
    @staticmethod
    def preprocess_for_ocr(
        img: np.ndarray,
        enhance_contrast: bool = True,
        denoise: bool = True,
        binarize: bool = True,
        deskew: bool = False,
        scale_factor: float = 2.0
    ) -> np.ndarray:
        """
        Apply preprocessing pipeline optimized for OCR.
        
        Args:
            img: Input image (numpy array)
            enhance_contrast: Apply CLAHE contrast enhancement
            denoise: Apply denoising filter
            binarize: Apply adaptive thresholding
            deskew: Attempt to correct skewed text
            scale_factor: Upscaling factor for small images
        """
        # Convert to grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        # Scale up if needed (better OCR on larger images)
        height, width = gray.shape
        if height < 1000 or width < 1000:
            gray = cv2.resize(
                gray,
                None,
                fx=scale_factor,
                fy=scale_factor,
                interpolation=cv2.INTER_CUBIC
            )
        
        # Denoise (removes scanner artifacts, compression noise)
        if denoise:
            gray = cv2.fastNlMeansDenoising(gray, h=10)
        
        # Enhance contrast (CLAHE - Contrast Limited Adaptive Histogram Equalization)
        if enhance_contrast:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
        
        # Binarization (converts to pure black/white)
        if binarize:
            # Adaptive thresholding works better for varying lighting
            gray = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                11,
                2
            )
        
        # Deskew (correct rotation)
        if deskew:
            gray = ImagePreprocessor._deskew_image(gray)
        
        return gray
    
    @staticmethod
    def _deskew_image(img: np.ndarray) -> np.ndarray:
        """Detect and correct skew angle."""
        try:
            # Detect edges
            edges = cv2.Canny(img, 50, 150, apertureSize=3)
            
            # Detect lines using Hough transform
            lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
            
            if lines is None:
                return img
            
            # Calculate average angle
            angles = []
            for rho, theta in lines[:, 0]:
                angle = (theta * 180 / np.pi) - 90
                if -45 < angle < 45:
                    angles.append(angle)
            
            if not angles:
                return img
            
            median_angle = np.median(angles)
            
            # Rotate image
            (h, w) = img.shape
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(
                img, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            
            return rotated
            
        except Exception as e:
            logger.debug(f"Deskew failed: {e}")
            return img
    
    @staticmethod
    def preprocess_screenshot(img: np.ndarray) -> np.ndarray:
        """Specialized preprocessing for screenshots and UI elements."""
        # Screenshots usually have good contrast but may have:
        # - Anti-aliased text (smooth edges)
        # - Low resolution
        # - UI elements with varying backgrounds
        
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        # Upscale for better OCR
        gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        
        # Sharpen text
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        gray = cv2.filter2D(gray, -1, kernel)
        
        # Adaptive threshold to handle varying backgrounds
        gray = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 15, 3
        )
        
        return gray


class UniversalExtractor:
    """
    Universal text extractor supporting PDFs, images, screenshots.
    Optimized for RAG pipelines with smart preprocessing.
    """
    
    # Supported image formats
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'}
    
    # Pre-compiled regex
    WHITESPACE_PATTERN = re.compile(r'[ \t]+')
    NEWLINE_PATTERN = re.compile(r'\n{3,}')
    SENTENCE_ENDINGS = re.compile(r'(?<=[.!?])\s+')

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        max_workers: int = 4,
        ocr_timeout: int = 30,
        min_text_density: float = 0.05,
        preprocess_images: bool = True,
        tesseract_config: str = '--oem 3 --psm 6'
    ):
        """
        Args:
            chunk_size: Target characters per chunk
            chunk_overlap: Overlap for context preservation
            max_workers: Thread pool size
            ocr_timeout: Max seconds for OCR per page/image
            min_text_density: Min text area ratio for PDFs
            preprocess_images: Apply image enhancement before OCR
            tesseract_config: Tesseract configuration
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = min(chunk_overlap, chunk_size // 2)
        self.max_workers = max_workers
        self.ocr_timeout = ocr_timeout
        self.min_text_density = min_text_density
        self.preprocess_images = preprocess_images
        self.tesseract_config = tesseract_config
        self.stats = ProcessingStats()
        self.preprocessor = ImagePreprocessor()
        
        # Initialize Chunker
        chunk_conf = ChunkerConfig()
        chunk_conf.CHUNK_SIZE = chunk_size
        chunk_conf.CHUNK_OVERLAP = chunk_overlap
        self.chunker = TextChunker(chunk_conf)

    def process(
        self,
        input_data: Union[str, Path, bytes],
        parallel: bool = True,
        document_type: Optional[DocumentType] = None,
        filename: str = "unknown"
    ) -> Tuple[List[ExtractedChunk], ProcessingStats]:
        """
        Universal processing entry point.
        Auto-detects file type and routes to appropriate handler.
        
        Args:
            input_data: Path to document or raw bytes
            parallel: Enable parallel processing for multi-page PDFs
            document_type: Override auto-detection
            filename: Original filename (important for extension detection if input is bytes)
            
        Returns:
            (chunks, stats) tuple
        """
        self.stats = ProcessingStats()
        
        # Handle Path vs Bytes
        if isinstance(input_data, (str, Path)):
            input_path = Path(input_data)
            if not input_path.exists():
                logger.error(f"File not found: {input_path}")
                return [], self.stats
            filename = input_path.name
            if document_type is None:
                document_type = self._detect_document_type(input_path)
            mode = "path"
        else:
            # Bytes mode
            if document_type is None:
                document_type = self._detect_type_from_filename(filename)
            mode = "bytes"
        
        logger.info(f"Processing {document_type.value} ({mode}): {filename}")
        
        # Route to appropriate handler
        if document_type == DocumentType.PDF:
            return self._process_pdf(input_data, parallel, filename=filename)
        elif document_type in [DocumentType.IMAGE, DocumentType.SCREENSHOT]:
            return self._process_image(input_data, document_type, filename=filename)
        else:
            logger.error(f"Unsupported document type for {filename}")
            return [], self.stats

    def _detect_type_from_filename(self, filename: str) -> DocumentType:
        """Detect type from filename extension."""
        ext = Path(filename).suffix.lower()
        if ext == '.pdf':
            return DocumentType.PDF
        elif ext in self.IMAGE_EXTENSIONS:
            return DocumentType.IMAGE
        return DocumentType.UNKNOWN

    def _detect_document_type(self, file_path: Path) -> DocumentType:
        """Detect document type from file extension and content."""
        suffix = file_path.suffix.lower()
        
        if suffix == '.pdf':
            return DocumentType.PDF
        elif suffix in self.IMAGE_EXTENSIONS:
            # Could add heuristics to detect screenshots vs photos
            # (e.g., check for UI patterns, text density, etc.)
            return DocumentType.IMAGE
        else:
            return DocumentType.UNKNOWN

    def _process_pdf(
        self,
        input_data: Union[Path, bytes],
        parallel: bool,
        filename: str
    ) -> Tuple[List[ExtractedChunk], ProcessingStats]:
        """Process PDF with hybrid text extraction + OCR."""
        try:
            # Handle Path vs Bytes
            open_args = {"filename": str(input_data)} if isinstance(input_data, (str, Path)) else {"stream": input_data, "filetype": "pdf"}
            
            with fitz.open(**open_args) as doc:
                if doc.is_encrypted and not doc.authenticate(""):
                    logger.error(f"Cannot decrypt: {filename}")
                    return [], self.stats
                
                self.stats.total_pages = len(doc)
            
            # Extract text from all pages
            if parallel and self.stats.total_pages > 1:
                page_results = self._extract_pdf_parallel(input_data)
            else:
                page_results = self._extract_pdf_sequential(input_data)
            
            # Sort by page number
            page_results.sort(key=lambda x: x['page_num'])
            
            # Chunk all text
            return self._finalize_chunks(page_results, filename)
            
        except Exception as e:
            logger.error(f"PDF processing failed: {e}", exc_info=True)
            return [], self.stats

    def _process_image(
        self,
        input_data: Union[Path, bytes],
        doc_type: DocumentType,
        filename: str
    ) -> Tuple[List[ExtractedChunk], ProcessingStats]:
        """Process standalone image data."""
        try:
            # Load image from Path or Bytes
            if isinstance(input_data, (str, Path)):
                img = cv2.imread(str(input_data))
                if img is None:
                    pil_img = Image.open(input_data)
                    img = np.array(pil_img)
            else:
                # Processed bytes
                nparr = np.frombuffer(input_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is None:
                    # Fallback to PIL for bytes
                    from io import BytesIO
                    pil_img = Image.open(BytesIO(input_data))
                    img = np.array(pil_img)
            
            if img is None:
                logger.error(f"Could not decode image: {filename}")
                return [], self.stats

            if len(img.shape) == 2:  # Grayscale fallback
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            
            # Preprocess based on type
            if self.preprocess_images:
                if doc_type == DocumentType.SCREENSHOT:
                    processed = self.preprocessor.preprocess_screenshot(img)
                else:
                    # Auto-detect preprocessing needs
                    needs = self.preprocessor.detect_preprocessing_needs(img)
                    processed = self.preprocessor.preprocess_for_ocr(
                        img,
                        enhance_contrast=needs['contrast'],
                        denoise=needs['denoise'],
                        binarize=needs['binarize'],
                        deskew=needs['deskew']
                    )
                    if any(needs.values()):
                        self.stats.increment('preprocessing_applied')
            else:
                processed = img
            
            # Extract text
            text = self._ocr_image(processed)
            self.stats.increment('image_files')
            self.stats.increment('ocr_pages')
            
            if not text:
                logger.warning(f"No text extracted from {filename}")
                return [], self.stats
            
            # Clean and chunk
            cleaned = self._clean_text(text)
            chunks = self._create_semantic_chunks(
                cleaned,
                filename,
                page_num=1
            )
            
            self.stats.total_chunks = len(chunks)
            logger.info(f"Completed: {self.stats.summary()}")
            
            return chunks, self.stats
            
        except Exception as e:
            logger.error(f"Image processing failed: {e}", exc_info=True)
            return [], self.stats

    def _extract_pdf_sequential(self, input_data: Union[Path, bytes]) -> List[Dict]:
        """Sequential PDF page processing."""
        results = []
        open_args = {"filename": str(input_data)} if isinstance(input_data, (str, Path)) else {"stream": input_data, "filetype": "pdf"}
        with fitz.open(**open_args) as doc:
            for page_num in range(len(doc)):
                result = self._process_pdf_page(doc[page_num], page_num)
                if result:
                    results.append(result)
        return results

    def _extract_pdf_parallel(self, input_data: Union[Path, bytes]) -> List[Dict]:
        """Parallel PDF page processing."""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._process_pdf_page_worker, input_data, i): i
                for i in range(self.stats.total_pages)
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Page processing error: {e}")
                    self.stats.increment('failed_pages')
        
        return results

    def _process_pdf_page_worker(self, input_data: Union[Path, bytes], page_num: int) -> Optional[Dict]:
        """Worker: process single PDF page with own handle."""
        try:
            open_args = {"filename": str(input_data)} if isinstance(input_data, (str, Path)) else {"stream": input_data, "filetype": "pdf"}
            with fitz.open(**open_args) as doc:
                page = doc.load_page(page_num)
                return self._process_pdf_page(page, page_num)
        except Exception as e:
            logger.warning(f"Worker error on page {page_num}: {e}")
            return None

    def _process_pdf_page(self, page, page_num: int) -> Optional[Dict]:
        """Core PDF page processing."""
        try:
            text = page.get_text("text")
            needs_ocr = self._is_low_density_geometric(page, text)
            
            if needs_ocr:
                # Render page to image and preprocess
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                    pix.height, pix.width, 3
                )
                
                if self.preprocess_images:
                    needs = self.preprocessor.detect_preprocessing_needs(img_array)
                    img_array = self.preprocessor.preprocess_for_ocr(
                        img_array,
                        enhance_contrast=needs['contrast'],
                        denoise=needs['denoise'],
                        binarize=needs['binarize']
                    )
                    if any(needs.values()):
                        self.stats.increment('preprocessing_applied')
                
                processed_text = self._ocr_image(img_array)
                self.stats.increment('ocr_pages')
            else:
                processed_text = text
                self.stats.increment('text_pages')
            
            cleaned = self._clean_text(processed_text)
            
            return {
                'page_num': page_num + 1,
                'text': cleaned,
                'is_ocr': needs_ocr
            }
            
        except Exception as e:
            logger.warning(f"Page {page_num} error: {e}")
            self.stats.increment('failed_pages')
            return None

    def _is_low_density_geometric(self, page, text: str) -> bool:
        """Geometric density check for PDFs."""
        if not text.strip():
            return True
        
        try:
            text_blocks = page.get_text("blocks")
            if not text_blocks:
                return True
            
            text_area = sum([
                (block[2] - block[0]) * (block[3] - block[1])
                for block in text_blocks
            ])
            
            page_area = page.rect.width * page.rect.height
            if page_area == 0:
                return True
            
            density = text_area / page_area
            return density < self.min_text_density
            
        except Exception:
            return len(text.strip()) < 50

    def _ocr_image(self, img: Union[np.ndarray, Image.Image]) -> str:
        """OCR with Tesseract, handles both numpy arrays and PIL images."""
        try:
            # Convert numpy array to PIL if needed
            if isinstance(img, np.ndarray):
                if len(img.shape) == 2:  # Grayscale
                    pil_img = Image.fromarray(img, mode='L')
                else:  # Color
                    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            else:
                pil_img = img
            
            text = pytesseract.image_to_string(
                pil_img,
                config=self.tesseract_config,
                timeout=self.ocr_timeout
            )
            return text
            
        except RuntimeError:
            logger.warning("OCR timeout")
            return ""
        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            return ""

    def _clean_text(self, text: str) -> str:
        """Normalize whitespace."""
        text = self.NEWLINE_PATTERN.sub('\n\n', text)
        text = self.WHITESPACE_PATTERN.sub(' ', text)
        text = '\n'.join(line.strip() for line in text.split('\n'))
        return text.strip()

    def _create_semantic_chunks(
        self,
        text: str,
        source: str,
        page_num: int
    ) -> List[ExtractedChunk]:
        """Sentence-level semantic chunking using unified chunker."""
        meta = {"source": source, "page": page_num}
        doc_chunks = self.chunker.chunk_document(text, metadata=meta, strategy="semantic")
        
        return [
            ExtractedChunk(
                text=c.text,
                metadata={
                    "source": source,
                    "page": page_num,
                    "chunk_index": c.chunk_index,
                    "char_count": len(c.text)
                }
            ) for c in doc_chunks
        ]


# Usage Examples
if __name__ == "__main__":
    extractor = UniversalExtractor(
        chunk_size=1000,
        chunk_overlap=200,
        max_workers=4,
        preprocess_images=True
    )
    
    # Example 1: Process PDF
    safe_print("\n" + "="*70)
    safe_print("PROCESSING PDF")
    safe_print("="*70)
    chunks, stats = extractor.process("document.pdf", parallel=True)
    safe_print(stats.summary())
    
    # Example 2: Process Screenshot
    safe_print("\n" + "="*70)
    safe_print("PROCESSING SCREENSHOT")
    safe_print("="*70)
    chunks, stats = extractor.process(
        "screenshot.png",
        document_type=DocumentType.SCREENSHOT
    )
    safe_print(stats.summary())
    
    # Example 3: Process scanned image
    safe_print("\n" + "="*70)
    safe_print("PROCESSING SCANNED IMAGE")
    safe_print("="*70)
    chunks, stats = extractor.process("scan.jpg")
    safe_print(stats.summary())
    
    # Preview chunks
    if chunks:
        safe_print(f"\n{'='*70}")
        safe_print("SAMPLE CHUNKS")
        safe_print("="*70)
        for i, chunk in enumerate(chunks[:2]):
            safe_print(f"\nChunk {i+1}:")
            safe_print(f"  ID: {chunk.chunk_id}")
            safe_print(f"  Page: {chunk.metadata['page']}")
            safe_print(f"  Length: {chunk.metadata['char_count']} chars")
            safe_print(f"  Text: {chunk.text[:200]}...")
