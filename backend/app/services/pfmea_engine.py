"""RPN calculation and risk matrix engine."""
from typing import Literal, Tuple
import json
from pathlib import Path

# Risk levels
RiskLevel = Literal["low", "medium", "high"]
ActionRequired = Literal["yes", "no", "maybe"]


class RiskMatrix:
    """
    Risk prioritization matrix based on Severity, Occurrence, and Detection ratings.
    
    Implements the exact matrix from the PFMEA specification:
    - Green (Low): No further controls required
    - Yellow (Medium): Pursue additional controls or document
    - Red (High): Apply controls, design/process change may be required
    """
    
    # Risk matrix definition based on specification
    # Format: {severity: {occurrence: {detection: risk_level}}}
    # Risk levels: "low" (green), "medium" (yellow), "high" (red)
    
    MATRIX = {
        1: {  # S=1: All green
            1: {1: "low", 2: "low", 3: "low", 4: "low", 5: "low"},
            2: {1: "low", 2: "low", 3: "low", 4: "low", 5: "low"},
            3: {1: "low", 2: "low", 3: "low", 4: "low", 5: "low"},
            4: {1: "low", 2: "low", 3: "low", 4: "low", 5: "low"},
            5: {1: "low", 2: "low", 3: "low", 4: "low", 5: "low"},
        },
        2: {  # S=2
            1: {1: "low", 2: "low", 3: "low", 4: "low", 5: "low"},
            2: {1: "low", 2: "low", 3: "low", 4: "low", 5: "low"},
            3: {1: "low", 2: "low", 3: "low", 4: "medium", 5: "medium"},
            4: {1: "low", 2: "low", 3: "medium", 4: "medium", 5: "medium"},
            5: {1: "low", 2: "medium", 3: "medium", 4: "medium", 5: "medium"},
        },
        3: {  # S=3
            1: {1: "low", 2: "low", 3: "low", 4: "low", 5: "low"},
            2: {1: "low", 2: "low", 3: "medium", 4: "medium", 5: "medium"},
            3: {1: "low", 2: "medium", 3: "medium", 4: "medium", 5: "medium"},
            4: {1: "medium", 2: "medium", 3: "high", 4: "high", 5: "high"},
            5: {1: "medium", 2: "medium", 3: "high", 4: "high", 5: "high"},
        },
        4: {  # S=4
            1: {1: "low", 2: "low", 3: "medium", 4: "medium", 5: "medium"},
            2: {1: "low", 2: "medium", 3: "medium", 4: "medium", 5: "medium"},
            3: {1: "medium", 2: "medium", 3: "high", 4: "high", 5: "high"},
            4: {1: "medium", 2: "medium", 3: "high", 4: "high", 5: "high"},
            5: {1: "medium", 2: "medium", 3: "high", 4: "high", 5: "high"},
        },
        5: {  # S=5
            1: {1: "low", 2: "medium", 3: "medium", 4: "medium", 5: "medium"},
            2: {1: "medium", 2: "medium", 3: "high", 4: "high", 5: "high"},
            3: {1: "medium", 2: "medium", 3: "high", 4: "high", 5: "high"},
            4: {1: "medium", 2: "medium", 3: "high", 4: "high", 5: "high"},
            5: {1: "medium", 2: "medium", 3: "high", 4: "high", 5: "high"},
        },
    }
    
    @classmethod
    def get_risk_level(cls, severity: int, occurrence: int, detection: int) -> RiskLevel:
        """
        Get risk level from severity, occurrence, and detection ratings.
        
        Args:
            severity: Severity rating (1-5)
            occurrence: Occurrence rating (1-5)
            detection: Detection rating (1-5)
            
        Returns:
            Risk level: "low", "medium", or "high"
        """
        # Validate inputs
        if not (1 <= severity <= 5 and 1 <= occurrence <= 5 and 1 <= detection <= 5):
            raise ValueError(f"Invalid ratings: S={severity}, O={occurrence}, D={detection}. All must be 1-5.")
        
        return cls.MATRIX[severity][occurrence][detection]
    
    @classmethod
    def get_action_required(cls, risk_level: RiskLevel) -> ActionRequired:
        """
        Determine action required based on risk level.
        
        Args:
            risk_level: Risk level from matrix
            
        Returns:
            Action required: "yes", "no", or "maybe"
        """
        if risk_level == "high":
            return "yes"
        elif risk_level == "medium":
            return "maybe"
        else:  # low
            return "no"
    
    @classmethod
    def calculate_rpn(cls, severity: int, occurrence: int, detection: int) -> int:
        """
        Calculate Risk Priority Number.
        
        Note: Traditional RPN = S * O * D, but we use the matrix-based approach
        which may have different prioritization. For display purposes, we'll
        calculate traditional RPN but prioritize based on matrix.
        
        Args:
            severity: Severity rating (1-5)
            occurrence: Occurrence rating (1-5)
            detection: Detection rating (1-5)
            
        Returns:
            RPN value (1-125)
        """
        if not (1 <= severity <= 5 and 1 <= occurrence <= 5 and 1 <= detection <= 5):
            raise ValueError(f"Invalid ratings: S={severity}, O={occurrence}, D={detection}. All must be 1-5.")
        
        return severity * occurrence * detection


def get_rating_scales() -> dict:
    """
    Load rating scales from JSON file.
    
    Returns:
        Dictionary containing severity, occurrence, and detection scales
    """
    scales_path = Path(__file__).parent.parent.parent / "rating_scales.json"
    with open(scales_path, "r") as f:
        return json.load(f)


def format_rating_justification(
    rating_type: str,
    rating: int,
    justification: str,
    scales: dict
) -> str:
    """
    Format rating justification with scale criteria.
    
    Args:
        rating_type: "severity", "occurrence", or "detection"
        rating: Rating value (1-5)
        justification: LLM-generated justification
        scales: Rating scales dictionary
        
    Returns:
        Formatted justification string
    """
    scale_data = scales.get(rating_type, {}).get(str(rating), {})
    
    if rating_type == "severity":
        criteria = scale_data.get("product_performance", "") or scale_data.get("manufacturing_process", "")
    elif rating_type == "occurrence":
        criteria = scale_data.get("qualitative", "")
    else:  # detection
        criteria = scale_data.get("qualitative_1", "") or scale_data.get("qualitative_3", "")
    
    if criteria:
        return f"{justification}\n\nCriteria for {rating_type.upper()}={rating}: {criteria}"
    return justification




