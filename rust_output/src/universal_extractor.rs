/// universal_extractor::py - Universal Text Extractor for RAG
/// Extracts from: PDFs, Images, Screenshots, UI elements
/// Optimized for production RAG pipelines

use anyhow::{Result, Context};
use crate::chunker::{TextChunker, ChunkerConfig};
use crate::utils::{safe_print};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::collections::HashSet;
use std::fs::File;
use std::io::{self, Read, Write};
use std::path::PathBuf;

pub static LOGGER: std::sync::LazyLock<String /* logging::getLogger */> = std::sync::LazyLock::new(|| Default::default());

/// Supported document types.
#[derive(Debug, Clone)]
pub struct DocumentType {
}

/// Thread-safe statistics tracking.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessingStats {
    pub total_pages: i64,
    pub text_pages: i64,
    pub ocr_pages: i64,
    pub image_files: i64,
    pub failed_pages: i64,
    pub total_chunks: i64,
    pub preprocessing_applied: i64,
    pub start_time: f64,
    pub _lock: threading::Lock,
}

impl ProcessingStats {
    pub fn increment(&mut self, category: String, count: i64) -> () {
        let _ctx = self._lock;
        {
            let mut current = /* getattr */ 0;
            /* setattr(self, category, (current + count)) */;
        }
    }
    /// Summary.
    pub fn summary(&mut self) -> String {
        // Summary.
        let mut elapsed = (std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs_f64() - self.start_time);
        format!("Pages: {} | Text: {} | OCR: {} | Images: {} | Preprocessed: {} | Failed: {} | Chunks: {} | Time: {:.2}s", self.total_pages, self.text_pages, self.ocr_pages, self.image_files, self.preprocessing_applied, self.failed_pages, self.total_chunks, elapsed)
    }
}

/// RAG-ready chunk with unique ID and metadata.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtractedChunk {
    pub text: String,
    pub metadata: HashMap<String, any>,
    pub chunk_id: Option<String>,
}

impl ExtractedChunk {
    /// Generate deterministic ID if not provided.
    pub fn __post_init__(&mut self) -> () {
        // Generate deterministic ID if not provided.
        if self.chunk_id {
            return;
        }
        let mut source = self.metadata.get(&"source".to_string()).cloned().unwrap_or("".to_string());
        let mut page = self.metadata.get(&"page".to_string()).cloned().unwrap_or(0);
        let mut content_sample = self.text[..50];
        let mut unique_str = format!("{}_{}_{}", source, page, content_sample);
        self.chunk_id = hashlib::sha256(unique_str.as_bytes().to_vec()).hexdigest();
    }
}

/// Advanced image preprocessing for better OCR accuracy.
/// Handles screenshots, UI elements, low-contrast images.
#[derive(Debug, Clone)]
pub struct ImagePreprocessor {
}

impl ImagePreprocessor {
    /// Analyze image to determine which preprocessing steps are needed.
    pub fn detect_preprocessing_needs(img: np::ndarray) -> HashMap<String, bool> {
        // Analyze image to determine which preprocessing steps are needed.
        let mut needs = HashMap::from([("denoise".to_string(), false), ("contrast".to_string(), false), ("binarize".to_string(), false), ("deskew".to_string(), false), ("scale".to_string(), false)]);
        if img.shape.len() == 3 {
            let mut gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY);
        } else {
            let mut gray = img;
        }
        let mut contrast = gray.std();
        if contrast < 50 {
            needs["contrast".to_string()] = true;
            needs["binarize".to_string()] = true;
        }
        let (mut height, mut width) = gray.shape;
        if (height < 1000 || width < 1000) {
            needs["scale".to_string()] = true;
        }
        if contrast > 70 {
            needs["denoise".to_string()] = true;
        }
        needs
    }
    /// Apply preprocessing pipeline optimized for OCR.
    /// 
    /// Args:
    /// img: Input image (numpy array)
    /// enhance_contrast: Apply CLAHE contrast enhancement
    /// denoise: Apply denoising filter
    /// binarize: Apply adaptive thresholding
    /// deskew: Attempt to correct skewed text
    /// scale_factor: Upscaling factor for small images
    pub fn preprocess_for_ocr(img: np::ndarray, enhance_contrast: bool, denoise: bool, binarize: bool, deskew: bool, scale_factor: f64) -> np::ndarray {
        // Apply preprocessing pipeline optimized for OCR.
        // 
        // Args:
        // img: Input image (numpy array)
        // enhance_contrast: Apply CLAHE contrast enhancement
        // denoise: Apply denoising filter
        // binarize: Apply adaptive thresholding
        // deskew: Attempt to correct skewed text
        // scale_factor: Upscaling factor for small images
        if img.shape.len() == 3 {
            let mut gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY);
        } else {
            let mut gray = img.clone();
        }
        let (mut height, mut width) = gray.shape;
        if (height < 1000 || width < 1000) {
            let mut gray = cv2.resize(gray, None, /* fx= */ scale_factor, /* fy= */ scale_factor, /* interpolation= */ cv2.INTER_CUBIC);
        }
        if denoise {
            let mut gray = cv2.fastNlMeansDenoising(gray, /* h= */ 10);
        }
        if enhance_contrast {
            let mut clahe = cv2.createCLAHE(/* clipLimit= */ 2.0_f64, /* tileGridSize= */ (8, 8));
            let mut gray = clahe.apply(gray);
        }
        if binarize {
            let mut gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2);
        }
        if deskew {
            let mut gray = ImagePreprocessor._deskew_image(gray);
        }
        gray
    }
    /// Detect and correct skew angle.
    pub fn _deskew_image(img: np::ndarray) -> Result<np::ndarray> {
        // Detect and correct skew angle.
        // try:
        {
            let mut edges = cv2.Canny(img, 50, 150, /* apertureSize= */ 3);
            let mut lines = cv2.HoughLines(edges, 1, (np.pi / 180), 200);
            if lines.is_none() {
                img
            }
            let mut angles = vec![];
            for (rho, theta) in lines[(.., 0)].iter() {
                let mut angle = (((theta * 180) / np.pi) - 90);
                if (-45 < angle) && (angle < 45) {
                    angles.push(angle);
                }
            }
            if !angles {
                img
            }
            let mut median_angle = np.median(angles);
            let (mut h, mut w) = img.shape;
            let mut center = ((w / 2), (h / 2));
            let mut M = cv2.getRotationMatrix2D(center, median_angle, 1.0_f64);
            let mut rotated = cv2.warpAffine(img, M, (w, h), /* flags= */ cv2.INTER_CUBIC, /* borderMode= */ cv2.BORDER_REPLICATE);
            rotated
        }
        // except Exception as e:
    }
    /// Specialized preprocessing for screenshots and UI elements.
    pub fn preprocess_screenshot(img: np::ndarray) -> np::ndarray {
        // Specialized preprocessing for screenshots and UI elements.
        if img.shape.len() == 3 {
            let mut gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY);
        } else {
            let mut gray = img.clone();
        }
        let mut gray = cv2.resize(gray, None, /* fx= */ 2.0_f64, /* fy= */ 2.0_f64, /* interpolation= */ cv2.INTER_CUBIC);
        let mut kernel = np.array(vec![vec![-1, -1, -1], vec![-1, 9, -1], vec![-1, -1, -1]]);
        let mut gray = cv2.filter2D(gray, -1, kernel);
        let mut gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 3);
        gray
    }
    /// Perform visual analysis of the image to provide context for RAG.
    /// Detects if it's likely a screenshot, scanned document, or photo.
    pub fn analyze_visuals(img: np::ndarray) -> Result<HashMap<String, Box<dyn std::any::Any>>> {
        // Perform visual analysis of the image to provide context for RAG.
        // Detects if it's likely a screenshot, scanned document, or photo.
        let mut stats = HashMap::from([("is_screenshot_likely".to_string(), false), ("avg_brightness".to_string(), 0), ("contrast_level".to_string(), "normal".to_string()), ("has_color".to_string(), false), ("dimensions".to_string(), vec![0, 0])]);
        // try:
        {
            if img.is_none() {
                stats
            }
            if !/* /* isinstance(img, np.ndarray) */ */ true {
                let mut img = np.array(img);
            }
            let (mut h, mut w) = img.shape[..2];
            stats["dimensions".to_string()] = vec![w, h];
            if (img.shape.len() == 3 && img.shape[2] == 3) {
                let (mut b, mut g, mut r) = cv2.split(img).map(|s| s.to_string()).collect::<Vec<String>>();
                if !(np.array_equal(b, g) && np.array_equal(g, r)) {
                    stats["has_color".to_string()] = true;
                }
            }
            let mut gray = if img.shape.len() == 3 { cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) } else { img };
            stats["avg_brightness".to_string()] = np.mean(gray).to_string().parse::<f64>().unwrap_or(0.0);
            let mut std = np.std(gray);
            if std < 30 {
                stats["contrast_level".to_string()] = "low".to_string();
            } else if std > 80 {
                stats["contrast_level".to_string()] = "high".to_string();
            }
            let mut edges = cv2.Canny(gray, 100, 200);
            let mut edge_density = (np.sum(edges > 0) / (h * w));
            let mut small = cv2.resize(img, (100, 100));
            let mut unique_colors = np.unique(small.reshape(-1, small.shape[-1]), /* axis= */ 0).len();
            if (unique_colors < 50 && edge_density > 0.01_f64) {
                stats["is_screenshot_likely".to_string()] = true;
            }
        }
        // except Exception as e:
        Ok(stats)
    }
}

/// Base methods for UniversalExtractor.
#[derive(Debug, Clone)]
pub struct _UniversalExtractorBase {
    pub chunk_size: String,
    pub chunk_overlap: min,
    pub max_workers: String,
    pub ocr_timeout: String,
    pub min_text_density: String,
    pub preprocess_images: String,
    pub tesseract_config: String,
    pub stats: ProcessingStats,
    pub preprocessor: ImagePreprocessor,
    pub vision_engine: String,
    pub IMAGE_EXTENSIONS: HashSet<serde_json::Value>,
    pub VIDEO_EXTENSIONS: HashSet<serde_json::Value>,
    pub chunker: TextChunker,
}

impl _UniversalExtractorBase {
    /// Args:
    /// chunk_size: Target characters per chunk
    /// chunk_overlap: Overlap for context preservation
    /// max_workers: Thread pool size
    /// ocr_timeout: Max seconds for OCR per page/image
    /// min_text_density: Min text area ratio for PDFs
    /// preprocess_images: Apply image enhancement before OCR
    /// tesseract_config: Tesseract configuration
    /// vision_enabled: Enable YOLOv26 vision analysis
    pub fn new(chunk_size: i64, chunk_overlap: i64, max_workers: i64, ocr_timeout: i64, min_text_density: f64, preprocess_images: bool, tesseract_config: String, vision_enabled: bool) -> Self {
        Self {
            chunk_size,
            chunk_overlap: chunk_overlap.min((chunk_size / 2)),
            max_workers,
            ocr_timeout,
            min_text_density,
            preprocess_images,
            tesseract_config,
            stats: ProcessingStats(),
            preprocessor: ImagePreprocessor(),
            vision_engine: if vision_enabled { get_vision_engine() } else { None },
            IMAGE_EXTENSIONS: HashSet::from([".png".to_string(), ".jpg".to_string(), ".jpeg".to_string(), ".bmp".to_string(), ".tiff".to_string(), ".tif".to_string(), ".webp".to_string()]),
            VIDEO_EXTENSIONS: HashSet::from([".mp4".to_string(), ".avi".to_string(), ".mov".to_string(), ".mkv".to_string(), ".wmv".to_string()]),
            chunker: TextChunker(chunk_conf),
        }
    }
    /// Universal processing entry point.
    /// Auto-detects file type and routes to appropriate handler.
    /// 
    /// Args:
    /// input_data: Path to document or raw bytes
    /// parallel: Enable parallel processing for multi-page PDFs
    /// document_type: Override auto-detection
    /// filename: Original filename (important for extension detection if input is bytes)
    /// 
    /// Returns:
    /// (chunks, stats) tuple
    pub fn process(&mut self, input_data: Union<serde_json::Value>, parallel: bool, document_type: Option<DocumentType>, filename: String) -> (Vec<ExtractedChunk>, ProcessingStats) {
        // Universal processing entry point.
        // Auto-detects file type and routes to appropriate handler.
        // 
        // Args:
        // input_data: Path to document or raw bytes
        // parallel: Enable parallel processing for multi-page PDFs
        // document_type: Override auto-detection
        // filename: Original filename (important for extension detection if input is bytes)
        // 
        // Returns:
        // (chunks, stats) tuple
        self.stats = ProcessingStats();
        if /* /* isinstance(input_data, (str, Path) */) */ true {
            let mut input_path = PathBuf::from(input_data);
            if !input_path.exists() {
                logger.error(format!("File not found: {}", input_path));
                (vec![], self.stats)
            }
            let mut filename = input_path.file_name().unwrap_or_default().to_str().unwrap_or("");
            if document_type.is_none() {
                let mut document_type = self._detect_document_type(input_path);
            }
            let mut mode = "path".to_string();
        } else {
            if document_type.is_none() {
                let mut document_type = self._detect_type_from_filename(filename);
            }
            let mut mode = "bytes".to_string();
        }
        logger.info(format!("Processing {} ({}): {}", document_type.value, mode, filename));
        if document_type == DocumentType.PDF {
            self._process_pdf(input_data, parallel, /* filename= */ filename)
        } else if vec![DocumentType.IMAGE, DocumentType.SCREENSHOT].contains(&document_type) {
            self._process_image(input_data, document_type, /* filename= */ filename)
        } else if document_type == DocumentType.VIDEO {
            self._process_video(input_data, /* filename= */ filename)
        } else {
            logger.error(format!("Unsupported document type for {}", filename));
            (vec![], self.stats)
        }
    }
    /// Detect type from filename extension.
    pub fn _detect_type_from_filename(&mut self, filename: String) -> DocumentType {
        // Detect type from filename extension.
        let mut ext = PathBuf::from(filename).extension().unwrap_or_default().to_str().unwrap_or("").to_lowercase();
        if ext == ".pdf".to_string() {
            DocumentType.PDF
        } else if self.IMAGE_EXTENSIONS.contains(&ext) {
            DocumentType.IMAGE
        } else if self.VIDEO_EXTENSIONS.contains(&ext) {
            DocumentType.VIDEO
        }
        DocumentType.UNKNOWN
    }
    /// Detect document type from file extension and content.
    pub fn _detect_document_type(&mut self, file_path: PathBuf) -> DocumentType {
        // Detect document type from file extension and content.
        let mut suffix = file_path.extension().unwrap_or_default().to_str().unwrap_or("").to_lowercase();
        if suffix == ".pdf".to_string() {
            DocumentType.PDF
        } else if self.IMAGE_EXTENSIONS.contains(&suffix) {
            DocumentType.IMAGE
        } else if self.VIDEO_EXTENSIONS.contains(&suffix) {
            DocumentType.VIDEO
        } else {
            DocumentType.UNKNOWN
        }
    }
    /// Process PDF with hybrid text extraction + OCR.
    pub fn _process_pdf(&mut self, input_data: Union<serde_json::Value>, parallel: bool, filename: String) -> Result<(Vec<ExtractedChunk>, ProcessingStats)> {
        // Process PDF with hybrid text extraction + OCR.
        // try:
        {
            let mut open_args = if /* /* isinstance(input_data, (str, Path) */) */ true { HashMap::from([("filename".to_string(), input_data.to_string())]) } else { HashMap::from([("stream".to_string(), input_data), ("filetype".to_string(), "pdf".to_string())]) };
            let mut doc = fitz.open(/* ** */ open_args);
            {
                if (doc.is_encrypted && !doc.authenticate("".to_string())) {
                    logger.error(format!("Cannot decrypt: {}", filename));
                    (vec![], self.stats)
                }
                self.stats.total_pages = doc.len();
            }
            if (parallel && self.stats.total_pages > 1) {
                let mut page_results = self._extract_pdf_parallel(input_data);
            } else {
                let mut page_results = self._extract_pdf_sequential(input_data);
            }
            page_results.sort(/* key= */ |x| x["page_num".to_string()]);
            self._finalize_chunks(page_results, filename)
        }
        // except Exception as e:
    }
    /// Process standalone image data.
    pub fn _process_image(&mut self, input_data: Union<serde_json::Value>, doc_type: DocumentType, filename: String) -> Result<(Vec<ExtractedChunk>, ProcessingStats)> {
        // Process standalone image data.
        // try:
        {
            if /* /* isinstance(input_data, (str, Path) */) */ true {
                let mut img = cv2.imread(input_data.to_string());
                if img.is_none() {
                    let mut pil_img = Image.open(input_data);
                    let mut img = np.array(pil_img);
                }
            } else {
                let mut nparr = np.frombuffer(input_data, np.uint8);
                let mut img = cv2.imdecode(nparr, cv2.IMREAD_COLOR);
                if img.is_none() {
                    // TODO: from io import BytesIO
                    let mut pil_img = Image.open(BytesIO(input_data));
                    let mut img = np.array(pil_img);
                }
            }
            if img.is_none() {
                logger.error(format!("Could not decode image: {}", filename));
                (vec![], self.stats)
            }
            if img.shape.len() == 2 {
                let mut img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR);
            }
            if self.preprocess_images {
                if doc_type == DocumentType.SCREENSHOT {
                    let mut processed = self.preprocessor.preprocess_screenshot(img);
                } else {
                    let mut needs = self.preprocessor.detect_preprocessing_needs(img);
                    let mut processed = self.preprocessor.preprocess_for_ocr(img, /* enhance_contrast= */ needs["contrast".to_string()], /* denoise= */ needs["denoise".to_string()], /* binarize= */ needs["binarize".to_string()], /* deskew= */ needs["deskew".to_string()]);
                    if needs.values().iter().any(|v| *v) {
                        self.stats.increment("preprocessing_applied".to_string());
                    }
                }
            } else {
                let mut processed = img;
            }
            let mut text = self._ocr_image(processed);
            let mut visual_stats = self.preprocessor.analyze_visuals(img);
            let mut vision_context = "".to_string();
            if self.vision_engine {
                let mut detections = self.vision_engine::detect_objects(img);
                if detections {
                    let mut vision_context = self.vision_engine::get_vision_summary(detections);
                    visual_stats["detections".to_string()] = detections;
                    logger.info(format!("[Vision] YOLO detected: {}", vision_context));
                }
            }
            self.stats.increment("image_files".to_string());
            self.stats.increment("ocr_pages".to_string());
            if (!text && !vision_context) {
                logger.warning(format!("No text or objects extracted from {}", filename));
                (vec![], self.stats)
            }
            let mut full_text = text;
            if vision_context {
                let mut full_text = (format!("[{}]\n\n", vision_context) + full_text);
            }
            let mut cleaned = self._clean_text(full_text);
            let mut chunks = self._create_semantic_chunks(cleaned, filename, /* page_num= */ 1, /* visual_meta= */ visual_stats);
            self.stats.total_chunks = chunks.len();
            logger.info(format!("Completed: {}", self.stats.summary()));
            (chunks, self.stats)
        }
        // except Exception as e:
    }
    /// Process video files using YOLOv26 keyframe analysis.
    pub fn _process_video(&mut self, input_data: Union<serde_json::Value>, filename: String) -> Result<(Vec<ExtractedChunk>, ProcessingStats)> {
        // Process video files using YOLOv26 keyframe analysis.
        // try:
        {
            let mut temp_path = None;
            if /* /* isinstance(input_data, bytes) */ */ true {
                // TODO: import tempfile
                let mut tf = tempfile::NamedTuple(/* suffix= */ PathBuf::from(filename).extension().unwrap_or_default().to_str().unwrap_or(""), /* delete= */ false);
                {
                    tf.write(input_data);
                    let mut temp_path = tf.name;
                }
                let mut path_to_process = temp_path;
            } else {
                let mut path_to_process = input_data.to_string();
            }
            if !self.vision_engine {
                (vec![], self.stats)
            }
            let mut video_data = self.vision_engine::analyze_video(path_to_process);
            if temp_path {
                // try:
                {
                    os::unlink(temp_path);
                }
                // except Exception as _e:
            }
            if video_data.contains(&"error".to_string()) {
                logger.error(format!("Video analysis failed: {}", video_data["error".to_string()]));
                (vec![], self.stats)
            }
            let mut narrative = format!("Video Analysis for {}:\n", filename);
            narrative += format!("Summary: {}\n\n", video_data["summary".to_string()]);
            narrative += "Chronological Timeline:\n".to_string();
            for frame in video_data["timeline".to_string()].iter() {
                narrative += format!("[{}s]: {}\n", frame["timestamp".to_string()], frame["summary".to_string()]);
            }
            let mut chunks = self._create_semantic_chunks(narrative, filename, /* page_num= */ 1, /* visual_meta= */ HashMap::from([("video_stats".to_string(), video_data)]));
            self.stats.total_chunks = chunks.len();
            (chunks, self.stats)
        }
        // except Exception as e:
    }
}

/// Universal text extractor supporting PDFs, images, screenshots.
/// Optimized for RAG pipelines with smart preprocessing.
#[derive(Debug, Clone)]
pub struct UniversalExtractor {
}

impl UniversalExtractor {
    /// Sequential PDF page processing.
    pub fn _extract_pdf_sequential(&mut self, input_data: Union<serde_json::Value>) -> Result<Vec<HashMap>> {
        // Sequential PDF page processing.
        let mut results = vec![];
        let mut open_args = if /* /* isinstance(input_data, (str, Path) */) */ true { HashMap::from([("filename".to_string(), input_data.to_string())]) } else { HashMap::from([("stream".to_string(), input_data), ("filetype".to_string(), "pdf".to_string())]) };
        let mut doc = fitz.open(/* ** */ open_args);
        {
            for page_num in 0..doc.len().iter() {
                let mut result = self._process_pdf_page(doc[&page_num], page_num, doc);
                if result {
                    results.push(result);
                }
            }
        }
        Ok(results)
    }
    /// Parallel PDF page processing.
    pub fn _extract_pdf_parallel(&mut self, input_data: Union<serde_json::Value>) -> Result<Vec<HashMap>> {
        // Parallel PDF page processing.
        let mut results = vec![];
        let mut executor = ThreadPoolExecutor(/* max_workers= */ self.max_workers);
        {
            let mut futures = 0..self.stats.total_pages.iter().map(|i| (executor.submit(self._process_pdf_page_worker, input_data, i), i)).collect::<HashMap<_, _>>();
            for future in as_completed(futures).iter() {
                // try:
                {
                    let mut result = future.result();
                    if result {
                        results.push(result);
                    }
                }
                // except Exception as e:
            }
        }
        Ok(results)
    }
    /// Worker: process single PDF page with own handle.
    pub fn _process_pdf_page_worker(&mut self, input_data: Union<serde_json::Value>, page_num: i64) -> Result<Option<HashMap>> {
        // Worker: process single PDF page with own handle.
        // try:
        {
            let mut open_args = if /* /* isinstance(input_data, (str, Path) */) */ true { HashMap::from([("filename".to_string(), input_data.to_string())]) } else { HashMap::from([("stream".to_string(), input_data), ("filetype".to_string(), "pdf".to_string())]) };
            let mut doc = fitz.open(/* ** */ open_args);
            {
                let mut page = doc.load_page(page_num);
                self._process_pdf_page(page, page_num, doc)
            }
        }
        // except Exception as e:
    }
    /// Core PDF page processing.
    pub fn _process_pdf_page(&mut self, page: String, page_num: i64, doc: String) -> Result<Option<HashMap>> {
        // Core PDF page processing.
        let mut table_markdown = "".to_string();
        // try:
        {
            if /* hasattr(page, "find_tables".to_string()) */ true {
                let mut tables = page.find_tables();
                if tables {
                    let mut table_markdown = "\n\n### Extracted Tables:\n".to_string();
                    for (i, table) in tables.iter().enumerate().iter() {
                        table_markdown += format!("\n**Table {}**\n", (i + 1));
                        if /* hasattr(table, "to_markdown".to_string()) */ true {
                            table_markdown += table.to_markdown();
                        } else {
                            if !table.header {
                                continue;
                            }
                            let mut headers = table.header.names.iter().map(|h| h.to_string().replace(&*"\n".to_string(), &*" ".to_string())).collect::<Vec<_>>();
                            table_markdown += (("| ".to_string() + headers.join(&" | ".to_string())) + " |\n".to_string());
                            table_markdown += (("| ".to_string() + (vec!["---".to_string()] * headers.len()).join(&" | ".to_string())) + " |\n".to_string());
                            for row in table.extract().iter() {
                                if row == table.header.names {
                                    continue;
                                }
                                let mut clean_row = row.iter().map(|cell| if cell { cell.to_string().replace(&*"\n".to_string(), &*" ".to_string()) } else { "".to_string() }).collect::<Vec<_>>();
                                table_markdown += (("| ".to_string() + clean_row.join(&" | ".to_string())) + " |\n".to_string());
                            }
                        }
                    }
                    logger.debug(format!("Found {} tables on page {}", tables.len(), page_num));
                }
            }
        }
        // except Exception as e:
        // try:
        {
            let mut text = page.get_text("text".to_string());
            let mut needs_ocr = self._is_low_density_geometric(page, text);
            if needs_ocr {
                let mut pix = page.get_pixmap(/* matrix= */ fitz.Matrix(2, 2), /* alpha= */ false);
                let mut img_array = np.frombuffer(pix.samples, /* dtype= */ np.uint8).reshape(pix.height, pix.width, 3);
                if self.preprocess_images {
                    let mut needs = self.preprocessor.detect_preprocessing_needs(img_array);
                    let mut img_array = self.preprocessor.preprocess_for_ocr(img_array, /* enhance_contrast= */ needs["contrast".to_string()], /* denoise= */ needs["denoise".to_string()], /* binarize= */ needs["binarize".to_string()]);
                    if needs.values().iter().any(|v| *v) {
                        self.stats.increment("preprocessing_applied".to_string());
                    }
                }
                let mut processed_text = self._ocr_image(img_array);
                self.stats.increment("ocr_pages".to_string());
            } else {
                let mut processed_text = text;
                self.stats.increment("text_pages".to_string());
            }
            let mut cleaned = self._clean_text(processed_text);
            if table_markdown {
                cleaned += table_markdown;
            }
            let mut image_markdown = "".to_string();
            // try:
            {
                let mut img_dir = PathBuf::from("_static/rag_images".to_string());
                img_dir.create_dir_all();
                let mut images = page.get_images(/* full= */ true);
                for (img_index, img) in images.iter().enumerate().iter() {
                    let mut xref = img[0];
                    let mut base_image = doc.extract_image(xref);
                    let mut image_bytes = base_image["image".to_string()];
                    let mut ext = base_image["ext".to_string()];
                    let mut img_hash = hashlib::sha256(image_bytes).hexdigest();
                    let mut img_filename = format!("{}.{}", img_hash, ext);
                    let mut local_path = (img_dir / img_filename);
                    if !local_path.exists() {
                        let mut f = File::open(local_path)?;
                        {
                            f.write(image_bytes);
                        }
                    }
                    if image_bytes.len() > 2048 {
                        image_markdown += format!("\n\n![PDF Image {}](/rag_images/{})\n", (img_index + 1), img_filename);
                        self.stats.increment("image_files".to_string());
                    }
                }
            }
            // except Exception as e:
            HashMap::from([("page_num".to_string(), (page_num + 1)), ("text".to_string(), (cleaned + image_markdown)), ("is_ocr".to_string(), needs_ocr)])
        }
        // except Exception as e:
    }
    /// Geometric density check for PDFs.
    pub fn _is_low_density_geometric(&mut self, page: String, text: String) -> Result<bool> {
        // Geometric density check for PDFs.
        if !text.trim().to_string() {
            true
        }
        // try:
        {
            let mut text_blocks = page.get_text("blocks".to_string());
            if !text_blocks {
                true
            }
            let mut text_area = text_blocks.iter().map(|block| ((block[2] - block[0]) * (block[3] - block[1]))).collect::<Vec<_>>().iter().sum::<i64>();
            let mut page_area = (page.rect.width * page.rect.height);
            if page_area == 0 {
                true
            }
            let mut density = (text_area / page_area);
            density < self.min_text_density
        }
        // except Exception as _e:
    }
    /// OCR with Tesseract, handles both numpy arrays and PIL images.
    pub fn _ocr_image(&mut self, img: Union<serde_json::Value>) -> Result<String> {
        // OCR with Tesseract, handles both numpy arrays and PIL images.
        // try:
        {
            if /* /* isinstance(img, np.ndarray) */ */ true {
                if img.shape.len() == 2 {
                    let mut pil_img = Image.fromarray(img, /* mode= */ "L".to_string());
                } else {
                    let mut pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB));
                }
            } else {
                let mut pil_img = img;
            }
            let mut text = pytesseract.image_to_string(pil_img, /* config= */ self.tesseract_config, /* timeout= */ self.ocr_timeout);
            text
        }
        // except RuntimeError as _e:
        // except Exception as e:
    }
    /// Normalize whitespace.
    pub fn _clean_text(&mut self, text: String) -> String {
        // Normalize whitespace.
        let mut text = self.NEWLINE_PATTERN.sub("\n\n".to_string(), text);
        let mut text = self.WHITESPACE_PATTERN.sub(" ".to_string(), text);
        let mut text = text.split("\n".to_string()).map(|s| s.to_string()).collect::<Vec<String>>().iter().map(|line| line.trim().to_string()).collect::<Vec<_>>().join(&"\n".to_string());
        text.trim().to_string()
    }
    /// Sentence-level semantic chunking using unified chunker.
    pub fn _create_semantic_chunks(&mut self, text: String, source: String, page_num: i64, visual_meta: Option<HashMap>) -> Vec<ExtractedChunk> {
        // Sentence-level semantic chunking using unified chunker.
        let mut meta = HashMap::from([("source".to_string(), source), ("page".to_string(), page_num)]);
        if visual_meta {
            meta.extend(HashMap::from([("visual_stats".to_string(), visual_meta)]));
        }
        let mut doc_chunks = self.chunker::chunk_document(text, /* metadata= */ meta, /* strategy= */ "semantic".to_string());
        doc_chunks.iter().map(|c| ExtractedChunk(/* text= */ c.text, /* metadata= */ HashMap::from([("source".to_string(), source), ("page".to_string(), page_num), ("chunk_index".to_string(), c.chunk_index), ("char_count".to_string(), c.text.len()), ("visual_stats".to_string(), visual_meta)]))).collect::<Vec<_>>()
    }
}
