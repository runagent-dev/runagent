
#!/usr/bin/env python
"""
RunAgent-compatible entry points for Book Writer Flow
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
if src_dir.exists():
    sys.path.insert(0, str(src_dir))

# Safe print function to avoid rich FileProxy issues in VM environments
def safe_print(*args, **kwargs):
    """Print function that safely handles rich FileProxy issues"""
    try:
        # Try to use the original stdout if available
        if hasattr(sys, '__stdout__') and sys.__stdout__ is not None:
            print(*args, **kwargs, file=sys.__stdout__)
        else:
            # Direct write to stdout file descriptor to bypass rich
            import os
            message = ' '.join(str(arg) for arg in args) + '\n'
            os.write(1, message.encode('utf-8'))
    except (AttributeError, OSError, TypeError):
        # Final fallback: write to stderr
        try:
            import os
            message = ' '.join(str(arg) for arg in args) + '\n'
            os.write(2, message.encode('utf-8'))
        except:
            pass  # Silently fail if all else fails

# Lazy imports - will be loaded when functions are called
def get_outline_crew():
    from write_a_book_with_flows.crews.outline_book_crew.outline_crew import OutlineCrew
    return OutlineCrew

def get_write_chapter_crew():
    from write_a_book_with_flows.crews.write_book_chapter_crew.write_book_chapter_crew import WriteBookChapterCrew
    return WriteBookChapterCrew

def get_chapter_types():
    from write_a_book_with_flows.types import Chapter, ChapterOutline
    return Chapter, ChapterOutline


def generate_outline(
    title: str = "AI in 2025",
    topic: str = "The current state of AI",
    goal: str = "Provide comprehensive overview of AI trends"
) -> Dict[str, Any]:
    """
    RunAgent entry point: Generate book outline
    
    Args:
        title: Book title
        topic: Main topic of the book
        goal: Overall goal/purpose of the book
    
    Returns:
        Dictionary with book outline including chapters
    """
    try:
        safe_print(f"📚 Generating outline for: {title}")
        safe_print(f"Topic: {topic}")
        
        # Import crew class
        OutlineCrew = get_outline_crew()
        
        # Generate outline using CrewAI
        output = (
            OutlineCrew()
            .crew()
            .kickoff(inputs={"topic": topic, "goal": goal})
        )
        
        chapters = output["chapters"]
        
        # Format chapters for response
        formatted_chapters = []
        for idx, chapter in enumerate(chapters, 1):
            formatted_chapters.append({
                "number": idx,
                "title": chapter.title,
                "description": chapter.description
            })
        
        return {
            "success": True,
            "title": title,
            "topic": topic,
            "goal": goal,
            "chapters": formatted_chapters,
            "total_chapters": len(formatted_chapters)
        }
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


async def write_chapter_async(
    title: str,
    topic: str,
    goal: str,
    chapter_title: str,
    chapter_description: str,
    book_outline: List[Dict]
):
    """Write a single chapter asynchronously"""
    # Import crew and types
    WriteBookChapterCrew = get_write_chapter_crew()
    Chapter, _ = get_chapter_types()
    
    output = (
        WriteBookChapterCrew()
        .crew()
        .kickoff(
            inputs={
                "goal": goal,
                "topic": topic,
                "chapter_title": chapter_title,
                "chapter_description": chapter_description,
                "book_outline": book_outline,
            }
        )
    )
    
    return Chapter(
        title=output["title"],
        content=output["content"]
    )


def write_chapter(
    title: str = "AI in 2025",
    topic: str = "The current state of AI",
    goal: str = "Provide comprehensive overview",
    chapter_title: str = "Introduction",
    chapter_description: str = "Overview of AI landscape"
) -> Dict[str, Any]:
    """
    RunAgent entry point: Write a single book chapter
    
    Args:
        title: Book title
        topic: Main topic
        goal: Book goal
        chapter_title: Title of the chapter to write
        chapter_description: Description/outline of the chapter
    
    Returns:
        Dictionary with chapter content
    """
    try:
        safe_print(f"✍️ Writing chapter: {chapter_title}")
        
        # Run async chapter writing
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
            chapter = loop.run_until_complete(
                write_chapter_async(
                    title, topic, goal, chapter_title, chapter_description, []
                )
            )
        else:
            chapter = asyncio.run(
                write_chapter_async(
                    title, topic, goal, chapter_title, chapter_description, []
                )
            )
        
        return {
            "success": True,
            "chapter_title": chapter.title,
            "chapter_content": chapter.content,
            "word_count": len(chapter.content.split())
        }
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def write_full_book(
    title: str = "AI in 2025",
    topic: str = "The current state of AI",
    goal: str = "Provide comprehensive overview of AI trends",
    num_chapters: int = 5
) -> Dict[str, Any]:
    """
    RunAgent entry point: Write complete book with outline and all chapters
    
    Args:
        title: Book title
        topic: Main topic of the book
        goal: Overall goal/purpose of the book
        num_chapters: Number of chapters to generate (default: 5)
    
    Returns:
        Dictionary with complete book including all chapters
    """
    try:
        safe_print(f"📖 Writing complete book: {title}")
        safe_print(f"Topic: {topic}")
        safe_print(f"Target chapters: {num_chapters}")
        
        # Step 1: Generate outline
        safe_print("\n📋 Step 1: Generating outline...")
        outline_result = generate_outline(title, topic, goal)
        
        if not outline_result.get("success"):
            return outline_result
        
        chapters_outline = outline_result["chapters"][:num_chapters]
        
        # Step 2: Write all chapters
        safe_print(f"\n✍️ Step 2: Writing {len(chapters_outline)} chapters...")
        
        async def write_all_chapters():
            tasks = []
            
            for chapter_outline in chapters_outline:
                safe_print(f"  - Scheduling: {chapter_outline['title']}")
                task = asyncio.create_task(
                    write_chapter_async(
                        title=title,
                        topic=topic,
                        goal=goal,
                        chapter_title=chapter_outline["title"],
                        chapter_description=chapter_outline["description"],
                        book_outline=[ch["title"] for ch in chapters_outline]
                    )
                )
                tasks.append(task)
            
            return await asyncio.gather(*tasks)
        
        # Run async chapter writing
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
            chapters = loop.run_until_complete(write_all_chapters())
        else:
            chapters = asyncio.run(write_all_chapters())
        
        # Step 3: Combine into full book
        safe_print("\n📚 Step 3: Combining chapters into book...")
        
        book_content = f"# {title}\n\n"
        book_content += f"## About This Book\n\n"
        book_content += f"**Topic:** {topic}\n\n"
        book_content += f"**Goal:** {goal}\n\n"
        book_content += f"---\n\n"
        
        formatted_chapters = []
        for idx, chapter in enumerate(chapters, 1):
            book_content += f"# Chapter {idx}: {chapter.title}\n\n"
            book_content += f"{chapter.content}\n\n"
            book_content += f"---\n\n"
            
            formatted_chapters.append({
                "number": idx,
                "title": chapter.title,
                "content": chapter.content,
                "word_count": len(chapter.content.split())
            })
        
        total_words = sum(ch["word_count"] for ch in formatted_chapters)
        
        return {
            "success": True,
            "title": title,
            "topic": topic,
            "goal": goal,
            "book_content": book_content,
            "chapters": formatted_chapters,
            "total_chapters": len(formatted_chapters),
            "total_words": total_words,
            "outline": outline_result["chapters"]
        }
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


if __name__ == "__main__":
    # Test the functions
    safe_print("Testing Book Writer Flow...\n")
    
    # Test outline generation
    result = generate_outline(
        title="Introduction to Python",
        topic="Python programming for beginners",
        goal="Teach fundamental Python concepts"
    )
    safe_print(result)