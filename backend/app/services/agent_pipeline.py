"""Agentic pipeline for PFMEA analysis with self-validation."""
import json
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable
from pathlib import Path
from app.services.llm_service import OllamaService
from app.services.pfmea_engine import RiskMatrix, get_rating_scales, format_rating_justification

logger = logging.getLogger(__name__)


class AgenticPFMEAPipeline:
    """
    Agentic pipeline for PFMEA analysis.
    
    Implements: ANALYZE → RATE → VALIDATE → CORRECT → FINALIZE
    """
    
    def __init__(self):
        """Initialize the agentic pipeline."""
        self.llm = OllamaService()
        self.scales = get_rating_scales()
        self.max_retries = 3
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with rating scale definitions."""
        scales_text = json.dumps(self.scales, indent=2)
        return f"""You are an expert in Process Failure Mode and Effects Analysis (PFMEA). 
Your task is to analyze manufacturing processes and identify potential failure modes, their effects, and assign appropriate ratings.

RATING SCALES:
{scales_text}

You must:
1. Accurately identify failure modes based on process steps
2. Assess potential effects on product performance and manufacturing
3. Assign ratings (1-5) that match the scale criteria exactly
4. Provide clear justifications for each rating
5. Be thorough and conservative in your assessments

Always output valid JSON with the exact structure requested."""
    
    def _build_analyze_prompt(self, process_step: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Build prompt for ANALYZE step."""
        process_text = process_step.get("operation", "")
        details = process_step.get("details", "")
        steps = process_step.get("steps", [])
        equipment = context.get("equipment", [])
        control_points = context.get("control_points", [])
        
        prompt = f"""Analyze the following manufacturing process step and identify potential failure modes.

PROCESS INFORMATION:
- Operation: {process_text}
- Details: {details}
- Steps: {json.dumps(steps, indent=2) if steps else "N/A"}
- Equipment: {', '.join(equipment) if equipment else "N/A"}
- Control Points: {', '.join(control_points) if control_points else "N/A"}

For each potential failure mode, identify:
1. The failure mode (what could go wrong)
2. The potential effect (impact on product/process)

Output JSON with this structure:
{{
  "failure_modes": [
    {{
      "failure_mode": "description of what could fail",
      "potential_effect": "description of the impact"
    }}
  ],
  "reasoning": "explanation of your analysis"
}}"""
        return prompt
    
    def _build_rate_prompt(self, failure_mode: str, effect: str, process_step: Dict[str, Any]) -> str:
        """Build prompt for RATE step."""
        prompt = f"""Rate the following failure mode using the provided scales.

FAILURE MODE: {failure_mode}
POTENTIAL EFFECT: {effect}

PROCESS CONTEXT:
{json.dumps(process_step, indent=2)}

Assign ratings (1-5) for:
1. SEVERITY: Impact of the effect (use product_performance or manufacturing_process criteria)
2. OCCURRENCE: Likelihood of the failure occurring (use qualitative description)
3. DETECTION: Likelihood of detecting the failure before it reaches the customer (lower = better detection)

For each rating, provide:
- The rating value (1-5)
- Detailed justification explaining why this rating matches the scale criteria

Output JSON with this structure:
{{
  "severity": <1-5>,
  "severity_justification": "detailed explanation",
  "occurrence": <1-5>,
  "occurrence_justification": "detailed explanation",
  "detection": <1-5>,
  "detection_justification": "detailed explanation",
  "reasoning": "overall reasoning for the ratings"
}}"""
        return prompt
    
    def _build_validate_prompt(
        self,
        failure_mode: str,
        effect: str,
        severity: int,
        occurrence: int,
        detection: int,
        justifications: Dict[str, str]
    ) -> str:
        """Build prompt for VALIDATE step."""
        severity_criteria = self.scales["severity"].get(str(severity), {})
        occurrence_criteria = self.scales["occurrence"].get(str(occurrence), {})
        detection_criteria = self.scales["detection"].get(str(detection), {})
        
        prompt = f"""Review and validate the following PFMEA ratings for consistency.

FAILURE MODE: {failure_mode}
POTENTIAL EFFECT: {effect}

CURRENT RATINGS:
- Severity: {severity}
  Justification: {justifications.get('severity', 'N/A')}
  Scale Criteria for {severity}: {severity_criteria}
  
- Occurrence: {occurrence}
  Justification: {justifications.get('occurrence', 'N/A')}
  Scale Criteria for {occurrence}: {occurrence_criteria}
  
- Detection: {detection}
  Justification: {justifications.get('detection', 'N/A')}
  Scale Criteria for {detection}: {detection_criteria}

Check if:
1. Each rating matches its scale criteria
2. The justifications support the assigned ratings
3. The ratings are consistent with each other
4. Any ratings need adjustment

Output JSON with this structure:
{{
  "is_valid": true/false,
  "issues": ["list of any issues found"],
  "corrected_ratings": {{
    "severity": <1-5 or null if correct>,
    "occurrence": <1-5 or null if correct>,
    "detection": <1-5 or null if correct>
  }},
  "correction_reasoning": "explanation of any corrections needed"
}}"""
        return prompt
    
    async def analyze_step(
        self,
        process_step: Dict[str, Any],
        context: Dict[str, Any],
        progress_callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Run full agentic pipeline for a process step.
        
        Args:
            process_step: Process step information
            context: Additional context (equipment, control points, etc.)
            
        Returns:
            List of PFMEA results (one per failure mode)
        """
        system_prompt = self._build_system_prompt()
        results = []
        
        # STEP 1: ANALYZE
        step_name = process_step.get('operation', 'Unknown')
        logger.info(f"ANALYZE: Processing step '{step_name}'")
        
        if progress_callback:
            await progress_callback({
                "step": "analyze",
                "status": "started",
                "message": f"Analyzing process step: {step_name}",
                "process_step": step_name,
                "llm_action": "Calling LLM to identify failure modes..."
            })
        
        logger.info(f"Building analyze prompt for step: {step_name}")
        analyze_prompt = self._build_analyze_prompt(process_step, context)
        logger.info(f"Prompt length: {len(analyze_prompt)} characters")
        
        if progress_callback:
            await progress_callback({
                "step": "analyze",
                "status": "processing",
                "message": "LLM is analyzing the process step...",
                "llm_action": "Generating failure modes"
            })
        
        analyze_result = await self.llm.generate(analyze_prompt, system_prompt)
        logger.info(f"ANALYZE result: {json.dumps(analyze_result, indent=2)[:500]}")
        
        failure_modes = analyze_result.get("failure_modes", [])
        analysis_reasoning = analyze_result.get("reasoning", "")
        
        if progress_callback:
            await progress_callback({
                "step": "analyze",
                "status": "completed",
                "message": f"Identified {len(failure_modes)} potential failure mode(s)",
                "reasoning": analysis_reasoning,
                "failure_modes_count": len(failure_modes)
            })
        
        if not failure_modes:
            logger.warning("No failure modes identified")
            return results
        
        # Process each failure mode
        for fm_data in failure_modes:
            failure_mode = fm_data.get("failure_mode", "")
            effect = fm_data.get("potential_effect", "")
            
            if not failure_mode or not effect:
                continue
            
            # STEP 2: RATE
            logger.info(f"RATE: Rating failure mode '{failure_mode[:50]}...'")
            
            if progress_callback:
                await progress_callback({
                    "step": "rate",
                    "status": "started",
                    "message": f"Rating failure mode: {failure_mode[:100]}...",
                    "failure_mode": failure_mode,
                    "effect": effect,
                    "llm_action": "Calling LLM to assign severity, occurrence, and detection ratings..."
                })
            
            logger.info(f"Building rate prompt for failure mode: {failure_mode[:50]}")
            rate_prompt = self._build_rate_prompt(failure_mode, effect, process_step)
            
            if progress_callback:
                await progress_callback({
                    "step": "rate",
                    "status": "processing",
                    "message": "LLM is assigning ratings...",
                    "llm_action": "Evaluating ratings against scale criteria"
                })
            
            rate_result = await self.llm.generate(rate_prompt, system_prompt)
            logger.info(f"RATE result: S={rate_result.get('severity')}, O={rate_result.get('occurrence')}, D={rate_result.get('detection')}")
            
            severity = rate_result.get("severity")
            occurrence = rate_result.get("occurrence")
            detection = rate_result.get("detection")
            
            # Validate ratings are in range
            if not all(isinstance(r, int) and 1 <= r <= 5 for r in [severity, occurrence, detection]):
                logger.warning(f"Invalid ratings: S={severity}, O={occurrence}, D={detection}")
                continue
            
            justifications = {
                "severity": rate_result.get("severity_justification", ""),
                "occurrence": rate_result.get("occurrence_justification", ""),
                "detection": rate_result.get("detection_justification", "")
            }
            
            if progress_callback:
                await progress_callback({
                    "step": "rate",
                    "status": "completed",
                    "message": f"Assigned ratings: S={severity}, O={occurrence}, D={detection}",
                    "ratings": {
                        "severity": severity,
                        "occurrence": occurrence,
                        "detection": detection
                    },
                    "justifications": justifications
                })
            
            # STEP 3 & 4: VALIDATE & CORRECT (with retries)
            retry_count = 0
            validation_reasoning = ""
            correction_reasoning = ""
            
            while retry_count < self.max_retries:
                logger.info(f"VALIDATE: Attempt {retry_count + 1} for failure mode '{failure_mode[:50]}...'")
                
                if progress_callback:
                    await progress_callback({
                        "step": "validate",
                        "status": "started",
                        "message": f"Validating ratings (attempt {retry_count + 1}/{self.max_retries})...",
                        "attempt": retry_count + 1
                    })
                
                validate_prompt = self._build_validate_prompt(
                    failure_mode, effect, severity, occurrence, detection, justifications
                )
                validate_result = await self.llm.generate(validate_prompt, system_prompt)
                
                is_valid = validate_result.get("is_valid", False)
                validation_reasoning = validate_result.get("reasoning", "")
                issues = validate_result.get("issues", [])
                
                if progress_callback:
                    await progress_callback({
                        "step": "validate",
                        "status": "completed",
                        "message": "Validation completed" if is_valid else f"Validation found issues: {', '.join(issues) if issues else 'Ratings need adjustment'}",
                        "is_valid": is_valid,
                        "issues": issues,
                        "reasoning": validation_reasoning
                    })
                
                if is_valid:
                    break
                
                # CORRECT: Adjust ratings if needed
                if progress_callback:
                    await progress_callback({
                        "step": "correct",
                        "status": "started",
                        "message": "Correcting ratings based on validation feedback...",
                    })
                
                corrected = validate_result.get("corrected_ratings", {})
                if corrected.get("severity"):
                    severity = corrected["severity"]
                if corrected.get("occurrence"):
                    occurrence = corrected["occurrence"]
                if corrected.get("detection"):
                    detection = corrected["detection"]
                
                correction_reasoning = validate_result.get("correction_reasoning", "")
                retry_count += 1
                
                if progress_callback:
                    await progress_callback({
                        "step": "correct",
                        "status": "completed",
                        "message": "Ratings corrected, re-validating...",
                        "correction_reasoning": correction_reasoning
                    })
                
                if retry_count < self.max_retries:
                    # Re-rate with corrections
                    rate_prompt = self._build_rate_prompt(failure_mode, effect, process_step)
                    rate_result = await self.llm.generate(rate_prompt, system_prompt)
                    severity = rate_result.get("severity", severity)
                    occurrence = rate_result.get("occurrence", occurrence)
                    detection = rate_result.get("detection", detection)
                    justifications = {
                        "severity": rate_result.get("severity_justification", ""),
                        "occurrence": rate_result.get("occurrence_justification", ""),
                        "detection": rate_result.get("detection_justification", "")
                    }
            
            # STEP 5: FINALIZE
            if progress_callback:
                await progress_callback({
                    "step": "finalize",
                    "status": "started",
                    "message": "Finalizing PFMEA result...",
                })
            
            confidence = 1.0 - (0.2 * retry_count)
            confidence_str = f"{confidence:.1f}"
            
            # Calculate RPN and risk level
            rpn = RiskMatrix.calculate_rpn(severity, occurrence, detection)
            risk_level = RiskMatrix.get_risk_level(severity, occurrence, detection)
            action_required = RiskMatrix.get_action_required(risk_level)
            
            if progress_callback:
                await progress_callback({
                    "step": "finalize",
                    "status": "completed",
                    "message": f"PFMEA result finalized: RPN={rpn}, Risk={risk_level.upper()}",
                    "rpn": rpn,
                    "risk_level": risk_level,
                    "action_required": action_required
                })
            
            # Format justifications with scale criteria
            severity_just = format_rating_justification(
                "severity", severity, justifications["severity"], self.scales
            )
            occurrence_just = format_rating_justification(
                "occurrence", occurrence, justifications["occurrence"], self.scales
            )
            detection_just = format_rating_justification(
                "detection", detection, justifications["detection"], self.scales
            )
            
            result = {
                "process": process_step.get("operation", "Unknown"),
                "subprocess": "\n".join(process_step.get("steps", [])) or process_step.get("details", ""),
                "failure_mode": failure_mode,
                "potential_effect": effect,
                "severity": severity,
                "severity_justification": severity_just,
                "occurrence": occurrence,
                "occurrence_justification": occurrence_just,
                "detection": detection,
                "detection_justification": detection_just,
                "rpn": rpn,
                "risk_level": risk_level,
                "action_required": action_required,
                "control_point": ", ".join(context.get("control_points", [])),
                "confidence": confidence_str,
                "analysis_reasoning": analysis_reasoning,
                "validation_reasoning": validation_reasoning,
                "correction_reasoning": correction_reasoning
            }
            
            results.append(result)
            logger.info(f"FINALIZE: Completed analysis for '{failure_mode[:50]}...' (RPN={rpn}, Risk={risk_level})")
        
        return results

