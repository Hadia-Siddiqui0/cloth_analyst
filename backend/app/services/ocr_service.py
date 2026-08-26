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


def enhance_image_for_ocr(image_path: str) -> Image.Image:
    """
    Apply image enhancements to improve OCR accuracy.
    Handles low-quality photos, uneven lighting, and blurry text.
    """
    img = Image.open(image_path)

    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # Resize if too small (helps OCR)
    width, height = img.size
    if width < 1000 or height < 1000:
        scale = max(1000 / width, 1000 / height)
        new_size = (int(width * scale), int(height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    # Convert to grayscale
    img = img.convert('L')

    # Increase contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)

    # Sharpen
    img = img.filter(ImageFilter.SHARPEN)

    # Binarize (black and white)
    threshold = 150
    img = img.point(lambda x: 255 if x > threshold else 0, '1')

    return img.convert('RGB')


def extract_text_from_image(image_path: str, language: str = 'eng+urd') -> str:
    """
    Extract text from an image using OCR.
    Supports English ('eng'), Urdu ('urd'), or both.
    """
    if not TESSERACT_AVAILABLE:
        raise RuntimeError(
            "Tesseract OCR is not installed. Please install it:\n"
            "  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki\n"
            "  Linux: sudo apt-get install tesseract-ocr tesseract-ocr-urd\n"
            "  Mac: brew install tesseract tesseract-lang"
        )

    # Enhance image for better OCR
    enhanced = enhance_image_for_ocr(image_path)

    # Run OCR
    try:
        text = pytesseract.image_to_string(
            enhanced,
            lang=language,
            config='--psm 6'  # Assume uniform block of text
        )
        return text
    except Exception as e:
        # Fallback to English only if Urdu fails
        if 'urd' in language:
            return pytesseract.image_to_string(enhanced, lang='eng', config='--psm 6')
        raise


def extract_tables_from_image(image_path: str) -> list[pd.DataFrame]:
    """
    Extract tabular data from an image.
    Uses OCR to find text and then tries to detect table structure.
    """
    if not TESSERACT_AVAILABLE:
        return []

    enhanced = enhance_image_for_ocr(image_path)

    try:
        # Use pytesseract's built-in table detection
        data = pytesseract.image_to_data(
            enhanced,
            lang='eng+urd',
            output_type=pytesseract.Output.DATAFRAME
        )

        # Filter out low-confidence text
        data = data[data['conf'] > 30]

        if len(data) == 0:
            return []

        # Group text by lines (similar top position)
        data['line_group'] = (data['top'] // 20) * 20  # Group within 20px tolerance

        # Build rows
        rows = []
        for line_group in data['line_group'].unique():
            line_data = data[data['line_group'] == line_group].sort_values('left')
            text = ' '.join(line_data['text'].astype(str))
            rows.append(text)

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
            if col_counts and max(col_counts) > 1:
                # Pad rows to same length
                max_cols = max(col_counts)
                padded_table = []
                for row in potential_table:
                    padded = row + [''] * (max_cols - len(row))
                    padded_table.append(padded)

                df = pd.DataFrame(padded_table[1:], columns=padded_table[0] if len(padded_table) > 0 else None)
                return [df]

        return []

    except Exception:
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
    """
    warnings = []

    if not TESSERACT_AVAILABLE:
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

        # Try to extract tables
        tables = extract_tables_from_image(image_path)

        # Calculate confidence based on text density
        confidence = min(1.0, len(raw_text) / 500) if raw_text else 0.0

        # Add warnings for low confidence
        if confidence < 0.3:
            warnings.append("Low text density detected. Image quality may be poor.")
        if urdu_chars > 0 and english_chars > 0:
            warnings.append("Mixed language detected. Some text may not be captured correctly.")

        return OCRResult(
            raw_text=raw_text,
            confidence=confidence,
            tables=tables,
            detected_language=detected_language,
            warnings=warnings,
        )

    except Exception as e:
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
