"""PDF parsing service for extracting work instructions."""
import pdfplumber
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

# Try to import PyMuPDF (optional fallback)
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

logger = logging.getLogger(__name__)


class PDFParser:
    """Service for parsing PDF work instructions."""
    
    def __init__(self, pdf_path: Path):
        """
        Initialize PDF parser.
        
        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = pdf_path
        self.tables: List[Dict[str, Any]] = []
        self.text_content: str = ""
        
    def parse(self) -> Dict[str, Any]:
        """
        Parse PDF and extract structured data.
        
        Returns:
            Dictionary containing extracted data:
            - operations: List of operation details
            - equipment: List of equipment
            - control_points: List of control points
            - raw_text: Full text content
        """
        # Try pdfplumber first for table extraction
        operations = []
        equipment = []
        control_points = []
        
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                # Extract all tables
                for page_num, page in enumerate(pdf.pages):
                    # Extract tables
                    page_tables = page.extract_tables()
                    for table in page_tables:
                        if table:
                            self._process_table(table, operations, equipment, control_points)
                    
                    # Extract text as fallback
                    page_text = page.extract_text()
                    if page_text:
                        self.text_content += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}, trying PyMuPDF")
            # Fallback to PyMuPDF
            self._extract_with_pymupdf()
        
        # If no structured data found, try to parse from text
        if not operations and self.text_content:
            operations = self._parse_operations_from_text(self.text_content)
        
        return {
            "operations": operations,
            "equipment": equipment,
            "control_points": control_points,
            "raw_text": self.text_content
        }
    
    def _process_table(self, table: List[List], operations: List, equipment: List, control_points: List):
        """
        Process extracted table and categorize rows.
        
        Args:
            table: Extracted table data
            operations: List to append operations to
            equipment: List to append equipment to
            control_points: List to append control points to
        """
        if not table or len(table) < 2:
            return
        
        # Assume first row is header
        headers = [str(cell).strip().lower() if cell else "" for cell in table[0]]
        
        # Look for operation-related columns
        operation_cols = {}
        equipment_col = None
        control_point_col = None
        
        for idx, header in enumerate(headers):
            header_lower = header.lower()
            if any(keyword in header_lower for keyword in ["operation", "step", "process", "procedure"]):
                operation_cols["operation"] = idx
            if any(keyword in header_lower for keyword in ["detail", "description", "instruction"]):
                operation_cols["details"] = idx
            if "equipment" in header_lower or "tool" in header_lower:
                equipment_col = idx
            if "control" in header_lower or "checkpoint" in header_lower:
                control_point_col = idx
        
        # Process data rows
        for row in table[1:]:
            if not any(row):  # Skip empty rows
                continue
            
            # Extract operation details
            if operation_cols:
                operation_data = {}
                for key, col_idx in operation_cols.items():
                    if col_idx < len(row) and row[col_idx]:
                        operation_data[key] = str(row[col_idx]).strip()
                
                if operation_data:
                    # Try to extract step-by-step details
                    if "details" in operation_data:
                        steps = self._parse_steps(operation_data["details"])
                        operation_data["steps"] = steps
                    operations.append(operation_data)
            
            # Extract equipment
            if equipment_col is not None and equipment_col < len(row) and row[equipment_col]:
                eq = str(row[equipment_col]).strip()
                if eq and eq not in equipment:
                    equipment.append(eq)
            
            # Extract control points
            if control_point_col is not None and control_point_col < len(row) and row[control_point_col]:
                cp = str(row[control_point_col]).strip()
                if cp and cp not in control_points:
                    control_points.append(cp)
    
    def _parse_steps(self, details_text: str) -> List[str]:
        """
        Parse step-by-step instructions from text.
        
        Args:
            details_text: Text containing step instructions
            
        Returns:
            List of individual steps
        """
        steps = []
        
        # Try to split by common step indicators
        # Look for numbered steps (1., 2., etc.) or bullet points
        import re
        
        # Pattern for numbered steps
        numbered_pattern = r'(?:^|\n)\s*(\d+[\.\)])\s+(.+?)(?=\n\s*\d+[\.\)]|\n\n|$)'
        matches = re.findall(numbered_pattern, details_text, re.MULTILINE | re.DOTALL)
        
        if matches:
            for match in matches:
                step_text = match[1].strip()
                if step_text:
                    steps.append(step_text)
        else:
            # Try bullet points
            bullet_pattern = r'(?:^|\n)\s*[-•*]\s+(.+?)(?=\n\s*[-•*]|\n\n|$)'
            matches = re.findall(bullet_pattern, details_text, re.MULTILINE | re.DOTALL)
            for match in matches:
                step_text = match.strip()
                if step_text:
                    steps.append(step_text)
        
        # If no structured steps found, split by newlines
        if not steps:
            lines = [line.strip() for line in details_text.split('\n') if line.strip()]
            steps = lines
        
        return steps
    
    def _parse_operations_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse operations from unstructured text.
        
        Args:
            text: Raw text content
            
        Returns:
            List of operation dictionaries
        """
        operations = []
        
        # Look for operation sections
        import re
        
        # Pattern for operation headers
        operation_pattern = r'(?:operation|process|step)\s*[:\-]?\s*(.+?)(?=(?:operation|process|step|equipment|control|$))'
        matches = re.finditer(operation_pattern, text, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            operation_text = match.group(1).strip()
            if operation_text:
                steps = self._parse_steps(operation_text)
                operations.append({
                    "operation": f"Operation {len(operations) + 1}",
                    "details": operation_text,
                    "steps": steps
                })
        
        return operations
    
    def _extract_with_pymupdf(self):
        """Fallback extraction using PyMuPDF."""
        if not PYMUPDF_AVAILABLE:
            logger.warning("PyMuPDF not available. Using pdfplumber only.")
            return
        
        try:
            import fitz
            doc = fitz.open(self.pdf_path)
            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text:
                    self.text_content += f"\n--- Page {page_num + 1} ---\n{text}\n"
            doc.close()
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
            raise


def parse_pdf(pdf_path: Path) -> Dict[str, Any]:
    """
    Convenience function to parse a PDF file.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Parsed data dictionary
    """
    parser = PDFParser(pdf_path)
    return parser.parse()

