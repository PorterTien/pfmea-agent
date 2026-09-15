"""API routes for PFMEA analysis."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path
import logging

from app.models import get_db, Analysis, PFMEAResult
from app.schemas.pfmea import (
    AnalysisSchema,
    AnalysisWithResultsSchema,
    PFMEAResultSchema,
    AnalysisStatusResponse
)
from app.services.pdf_parser import parse_pdf
from app.services.agent_pipeline import AgenticPFMEAPipeline

logger = logging.getLogger(__name__)

router = APIRouter()


async def process_analysis(analysis_id: int):
    """
    Background task to process PDF analysis.
    
    Args:
        analysis_id: Analysis ID
    """
    from app.models.database import SessionLocal
    from app.api.routes.websocket import get_manager
    
    db = SessionLocal()
    manager = get_manager()
    
    async def send_progress(message: dict):
        """Send progress update via WebSocket."""
        await manager.send_message(analysis_id, {
            "type": "progress",
            "analysis_id": analysis_id,
            **message
        })
    
    try:
        # Get analysis
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            logger.error(f"Analysis {analysis_id} not found")
            return
        
        # Update status
        analysis.status = "processing"
        db.commit()
        
        await send_progress({
            "step": "init",
            "status": "started",
            "message": f"Starting analysis of {analysis.filename}",
            "filename": analysis.filename
        })
        
        # Parse PDF
        await send_progress({
            "step": "parse",
            "status": "started",
            "message": "Parsing PDF file..."
        })
        
        pdf_path = Path(analysis.file_path)
        parsed_data = parse_pdf(pdf_path)
        
        await send_progress({
            "step": "parse",
            "status": "completed",
            "message": "PDF parsed successfully"
        })
        
        # Initialize agentic pipeline
        pipeline = AgenticPFMEAPipeline()
        
        # Process each operation
        operations = parsed_data.get("operations", [])
        total_operations = len(operations)
        
        if total_operations == 0:
            analysis.status = "failed"
            analysis.error_message = "No operations found in PDF"
            db.commit()
            await send_progress({
                "step": "error",
                "status": "failed",
                "message": "No operations found in PDF"
            })
            return
        
        await send_progress({
            "step": "operations",
            "status": "started",
            "message": f"Found {total_operations} operation(s) to analyze",
            "total_operations": total_operations
        })
        
        context = {
            "equipment": parsed_data.get("equipment", []),
            "control_points": parsed_data.get("control_points", [])
        }
        
        all_results = []
        for idx, operation in enumerate(operations):
            logger.info(f"Processing operation {idx + 1}/{total_operations}")
            await send_progress({
                "step": "operation",
                "status": "started",
                "message": f"Processing operation {idx + 1} of {total_operations}",
                "operation_number": idx + 1,
                "total_operations": total_operations,
                "operation_name": operation.get("operation", "Unknown")
            })
            
            try:
                logger.info(f"Starting agentic pipeline for operation {idx + 1}")
                results = await pipeline.analyze_step(operation, context, send_progress)
                logger.info(f"Pipeline completed for operation {idx + 1}: {len(results)} failure modes found")
                all_results.extend(results)
                
                await send_progress({
                    "step": "operation",
                    "status": "completed",
                    "message": f"Operation {idx + 1} completed: {len(results)} failure mode(s) identified",
                    "operation_number": idx + 1,
                    "failure_modes_found": len(results)
                })
            except Exception as e:
                logger.error(f"Error processing operation {idx + 1}: {e}")
                await send_progress({
                    "step": "operation",
                    "status": "error",
                    "message": f"Error processing operation {idx + 1}: {str(e)}",
                    "operation_number": idx + 1
                })
                continue
        
        # Save results to database
        await send_progress({
            "step": "save",
            "status": "started",
            "message": f"Saving {len(all_results)} PFMEA result(s) to database..."
        })
        
        for result_data in all_results:
            pfmea_result = PFMEAResult(
                analysis_id=analysis_id,
                **result_data
            )
            db.add(pfmea_result)
        
        analysis.status = "completed"
        db.commit()
        
        await send_progress({
            "step": "complete",
            "status": "completed",
            "message": f"Analysis completed successfully with {len(all_results)} result(s)",
            "total_results": len(all_results)
        })
        
        logger.info(f"Analysis {analysis_id} completed with {len(all_results)} results")
        
    except Exception as e:
        logger.error(f"Error processing analysis {analysis_id}: {e}")
        import traceback
        error_trace = traceback.format_exc()
        logger.error(error_trace)
        
        try:
            await send_progress({
                "step": "error",
                "status": "failed",
                "message": f"Analysis failed: {str(e)}",
                "error": str(e)
            })
        except:
            pass
        
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if analysis:
            analysis.status = "failed"
            analysis.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/analyze/{analysis_id}", response_model=AnalysisStatusResponse)
async def start_analysis(
    analysis_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start PFMEA analysis for an uploaded PDF.
    
    Args:
        analysis_id: Analysis ID
        background_tasks: FastAPI background tasks
        db: Database session
        
    Returns:
        Analysis status response
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if analysis.status == "processing":
        return AnalysisStatusResponse(
            analysis_id=analysis_id,
            status="processing",
            message="Analysis already in progress"
        )
    
    if analysis.status == "completed":
        return AnalysisStatusResponse(
            analysis_id=analysis_id,
            status="completed",
            message="Analysis already completed"
        )
    
    # Start background processing
    background_tasks.add_task(process_analysis, analysis_id)
    
    return AnalysisStatusResponse(
        analysis_id=analysis_id,
        status="processing",
        message="Analysis started"
    )


@router.get("/analyses")
async def list_analyses(db: Session = Depends(get_db)):
    """
    List all analyses.
    
    Args:
        db: Database session
        
    Returns:
        List of analyses
    """
    try:
        logger.info("Listing analyses...")
        analyses = db.query(Analysis).order_by(Analysis.uploaded_at.desc()).all()
        logger.info(f"Found {len(analyses)} analyses")
        # Convert to dict format for JSON serialization
        result = []
        for a in analyses:
            result.append({
                "id": a.id,
                "filename": a.filename,
                "status": a.status,
                "uploaded_at": a.uploaded_at.isoformat() if a.uploaded_at else None,
                "error_message": a.error_message
            })
        logger.info(f"Returning {len(result)} analyses")
        return result
    except Exception as e:
        logger.error(f"Error listing analyses: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to list analyses: {str(e)}")


@router.get("/analyses/{analysis_id}", response_model=AnalysisWithResultsSchema)
async def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    """
    Get analysis with results.
    
    Args:
        analysis_id: Analysis ID
        db: Database session
        
    Returns:
        Analysis with PFMEA results
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return analysis


@router.get("/analyses/{analysis_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(analysis_id: int, db: Session = Depends(get_db)):
    """
    Get analysis status.
    
    Args:
        analysis_id: Analysis ID
        db: Database session
        
    Returns:
        Analysis status
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return AnalysisStatusResponse(
        analysis_id=analysis_id,
        status=analysis.status,
        message=analysis.error_message
    )


@router.get("/analyses/{analysis_id}/results", response_model=List[PFMEAResultSchema])
async def get_analysis_results(analysis_id: int, db: Session = Depends(get_db)):
    """
    Get PFMEA results for an analysis.
    
    Args:
        analysis_id: Analysis ID
        db: Database session
        
    Returns:
        List of PFMEA results
    """
    results = db.query(PFMEAResult).filter(
        PFMEAResult.analysis_id == analysis_id
    ).all()
    
    return results

