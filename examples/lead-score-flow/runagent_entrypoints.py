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
    job_description: str,
    additional_instructions: str = ""
) -> CandidateScore:
    """Score a single candidate asynchronously"""
    result = await (
        LeadScoreCrew()
        .crew()
        .kickoff_async(
            inputs={
                "candidate_id": candidate.id,
                "name": candidate.name,
                "bio": candidate.bio,
                "job_description": job_description,
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
                score_single_candidate_async(candidate, JOB_DESCRIPTION, additional_instructions)
            )
        else:
            score = asyncio.run(
                score_single_candidate_async(candidate, JOB_DESCRIPTION, additional_instructions)
            )
        
        return {
            "success": True,
            "candidate_id": score.id,
            "candidate_name": name,
            "score": score.score,
            "reason": score.reason,
            "job_description": JOB_DESCRIPTION
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
    additional_instructions: str = ""
) -> List[CandidateScore]:
    """Score all candidates asynchronously"""
    tasks = []
    
    for candidate in candidates:
        task = asyncio.create_task(
            score_single_candidate_async(candidate, JOB_DESCRIPTION, additional_instructions)
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
    additional_instructions: str = "",
    generate_emails: bool = True
) -> Dict[str, Any]:
    """
    RunAgent entry point: Run the complete lead scoring flow
    
    Args:
        top_n: Number of top candidates to select (default: 3)
        additional_instructions: Additional scoring criteria
        generate_emails: Whether to generate follow-up emails (default: True)
    
    Returns:
        Dictionary with scored candidates and email generation status
    """
    try:
        # Load candidates
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
                score_all_candidates_async(candidates, additional_instructions)
            )
        else:
            scores = asyncio.run(
                score_all_candidates_async(candidates, additional_instructions)
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


if __name__ == "__main__":
    # Test the RunAgent-compatible entry points
    print("Testing RunAgent-compatible Lead Score Flow")
    print("=" * 50)
    
    # Test 1: Score a single candidate
    print("\n1. Testing single candidate scoring:")
    single_result = score_single_candidate(
        candidate_id="test-1",
        name="Test User",
        email="test@example.com",
        bio="Experienced React developer with 3 years of Next.js experience and AI integration skills.",
        skills="React, Next.js, JavaScript, Vercel AI SDK"
    )
    print(json.dumps(single_result, indent=2))
    
    # Test 2: Run full flow
    print("\n2. Testing full flow:")
    flow_result = run_flow(top_n=3, generate_emails=False)
    print(f"Total candidates: {flow_result.get('total_candidates')}")
    print(f"Success: {flow_result.get('success')}")
    if flow_result.get('success'):
        print(f"Top {len(flow_result.get('top_candidates', []))} candidates:")
        for candidate in flow_result.get('top_candidates', []):
            print(f"  - {candidate['name']}: {candidate['score']}")
    else:
        print(f"Error: {flow_result.get('error')}")