"""
OCR (Optical Character Recognition) service for extracting business data
from photos of paper registers, handwritten records, and printed documents.

This is designed for garment business owners who keep their records on paper
and want to digitize them by taking photos.

Supports:
- Handwritten text (English, Urdu, mixed)
- Printed tables
- Multi-column layouts
- Low-quality photos (auto-enhancement)
- Different register formats (sales, purchases, inventory)
"""
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from PIL import Image, ImageEnhance, ImageFilter

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Result of OCR extraction from an image."""
    raw_text: str
    confidence: float
    tables: list[pd.DataFrame]
    detected_language: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class ExtractedRecord:
    """A single business record extracted from OCR."""
    record_type: str  # "sale", "purchase", "expense", "inventory", "unknown"
    date: str | None
    fields: dict[str, Any]
    confidence: float
    raw_line: str


def _open_and_prepare_image(image_path: str) -> Image.Image:
    """Open an image and convert to RGB, resize if needed."""
    logger.info(f"[OCR] Opening image: {image_path}")
    img = Image.open(image_path)
    logger.info(f"[OCR] Original image: mode={img.mode}, size={img.size}, format={img.format}")

    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')
        logger.info("[OCR] Converted to RGB")

    # Resize if too small (helps OCR)
    width, height = img.size
    if width < 1000 or height < 1000:
        scale = max(1000 / width, 1000 / height)
        new_size = (int(width * scale), int(height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        logger.info(f"[OCR] Resized to: {new_size}")

    return img


def enhance_image_gentle(image_path: str) -> Image.Image:
    """
    Gentle enhancement: minimal preprocessing for clear images.
    Only applies light contrast boost and sharpening.
    No binarization - keeps grayscale for better OCR on clean images.
    """
    logger.info("[OCR] Using gentle enhancement (no binarization)")
    img = _open_and_prepare_image(image_path)

    # Convert to grayscale
    img = img.convert('L')
    logger.info("[OCR] Converted to grayscale")

    # Light contrast enhancement (1.2x instead of 1.5x)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.2)
    logger.info("[OCR] Applied gentle contrast enhancement (1.2x)")

    # Light sharpening
    img = img.filter(ImageFilter.SHARPEN)
    logger.info("[OCR] Applied sharpening")

    # NO binarization - keep grayscale for clear images
    return img.convert('RGB')


def enhance_image_moderate(image_path: str) -> Image.Image:
    """
    Moderate enhancement: for slightly blurry or low-contrast images.
    Applies moderate contrast boost, sharpening, and adaptive thresholding.
    """
    logger.info("[OCR] Using moderate enhancement")
    img = _open_and_prepare_image(image_path)

    # Convert to grayscale
    img = img.convert('L')
    logger.info("[OCR] Converted to grayscale")

    # Moderate contrast enhancement (1.4x)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.4)
    logger.info("[OCR] Applied moderate contrast enhancement (1.4x)")

    # Sharpen
    img = img.filter(ImageFilter.SHARPEN)
    logger.info("[OCR] Applied sharpening")

    # Use Otsu's method for adaptive thresholding instead of fixed threshold
    import numpy as np
    arr = np.array(img)

    # Calculate Otsu's threshold
    hist, _ = np.histogram(arr.flatten(), 256, [0, 256])
    total = arr.size
    sum_total = np.dot(np.arange(256), hist)
    sum_bg = 0
    weight_bg = 0
    max_variance = 0
    threshold = 128  # default

    for t in range(256):
        weight_bg += hist[t]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += t * hist[t]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_total - sum_bg) / weight_fg
        variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if variance > max_variance:
            max_variance = variance
            threshold = t

    logger.info(f"[OCR] Otsu's threshold calculated: {threshold}")

    # Apply adaptive threshold
    img = img.point(lambda x: 255 if x > threshold else 0, '1')
    logger.info("[OCR] Applied adaptive binarization")

    return img.convert('RGB')


def enhance_image_aggressive(image_path: str) -> Image.Image:
    """
    Aggressive enhancement: for poor quality, blurry, or low-light images.
    Applies strong contrast boost, sharpening, and fixed threshold binarization.
    """
    logger.info("[OCR] Using aggressive enhancement")
    img = _open_and_prepare_image(image_path)

    # Convert to grayscale
    img = img.convert('L')
    logger.info("[OCR] Converted to grayscale")

    # Strong contrast enhancement (1.8x)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.8)
    logger.info("[OCR] Applied aggressive contrast enhancement (1.8x)")

    # Strong sharpening
    img = img.filter(ImageFilter.SHARPEN)
    img = img.filter(ImageFilter.SHARPEN)  # Double sharpen
    logger.info("[OCR] Applied double sharpening")

    # Fixed threshold binarization (lower threshold to capture more text)
    threshold = 128
    img = img.point(lambda x: 255 if x > threshold else 0, '1')
    logger.info(f"[OCR] Applied aggressive binarization threshold={threshold}")

    return img.convert('RGB')


def _run_ocr_on_image(img: Image.Image, language: str, psm_mode: int = 6) -> str:
    """
    Run OCR on a prepared image with specific settings.
    Returns extracted text.
    """
    config = f'--psm {psm_mode}'
    logger.info(f"[OCR] Running pytesseract with lang={language}, config={config}")
    text = pytesseract.image_to_string(
        img,
        lang=language,
        config=config
    )
    return text


def _extract_text_with_fallback(img: Image.Image, language: str) -> str:
    """
    Try to extract text with the given language, falling back to alternatives.
    Tries different PSM modes if initial extraction fails.
    """
    psm_modes = [6, 4, 3, 11]  # Different page segmentation modes

    for psm in psm_modes:
        try:
            text = _run_ocr_on_image(img, language, psm_mode=psm)
            if text and text.strip():
                logger.info(f"[OCR] Success with lang={language}, psm={psm}, text_len={len(text)}")
                return text
        except Exception as e:
            logger.warning(f"[OCR] Failed with lang={language}, psm={psm}: {e}")
            continue

    return ""


def extract_text_from_image(image_path: str, language: str = 'eng+urd') -> str:
    """
    Extract text from an image using OCR with adaptive preprocessing.
    Tries multiple enhancement strategies and picks the best result.

    Supports English ('eng'), Urdu ('urd'), or both.
    """
    logger.info(f"[OCR] Starting text extraction for: {image_path}, language={language}")

    if not TESSERACT_AVAILABLE:
        logger.error("[OCR] Tesseract not available!")
        raise RuntimeError(
            "Tesseract OCR is not installed. Please install it:\n"
            "  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki\n"
            "  Linux: sudo apt-get install tesseract-ocr tesseract-ocr-urd\n"
            "  Mac: brew install tesseract tesseract-lang"
        )

    # Strategy 1: Try with gentle enhancement (best for clear images)
    logger.info("[OCR] Strategy 1: Gentle enhancement (no binarization)")
    try:
        enhanced = enhance_image_gentle(image_path)
        text = _extract_text_with_fallback(enhanced, language)
        if text and text.strip():
            logger.info(f"[OCR] Gentle enhancement worked! Text length: {len(text)}")
            return text
        logger.info("[OCR] Gentle enhancement produced no text, trying moderate...")
    except Exception as e:
        logger.warning(f"[OCR] Gentle enhancement failed: {e}")

    # Strategy 2: Try with moderate enhancement (for slightly blurry images)
    logger.info("[OCR] Strategy 2: Moderate enhancement (adaptive threshold)")
    try:
        enhanced = enhance_image_moderate(image_path)
        text = _extract_text_with_fallback(enhanced, language)
        if text and text.strip():
            logger.info(f"[OCR] Moderate enhancement worked! Text length: {len(text)}")
            return text
        logger.info("[OCR] Moderate enhancement produced no text, trying aggressive...")
    except Exception as e:
        logger.warning(f"[OCR] Moderate enhancement failed: {e}")

    # Strategy 3: Try with aggressive enhancement (for poor quality images)
    logger.info("[OCR] Strategy 3: Aggressive enhancement")
    try:
        enhanced = enhance_image_aggressive(image_path)
        text = _extract_text_with_fallback(enhanced, language)
        if text and text.strip():
            logger.info(f"[OCR] Aggressive enhancement worked! Text length: {len(text)}")
            return text
        logger.warning("[OCR] All enhancement strategies produced no text")
    except Exception as e:
        logger.warning(f"[OCR] Aggressive enhancement failed: {e}")

    # Strategy 4: Try original image without any enhancement
    logger.info("[OCR] Strategy 4: Original image (no enhancement)")
    try:
        img = _open_and_prepare_image(image_path)
        # Try English only as last resort
        text = _extract_text_with_fallback(img, 'eng')
        if text and text.strip():
            logger.info(f"[OCR] Original image with English only worked! Text length: {len(text)}")
            return text
    except Exception as e:
        logger.warning(f"[OCR] Original image with English failed: {e}")

    logger.error("[OCR] All strategies failed to extract any text")
    return ""


def extract_tables_from_image(image_path: str) -> list[pd.DataFrame]:
    """
    Extract tabular data from an image.
    Uses OCR to find text and then tries to detect table structure.
    Tries multiple enhancement strategies.
    """
    logger.info(f"[OCR] Starting table extraction for: {image_path}")

    if not TESSERACT_AVAILABLE:
        logger.warning("[OCR] Tesseract not available for table extraction")
        return []

    # Try table extraction with different enhancement strategies
    enhancement_strategies = [
        ("gentle", enhance_image_gentle),
        ("moderate", enhance_image_moderate),
        ("aggressive", enhance_image_aggressive),
    ]

    for strategy_name, enhance_fn in enhancement_strategies:
        try:
            logger.info(f"[OCR] Trying table extraction with {strategy_name} enhancement")
            enhanced = enhance_fn(image_path)

            # Use pytesseract's built-in table detection
            data = pytesseract.image_to_data(
                enhanced,
                lang='eng+urd',
                output_type=pytesseract.Output.DATAFRAME
            )
            logger.info(f"[OCR] Got {len(data)} text elements from image_to_data")

            # Filter out low-confidence text
            data = data[data['conf'] > 30]
            logger.info(f"[OCR] After confidence filter (>30): {len(data)} elements")

            if len(data) == 0:
                logger.warning(f"[OCR] No text elements with confidence > 30 ({strategy_name})")
                continue

            # Group text by lines (similar top position)
            data['line_group'] = (data['top'] // 20) * 20  # Group within 20px tolerance

            # Build rows
            rows = []
            for line_group in data['line_group'].unique():
                line_data = data[data['line_group'] == line_group].sort_values('left')
                text = ' '.join(line_data['text'].astype(str))
                rows.append(text)

            logger.info(f"[OCR] Built {len(rows)} text rows")

            # Try to parse as table
            if len(rows) > 2:
                # Assume first row is header
                # Split by multiple spaces to detect columns
                potential_table = []
                for row in rows:
                    cells = re.split(r'\s{2,}', row.strip())
                    potential_table.append(cells)

                # Check if we have consistent column counts
                col_counts = [len(row) for row in potential_table]
                logger.info(f"[OCR] Column counts per row: {col_counts}")
                if col_counts and max(col_counts) > 1:
                    # Pad rows to same length
                    max_cols = max(col_counts)
                    padded_table = []
                    for row in potential_table:
                        padded = row + [''] * (max_cols - len(row))
                        padded_table.append(padded)

                    df = pd.DataFrame(padded_table[1:], columns=padded_table[0] if len(padded_table) > 0 else None)
                    logger.info(f"[OCR] Table extracted with {strategy_name}: shape={df.shape}, columns={list(df.columns)}")
                    return [df]

            logger.warning(f"[OCR] No table structure found with {strategy_name}")

        except Exception as e:
            logger.error(f"[OCR] Table extraction failed with {strategy_name}: {e}")
            continue

    logger.warning("[OCR] All table extraction strategies failed")
    return []


def detect_record_type(text: str) -> str:
    """
    Detect what type of business record this is based on keywords.
    """
    text_lower = text.lower()

    # Sales keywords
    if any(kw in text_lower for kw in ['sale', 'bikri', 'بیع', 'sold', 'customer', 'grahak']):
        return 'sale'

    # Purchase keywords
    if any(kw in text_lower for kw in ['purchase', 'kharid', 'خرید', 'bought', 'supplier', 'faroosh']):
        return 'purchase'

    # Expense keywords
    if any(kw in text_lower for kw in ['expense', 'kharcha', 'خرچہ', 'payment', 'paid']):
        return 'expense'

    # Inventory keywords
    if any(kw in text_lower for kw in ['stock', 'inventory', 'maal', 'مال', 'balance']):
        return 'inventory'

    # Production keywords
    if any(kw in text_lower for kw in ['production', 'bunny', 'بنائی', 'stitch', 'cut']):
        return 'production'

    return 'unknown'


def extract_date_from_text(text: str) -> str | None:
    """Extract a date from text using various patterns."""
    # Common date patterns
    patterns = [
        # dd/mm/yyyy, dd-mm-yyyy
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        # yyyy-mm-dd
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        # Month name formats
        r'(\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4})',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def extract_number_from_text(text: str) -> float | None:
    """Extract a number (amount, quantity) from text."""
    # Find numbers with optional decimals
    # Handle both comma and dot as decimal separators
    patterns = [
        r'Rs\.?\s*([\d,]+\.?\d*)',  # Rs prefix
        r'PKR\.?\s*([\d,]+\.?\d*)',  # PKR prefix
        r'₹\.?\s*([\d,]+\.?\d*)',    # Rupee symbol
        r'([\d,]+\.?\d*)',           # Just number
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            num_str = match.group(1).replace(',', '')
            try:
                return float(num_str)
            except ValueError:
                continue

    return None


def parse_ocr_text_to_records(text: str) -> list[ExtractedRecord]:
    """
    Parse raw OCR text into structured business records.
    Handles various formats found in real register photos.
    """
    records = []
    lines = text.split('\n')

    # Detect overall record type
    overall_type = detect_record_type(text)

    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue

        # Try to extract date
        date = extract_date_from_text(line)

        # Try to extract amounts
        numbers = re.findall(r'[\d,]+\.?\d*', line)
        amounts = [float(n.replace(',', '')) for n in numbers if n and float(n.replace(',', '')) > 0]

        # Build record
        record = ExtractedRecord(
            record_type=overall_type if overall_type != 'unknown' else detect_record_type(line),
            date=date,
            fields={
                'amounts': amounts,
                'text': line,
            },
            confidence=0.7 if date else 0.4,
            raw_line=line,
        )

        if date or amounts:
            records.append(record)

    return records


def process_register_image(image_path: str) -> OCRResult:
    """
    Main entry point: Process a register photo and extract business data.

    Returns structured data that can be mapped to database records.
    Uses adaptive preprocessing for best results.
    """
    logger.info(f"[OCR] ===== Starting process_register_image for: {image_path} =====")
    warnings = []

    if not TESSERACT_AVAILABLE:
        logger.error("[OCR] Tesseract not available - returning empty result")
        return OCRResult(
            raw_text="",
            confidence=0.0,
            tables=[],
            detected_language="unknown",
            warnings=["Tesseract OCR is not installed. Please install it to process images."],
        )

    try:
        # Extract text with both English and Urdu
        raw_text = extract_text_from_image(image_path, language='eng+urd')

        # Detect primary language
        urdu_chars = len(re.findall(r'[؀-ۿ]', raw_text))
        english_chars = len(re.findall(r'[a-zA-Z]', raw_text))
        detected_language = 'urd' if urdu_chars > english_chars else 'eng'
        logger.info(f"[OCR] Language detection: urdu_chars={urdu_chars}, english_chars={english_chars}, detected={detected_language}")

        # Try to extract tables
        tables = extract_tables_from_image(image_path)
        logger.info(f"[OCR] Tables extracted: {len(tables)}")

        # Calculate confidence based on multiple factors
        if not raw_text or not raw_text.strip():
            confidence = 0.0
        else:
            # Base confidence on text density and content quality
            text_len = len(raw_text.strip())
            line_count = len([l for l in raw_text.split('\n') if l.strip()])

            # More lines and characters = higher confidence
            density_score = min(1.0, text_len / 200)
            line_score = min(1.0, line_count / 5)
            confidence = (density_score * 0.6 + line_score * 0.4)

        logger.info(f"[OCR] Confidence: {confidence:.2f}")

        # Add warnings based on quality indicators
        if confidence < 0.2:
            warnings.append("Very little text was extracted. The image may be unclear or contain no readable text.")
        elif confidence < 0.5:
            warnings.append("Some text was extracted but quality may be low. Please review carefully.")
        if urdu_chars > 0 and english_chars > 0:
            warnings.append("Mixed language detected. Some text may not be captured correctly.")
        if not tables:
            warnings.append("No table structure detected. Raw text is shown for manual review.")

        logger.info(f"[OCR] Final result: raw_text_len={len(raw_text)}, tables={len(tables)}, confidence={confidence:.2f}, warnings={warnings}")
        logger.info("[OCR] ===== process_register_image completed =====")

        return OCRResult(
            raw_text=raw_text,
            confidence=confidence,
            tables=tables,
            detected_language=detected_language,
            warnings=warnings,
        )

    except Exception as e:
        logger.exception(f"[OCR] process_register_image failed with exception: {e}")
        return OCRResult(
            raw_text="",
            confidence=0.0,
            tables=[],
            detected_language="unknown",
            warnings=[f"OCR processing failed: {str(e)}"],
        )


def ocr_result_to_dataframe(ocr_result: OCRResult) -> pd.DataFrame:
    """
    Convert OCR result to a pandas DataFrame suitable for ingestion.
    """
    # If we found tables, use the first one
    if ocr_result.tables:
        return ocr_result.tables[0]

    # Otherwise, parse text into records
    records = parse_ocr_text_to_records(ocr_result.raw_text)

    if not records:
        return pd.DataFrame()

    # Convert to DataFrame
    data = []
    for rec in records:
        row = {
            'date': rec.date,
            'record_type': rec.record_type,
            'raw_text': rec.raw_line,
            'confidence': rec.confidence,
        }
        # Add amounts as separate columns
        if rec.fields.get('amounts'):
            amounts = rec.fields['amounts']
            row['amount_1'] = amounts[0] if len(amounts) > 0 else None
            row['amount_2'] = amounts[1] if len(amounts) > 1 else None
            row['amount_3'] = amounts[2] if len(amounts) > 2 else None

        data.append(row)

    return pd.DataFrame(data)
