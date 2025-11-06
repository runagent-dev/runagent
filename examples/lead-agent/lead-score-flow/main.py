#!/usr/bin/env python
"""
RunAgent-compatible entry points for Lead Score Flow
"""
import asyncio
import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
if src_dir.exists():
    sys.path.insert(0, str(src_dir))

# Now import the modules
from lead_score_flow.constants import JOB_DESCRIPTION
from lead_score_flow.crews.lead_response_crew.lead_response_crew import LeadResponseCrew
from lead_score_flow.crews.lead_score_crew.lead_score_crew import LeadScoreCrew
from lead_score_flow.types import Candidate, CandidateScore
from lead_score_flow.utils.candidateUtils import combine_candidates_with_scores


def load_candidates_from_csv() -> List[Candidate]:
    """Load candidates from the CSV file"""
    csv_file = current_dir / "src" / "lead_score_flow" / "leads.csv"
    
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found at {csv_file}")
    
    candidates = []
    with open(csv_file, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            candidate = Candidate(**row)
            candidates.append(candidate)
    
    return candidates


async def score_single_candidate_async(
    candidate: Candidate,
    job_description: str = None,
    additional_instructions: str = ""
) -> CandidateScore:
    """Score a single candidate asynchronously"""
    # Use provided job_description or fall back to constant
    job_desc = job_description if job_description else JOB_DESCRIPTION
    
    result = await (
        LeadScoreCrew()
        .crew()
        .kickoff_async(
            inputs={
                "candidate_id": candidate.id,
                "name": candidate.name,
                "bio": candidate.bio,
                "job_description": job_desc,
                "additional_instructions": additional_instructions,
            }
        )
    )
    return result.pydantic


def score_single_candidate(
    candidate_id: str = None,
    name: str = None,
    email: str = None,
    bio: str = None,
    skills: str = None,
    job_description: str = None,
    additional_instructions: str = ""
) -> Dict[str, Any]:
    """
    RunAgent entry point: Score a single candidate
    
    Args:
        candidate_id: Unique identifier for the candidate
        name: Candidate's name
        email: Candidate's email
        bio: Candidate's biography/description
        skills: Candidate's skills (comma-separated)
        job_description: Job description to match against (optional)
        additional_instructions: Additional scoring criteria
    
    Returns:
        Dictionary with candidate score and reasoning
    """
    try:
        # Create candidate object
        candidate = Candidate(
            id=candidate_id or "unknown",
            name=name or "Unknown",
            email=email or "unknown@example.com",
            bio=bio or "",
            skills=skills or ""
        )
        
        # Run async scoring
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # Create new loop if one is already running
            try:
                import nest_asyncio
                nest_asyncio.apply()
            except ImportError:
                pass
            score = loop.run_until_complete(
                score_single_candidate_async(candidate, job_description, additional_instructions)
            )
        else:
            score = asyncio.run(
                score_single_candidate_async(candidate, job_description, additional_instructions)
            )
        
        return {
            "success": True,
            "candidate_id": score.id,
            "candidate_name": name,
            "score": score.score,
            "reason": score.reason,
            "job_description": job_description or JOB_DESCRIPTION
        }
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "candidate_id": candidate_id,
            "candidate_name": name
        }


async def score_all_candidates_async(
    candidates: List[Candidate],
    job_description: str = None,
    additional_instructions: str = ""
) -> List[CandidateScore]:
    """Score all candidates asynchronously"""
    tasks = []
    
    for candidate in candidates:
        task = asyncio.create_task(
            score_single_candidate_async(candidate, job_description, additional_instructions)
        )
        tasks.append(task)
    
    scores = await asyncio.gather(*tasks)
    return scores


async def generate_email_async(
    candidate_id: str,
    name: str,
    bio: str,
    proceed_with_candidate: bool
) -> str:
    """Generate follow-up email for a candidate"""
    result = await (
        LeadResponseCrew()
        .crew()
        .kickoff_async(
            inputs={
                "candidate_id": candidate_id,
                "name": name,
                "bio": bio,
                "proceed_with_candidate": proceed_with_candidate,
            }
        )
    )
    return result.raw


def run_flow(
    top_n: int = 3,
    job_description: str = None,
    additional_instructions: str = "",
    generate_emails: bool = True,
    candidates: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    RunAgent entry point: Run the complete lead scoring flow
    
    Args:
        top_n: Number of top candidates to select (default: 3)
        job_description: Job description to match against (optional)
        additional_instructions: Additional scoring criteria
        generate_emails: Whether to generate follow-up emails (default: True)
        candidates: Optional list of candidates as dicts. If not provided, loads from CSV.
    
    Returns:
        Dictionary with scored candidates and email generation status
    """
    try:
        # Load candidates from parameter or CSV file
        if candidates:
            # Debug: Log what we received
            print(f"[DEBUG] Candidates type: {type(candidates)}")
            print(f"[DEBUG] Candidates value (first 200 chars): {str(candidates)[:200]}")
            
            # Handle case where candidates itself might be a JSON string
            if isinstance(candidates, str):
                print(f"[DEBUG] Candidates is a JSON string, parsing...")
                try:
                    candidates = json.loads(candidates)
                    print(f"[DEBUG] Parsed candidates to type: {type(candidates)}")
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid candidates format: expected list or JSON string, got: {candidates[:200] if len(candidates) > 200 else candidates}")
            
            # Ensure candidates is a list
            if not isinstance(candidates, list):
                raise ValueError(f"Expected list of candidates, got {type(candidates)}: {candidates}")
            
            print(f"[DEBUG] Received {len(candidates)} candidates")
            if candidates:
                print(f"[DEBUG] First candidate type: {type(candidates[0])}")
                print(f"[DEBUG] First candidate value: {candidates[0]}")
            
            # Convert dicts to Candidate objects
            candidate_objects = []
            for idx, c in enumerate(candidates):
                # Handle case where c might be a JSON string (due to double serialization)
                if isinstance(c, str):
                    print(f"[DEBUG] Candidate {idx} is a string, parsing JSON...")
                    try:
                        c = json.loads(c)
                        print(f"[DEBUG] Parsed to: {type(c)}")
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Invalid candidate format: expected dict or JSON string, got: {c[:100] if len(str(c)) > 100 else c}")
                # Ensure c is a dict before unpacking
                if not isinstance(c, dict):
                    raise ValueError(f"Expected dict or JSON string, got {type(c)}: {c}")
                candidate_objects.append(Candidate(**c))
            candidates = candidate_objects
        else:
            candidates = load_candidates_from_csv()
        
        # Score all candidates
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            try:
                import nest_asyncio
                nest_asyncio.apply()
            except ImportError:
                pass
            scores = loop.run_until_complete(
                score_all_candidates_async(candidates, job_description, additional_instructions)
            )
        else:
            scores = asyncio.run(
                score_all_candidates_async(candidates, job_description, additional_instructions)
            )
        
        # Combine candidates with scores
        scored_candidates = combine_candidates_with_scores(candidates, scores)
        
        # Sort by score
        sorted_candidates = sorted(
            scored_candidates, key=lambda c: c.score, reverse=True
        )
        
        # Get top N candidates
        top_candidates = sorted_candidates[:top_n]
        top_candidate_ids = {c.id for c in top_candidates}
        
        result = {
            "success": True,
            "total_candidates": len(candidates),
            "top_candidates": [
                {
                    "id": c.id,
                    "name": c.name,
                    "email": c.email,
                    "score": c.score,
                    "reason": c.reason,
                    "bio": c.bio,
                    "skills": c.skills
                }
                for c in top_candidates
            ],
            "all_candidates": [
                {
                    "id": c.id,
                    "name": c.name,
                    "email": c.email,
                    "score": c.score,
                    "reason": c.reason
                }
                for c in sorted_candidates
            ]
        }
        
        # Generate emails if requested
        if generate_emails:
            emails_generated = []
            
            async def generate_all_emails():
                tasks = []
                for candidate in sorted_candidates:
                    proceed = candidate.id in top_candidate_ids
                    task = asyncio.create_task(
                        generate_email_async(
                            candidate.id,
                            candidate.name,
                            candidate.bio,
                            proceed
                        )
                    )
                    tasks.append((candidate, proceed, task))
                
                results = []
                for candidate, proceed, task in tasks:
                    email_content = await task
                    results.append({
                        "candidate_id": candidate.id,
                        "candidate_name": candidate.name,
                        "candidate_email": candidate.email,
                        "proceed_with_candidate": proceed,
                        "email_content": email_content
                    })
                return results
            
            if loop.is_running():
                emails_generated = loop.run_until_complete(generate_all_emails())
            else:
                emails_generated = asyncio.run(generate_all_emails())
            
            result["emails_generated"] = emails_generated
            result["emails_saved"] = len(emails_generated)
        
        return result
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

