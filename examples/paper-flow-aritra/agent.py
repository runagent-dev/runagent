"""
PaperFlow Agent - RunAgent Serverless Compatible
Monitors arXiv for relevant papers and sends email notifications
Uses OpenAI for LLM filtering
Supports async/parallel processing and streaming
"""
import requests
import feedparser
from datetime import datetime, timezone, timedelta
import time
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Tuple, Set, Optional, AsyncIterator
import asyncio
from openai import OpenAI, AsyncOpenAI


class ArxivAgent:
    """ArXiv paper monitoring agent with OpenAI-based LLM filtering"""
    
    def __init__(
        self,
        topics: List[str],
        max_results: int = 10,
        model: str = "gpt-4o-mini",
        days_back: int = 7,
        verbose: bool =  False,
        cache_dir: str = "paper_cache"
    ):
        self.topics = topics
        self.max_results = max_results
        self.model = model
        self.days_back = days_back
        self.verbose = verbose
        self.cache_dir = cache_dir
        
        # OpenAI configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=self.openai_api_key)
        self.async_client = AsyncOpenAI(api_key=self.openai_api_key)
        
        # Email configuration from environment
        self.user_email = os.getenv("USER_EMAIL", "")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        
        # Cache file path
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache_file = os.path.join(self.cache_dir, "relevant_papers.txt")
        
    def extract_paper_id(self, entry) -> Optional[str]:
        """Extract arXiv paper ID from entry"""
        id_str = getattr(entry, 'id', getattr(entry, 'link', ''))
        match = re.search(r'/(\d{4}\.\d{4,5})', id_str)
        if match:
            return match.group(1)
        match = re.search(r'(\d{4}\.\d{4,5})', id_str)
        if match:
            return match.group(1)
        return None
    
    def load_cached_papers(self) -> Set[str]:
        """Load existing relevant paper IDs from cache"""
        if not os.path.exists(self.cache_file):
            if self.verbose:
                print(f"[DEBUG] Cache file '{self.cache_file}' does not exist, starting with empty cache")
            return set()
        
        paper_ids = set()
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                for line in f:
                    paper_id = line.strip()
                    if paper_id:
                        paper_ids.add(paper_id)
            if self.verbose:
                print(f"[DEBUG] Loaded {len(paper_ids)} paper IDs from cache")
        except Exception as e:
            print(f"[WARN] Failed to load cache: {e}")
        
        return paper_ids
    
    def save_paper_id(self, paper_id: str):
        """Append a paper ID to cache"""
        try:
            with open(self.cache_file, 'a', encoding='utf-8') as f:
                f.write(f"{paper_id}\n")
            if self.verbose:
                print(f"[DEBUG] Saved paper ID '{paper_id}' to cache")
        except Exception as e:
            print(f"[WARN] Failed to save paper ID: {e}")
    
    def query_arxiv(self, keyword: str) -> List:
        """Query arXiv API for papers"""
        if self.verbose:
            print(f"[DEBUG] Querying arXiv for: '{keyword}'")
        
        try:
            url = (
                f"http://export.arxiv.org/api/query?"
                f"search_query=all:{keyword.replace(' ', '+')}"
                f"&start=0&max_results={self.max_results}"
                f"&sortBy=submittedDate&sortOrder=descending"
            )
            
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()  # Raise exception for bad status codes
            feed = feedparser.parse(resp.text)
            
            if self.verbose:
                print(f"[DEBUG] Found {len(feed.entries)} entries")
            
            return feed.entries
        except requests.RequestException as e:
            print(f"[WARN] Failed to query arXiv: {e}")
            if self.verbose:
                print(f"[DEBUG] Network error details: {type(e).__name__}: {str(e)}")
            return []
        except Exception as e:
            print(f"[WARN] Error parsing arXiv feed: {e}")
            if self.verbose:
                print(f"[DEBUG] Parse error details: {type(e).__name__}: {str(e)}")
            return []
    
    def parse_llm_response(self, output: str) -> Tuple[bool, str]:
        """Parse LLM response to determine relevance"""
        if not output:
            return False, "(empty)"
        
        words = output.strip().split()
        if not words:
            return False, "(empty)"
        
        first_word = words[0].strip().upper().rstrip('.,!?:;')
        
        if first_word == "YES":
            return True, first_word
        elif first_word == "NO":
            return False, first_word
        else:
            if self.verbose:
                print(f"[WARN] Unexpected answer: '{first_word}' - treating as NOT RELEVANT")
            return False, first_word
    
    def llm_filter(self, title: str, abstract: str) -> bool:
        """Use OpenAI to filter papers for relevance (synchronous)"""
        if self.verbose:
            print(f"[DEBUG] Filtering paper: '{title[:60]}...'")
        
        # Create topics list for the prompt
        topics_text = "\n".join([f"- {topic}" for topic in self.topics])
        
        prompt = f"""You are filtering academic papers for relevance to specific research topics.

The paper must be DIRECTLY and SUBSTANTIALLY related to one or more of these topics:
{topics_text}

INCLUDE papers that:
- Directly address the topic or subtopics
- Present new methods, techniques, or approaches for the topic
- Provide experimental results, benchmarks, or evaluations for the topic
- Survey or review work related to the topic

EXCLUDE papers that:
- Only mention the topic tangentially or in passing
- Use the topic as a minor tool but focus on something else
- Are about completely different fields

Title: {title}
Abstract: {abstract}

Is this paper DIRECTLY and SUBSTANTIALLY related to the topics listed above?

Respond with ONLY one word: YES or NO. Do not explain."""

        try:
            if self.verbose:
                print(f"[DEBUG] Calling OpenAI with model: {self.model}")
            
            start_time = time.time()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a paper relevance filter. Respond with ONLY 'YES' or 'NO'."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=5,
                temperature=0
            )
            
            elapsed = time.time() - start_time
            output = response.choices[0].message.content.strip()
            
            if self.verbose:
                print(f"[DEBUG] OpenAI response in {elapsed:.2f}s: {output}")
            
            is_relevant, extracted_answer = self.parse_llm_response(output)
            if self.verbose:
                print(f"[DEBUG] Decision: {'RELEVANT' if is_relevant else 'NOT RELEVANT'}")
            
            return is_relevant
        except Exception as e:
            print(f"[WARN] OpenAI filter failed: {e}")
            if self.verbose:
                print(f"[DEBUG] Exception details: {type(e).__name__}: {str(e)}")
            return False
    
    async def llm_filter_async(self, title: str, abstract: str) -> bool:
        """Use OpenAI to filter papers for relevance (async for parallel processing)"""
        if self.verbose:
            print(f"[DEBUG] Filtering paper: '{title[:60]}...'")
        
        # Create topics list for the prompt
        topics_text = "\n".join([f"- {topic}" for topic in self.topics])
        
        prompt = f"""You are filtering academic papers for relevance to specific research topics.

The paper must be DIRECTLY and SUBSTANTIALLY related to one or more of these topics:
{topics_text}

INCLUDE papers that:
- Directly address the topic or subtopics
- Present new methods, techniques, or approaches for the topic
- Provide experimental results, benchmarks, or evaluations for the topic
- Survey or review work related to the topic

EXCLUDE papers that:
- Only mention the topic tangentially or in passing
- Use the topic as a minor tool but focus on something else
- Are about completely different fields

Title: {title}
Abstract: {abstract}

Is this paper DIRECTLY and SUBSTANTIALLY related to the topics listed above?

Respond with ONLY one word: YES or NO. Do not explain."""

        try:
            if self.verbose:
                print(f"[DEBUG] Calling OpenAI (async) with model: {self.model}")
            
            start_time = time.time()
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a paper relevance filter. Respond with ONLY 'YES' or 'NO'."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=5,
                temperature=0
            )
            
            elapsed = time.time() - start_time
            output = response.choices[0].message.content.strip()
            
            if self.verbose:
                print(f"[DEBUG] OpenAI response in {elapsed:.2f}s: {output}")
            
            is_relevant, extracted_answer = self.parse_llm_response(output)
            if self.verbose:
                print(f"[DEBUG] Decision: {'RELEVANT' if is_relevant else 'NOT RELEVANT'}")
            
            return is_relevant
        except Exception as e:
            print(f"[WARN] OpenAI filter failed: {e}")
            if self.verbose:
                print(f"[DEBUG] Exception details: {type(e).__name__}: {str(e)}")
            return False
    
    def format_entry(self, entry) -> str:
        """Format an arXiv entry for display"""
        # Safely get published date
        published_date_str = "Unknown"
        if hasattr(entry, 'published') and entry.published:
            try:
                published_date_str = datetime.strptime(
                    entry.published, "%Y-%m-%dT%H:%M:%SZ"
                ).strftime("%Y-%m-%d")
            except (ValueError, AttributeError):
                published_date_str = getattr(entry, 'published', 'Unknown')
        
        title = getattr(entry, 'title', 'No title').strip()
        link = getattr(entry, 'link', 'No link')
        
        return (
            f"Title: {title}\n"
            f"Date: {published_date_str}\n"
            f"Link: {link}\n"
            f"{'-'*80}\n"
        )
    
    def send_email_notification(self, papers_list: List[Tuple]) -> bool:
        """Send email notification with new relevant papers"""
        if not papers_list:
            return False
        
        if not self.user_email or not self.smtp_username or not self.smtp_password:
            if self.verbose:
                print(f"[WARN] Email configuration incomplete. Skipping notification.")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = self.user_email
            
            paper_count = len(papers_list)
            if paper_count == 1:
                msg['Subject'] = f"New Relevant arXiv Paper: {papers_list[0][0].title.strip()[:60]}"
            else:
                msg['Subject'] = f"New Relevant arXiv Papers: {paper_count} papers"
            
            body = f"""Found {paper_count} new relevant paper{'s' if paper_count > 1 else ''} on arXiv!

"""
            for entry, paper_id in papers_list:
                body += self.format_entry(entry)
            
            msg.attach(MIMEText(body, 'plain'))
            
            if self.verbose:
                print(f"[DEBUG] Sending email to {self.user_email}...")
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.smtp_username, self.user_email, msg.as_string())
            
            if self.verbose:
                print(f"[INFO] Email sent successfully")
            return True
            
        except Exception as e:
            print(f"[WARN] Failed to send email: {e}")
            return False
    
    def run(self) -> Dict:
        """Main execution logic"""
        try:
            if self.verbose:
                print("[DEBUG] Starting arXiv agent...")
            
            cached_paper_ids = self.load_cached_papers()
            
            now = datetime.now(timezone.utc)
            week_ago = now - timedelta(days=self.days_back)
            
            if self.verbose:
                print(f"[DEBUG] Date range: {week_ago.date()} to {now.date()}")
            
            relevant_papers = []
            new_relevant_papers = []
            total_processed = 0
            total_llm_calls = 0
            total_cached_hits = 0
            
            for idx, topic in enumerate(self.topics, 1):
                if self.verbose:
                    print(f"\n[INFO] Processing topic {idx}/{len(self.topics)}: '{topic}'")
                
                entries = self.query_arxiv(topic)
                total_processed += len(entries)
                
                for entry in entries:
                    # Validate entry has required attributes
                    if not hasattr(entry, 'published') or not entry.published:
                        if self.verbose:
                            print(f"[DEBUG] Skipping entry without published date: {getattr(entry, 'title', 'Unknown')[:50]}")
                        continue
                    
                    if not hasattr(entry, 'title') or not entry.title:
                        if self.verbose:
                            print(f"[DEBUG] Skipping entry without title")
                        continue
                    
                    if not hasattr(entry, 'summary') or not entry.summary:
                        if self.verbose:
                            print(f"[DEBUG] Skipping entry without summary: {entry.title[:50]}")
                        continue
                    
                    # Parse published date safely
                    try:
                        published_date = datetime.strptime(
                            entry.published, "%Y-%m-%dT%H:%M:%SZ"
                        ).replace(tzinfo=timezone.utc)
                    except (ValueError, AttributeError) as e:
                        if self.verbose:
                            print(f"[DEBUG] Skipping entry with invalid date format: {entry.published} - {e}")
                        continue
                    
                    # Filter by date range
                    if not (week_ago <= published_date <= now):
                        continue
                    
                    title = entry.title
                    abstract = entry.summary
                    paper_id = self.extract_paper_id(entry)
                    
                    is_relevant = False
                    is_new_paper = False
                    
                    if paper_id and paper_id in cached_paper_ids:
                        is_relevant = True
                        total_cached_hits += 1
                        if self.verbose:
                            print(f"[DEBUG] Paper '{paper_id}' in cache, skipping LLM")
                    else:
                        total_llm_calls += 1
                        is_relevant = self.llm_filter(title, abstract)
                        
                        if is_relevant:
                            # Check if it's a new paper BEFORE adding to cache
                            is_new_paper = not paper_id or paper_id not in cached_paper_ids
                            
                            if paper_id:
                                cached_paper_ids.add(paper_id)
                                self.save_paper_id(paper_id)
                            
                            if is_new_paper:
                                new_relevant_papers.append((entry, paper_id))
                    
                    if is_relevant:
                        relevant_papers.append((published_date.date(), self.format_entry(entry)))
                
                # Rate limiting between topics
                if idx < len(self.topics):
                    time.sleep(3)
            
            # Send email notification for new papers
            email_sent = False
            if new_relevant_papers:
                if self.verbose:
                    print(f"\n[INFO] Sending email for {len(new_relevant_papers)} new papers...")
                email_sent = self.send_email_notification(new_relevant_papers)
            
            result = {
                "status": "success",
                "total_processed": total_processed,
                "total_relevant": len(relevant_papers),
                "new_papers": len(new_relevant_papers),
                "cached_hits": total_cached_hits,
                "llm_calls": total_llm_calls,
                "email_sent": email_sent,
                "papers": [paper[1] for paper in relevant_papers]
            }
            
            if self.verbose:
                print(f"\n[DEBUG] Processing complete:")
                print(f"  - Total processed: {total_processed}")
                print(f"  - Relevant papers: {len(relevant_papers)}")
                print(f"  - New papers: {len(new_relevant_papers)}")
                print(f"  - Email sent: {email_sent}")
            
            return result
            
        except Exception as e:
            error_msg = f"Agent execution failed: {type(e).__name__}: {str(e)}"
            print(f"[ERROR] {error_msg}")
            if self.verbose:
                import traceback
                print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            
            # Always return a dict, even on error
            return {
                "status": "error",
                "error": error_msg,
                "total_processed": 0,
                "total_relevant": 0,
                "new_papers": 0,
                "cached_hits": 0,
                "llm_calls": 0,
                "email_sent": False,
                "papers": []
            }
    
    async def run_async(self) -> Dict:
        """Main execution logic with async/parallel processing"""
        try:
            if self.verbose:
                print("[DEBUG] Starting arXiv agent (async mode)...")
            
            cached_paper_ids = self.load_cached_papers()
            
            now = datetime.now(timezone.utc)
            week_ago = now - timedelta(days=self.days_back)
            
            if self.verbose:
                print(f"[DEBUG] Date range: {week_ago.date()} to {now.date()}")
            
            relevant_papers = []
            new_relevant_papers = []
            total_processed = 0
            total_llm_calls = 0
            total_cached_hits = 0
            
            # Collect all entries from all topics first
            all_entries = []
            for idx, topic in enumerate(self.topics, 1):
                if self.verbose:
                    print(f"\n[INFO] Querying topic {idx}/{len(self.topics)}: '{topic}'")
                
                entries = self.query_arxiv(topic)
                all_entries.extend([(entry, topic) for entry in entries])
                total_processed += len(entries)
            
            # Filter entries by date and validate
            valid_entries = []
            for entry, topic in all_entries:
                if not hasattr(entry, 'published') or not entry.published:
                    continue
                if not hasattr(entry, 'title') or not entry.title:
                    continue
                if not hasattr(entry, 'summary') or not entry.summary:
                    continue
                
                try:
                    published_date = datetime.strptime(
                        entry.published, "%Y-%m-%dT%H:%M:%SZ"
                    ).replace(tzinfo=timezone.utc)
                except (ValueError, AttributeError):
                    continue
                
                if week_ago <= published_date <= now:
                    valid_entries.append((entry, topic, published_date))
            
            if self.verbose:
                print(f"\n[INFO] Processing {len(valid_entries)} valid entries in parallel...")
            
            # Process all entries in parallel with semaphore to limit concurrency
            semaphore = asyncio.Semaphore(10)  # Max 10 concurrent LLM calls
            
            async def process_entry(entry, topic, published_date):
                nonlocal total_llm_calls, total_cached_hits
                
                title = entry.title
                abstract = entry.summary
                paper_id = self.extract_paper_id(entry)
                
                is_relevant = False
                is_new_paper = False
                
                if paper_id and paper_id in cached_paper_ids:
                    is_relevant = True
                    total_cached_hits += 1
                    if self.verbose:
                        print(f"[DEBUG] Paper '{paper_id}' in cache, skipping LLM")
                else:
                    async with semaphore:
                        total_llm_calls += 1
                        is_relevant = await self.llm_filter_async(title, abstract)
                    
                    if is_relevant:
                        # Check if it's a new paper BEFORE adding to cache
                        is_new_paper = not paper_id or paper_id not in cached_paper_ids
                        
                        if paper_id:
                            cached_paper_ids.add(paper_id)
                            self.save_paper_id(paper_id)
                        
                        if is_new_paper:
                            new_relevant_papers.append((entry, paper_id))
                
                if is_relevant:
                    return (published_date.date(), self.format_entry(entry))
                return None
            
            # Run all processing tasks in parallel
            tasks = [process_entry(entry, topic, pub_date) for entry, topic, pub_date in valid_entries]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect valid results
            for result in results:
                if result and not isinstance(result, Exception):
                    relevant_papers.append(result)
            
            # Send email notification for new papers
            email_sent = False
            if new_relevant_papers:
                if self.verbose:
                    print(f"\n[INFO] Sending email for {len(new_relevant_papers)} new papers...")
                email_sent = self.send_email_notification(new_relevant_papers)
            
            result = {
                "status": "success",
                "total_processed": total_processed,
                "total_relevant": len(relevant_papers),
                "new_papers": len(new_relevant_papers),
                "cached_hits": total_cached_hits,
                "llm_calls": total_llm_calls,
                "email_sent": email_sent,
                "papers": [paper for _, paper in sorted(relevant_papers, reverse=True)]
            }
            
            if self.verbose:
                print(f"\n[INFO] Completed: {result['total_relevant']} relevant papers found")
            
            return result
        except Exception as e:
            error_msg = f"Agent execution failed: {type(e).__name__}: {str(e)}"
            print(f"[ERROR] {error_msg}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return {
                "status": "error",
                "error": error_msg,
                "total_processed": 0,
                "total_relevant": 0,
                "new_papers": 0,
                "cached_hits": 0,
                "llm_calls": 0,
                "email_sent": False,
                "papers": []
            }
    
    async def run_stream(self) -> AsyncIterator[Dict]:
        """Streaming version that yields progress updates in real-time"""
        try:
            yield {"type": "status", "message": "Starting arXiv agent (streaming mode)...", "progress": 0}
            
            cached_paper_ids = self.load_cached_papers()
            
            now = datetime.now(timezone.utc)
            week_ago = now - timedelta(days=self.days_back)
            
            yield {"type": "status", "message": f"Date range: {week_ago.date()} to {now.date()}", "progress": 5}
            
            relevant_papers = []
            new_relevant_papers = []
            total_processed = 0
            total_llm_calls = 0
            total_cached_hits = 0
            
            # Collect all entries from all topics
            all_entries = []
            for idx, topic in enumerate(self.topics, 1):
                yield {
                    "type": "status",
                    "message": f"Querying topic {idx}/{len(self.topics)}: '{topic}'",
                    "progress": 10 + (idx * 10 // len(self.topics))
                }
                
                entries = self.query_arxiv(topic)
                all_entries.extend([(entry, topic) for entry in entries])
                total_processed += len(entries)
                
                yield {
                    "type": "status",
                    "message": f"Found {len(entries)} papers for '{topic}'",
                    "progress": 10 + (idx * 10 // len(self.topics))
                }
            
            # Filter entries by date and validate
            valid_entries = []
            for entry, topic in all_entries:
                if not hasattr(entry, 'published') or not entry.published:
                    continue
                if not hasattr(entry, 'title') or not entry.title:
                    continue
                if not hasattr(entry, 'summary') or not entry.summary:
                    continue
                
                try:
                    published_date = datetime.strptime(
                        entry.published, "%Y-%m-%dT%H:%M:%SZ"
                    ).replace(tzinfo=timezone.utc)
                except (ValueError, AttributeError):
                    continue
                
                if week_ago <= published_date <= now:
                    valid_entries.append((entry, topic, published_date))
            
            yield {
                "type": "status",
                "message": f"Processing {len(valid_entries)} valid entries in parallel...",
                "progress": 30
            }
            
            # Process entries in parallel with progress updates
            semaphore = asyncio.Semaphore(10)
            processed_count = 0
            lock = asyncio.Lock()
            
            async def process_entry(entry, topic, published_date):
                nonlocal total_llm_calls, total_cached_hits, processed_count
                
                title = entry.title
                abstract = entry.summary
                paper_id = self.extract_paper_id(entry)
                
                is_relevant = False
                is_new_paper = False
                
                if paper_id and paper_id in cached_paper_ids:
                    is_relevant = True
                    async with lock:
                        total_cached_hits += 1
                else:
                    async with semaphore:
                        async with lock:
                            total_llm_calls += 1
                        is_relevant = await self.llm_filter_async(title, abstract)
                    
                    if is_relevant:
                        # Check if it's a new paper BEFORE adding to cache
                        is_new_paper = not paper_id or paper_id not in cached_paper_ids
                        
                        if paper_id:
                            cached_paper_ids.add(paper_id)
                            self.save_paper_id(paper_id)
                        
                        if is_new_paper:
                            new_relevant_papers.append((entry, paper_id))
                
                async with lock:
                    processed_count += 1
                    current_progress = processed_count
                
                if is_relevant:
                    paper_info = self.format_entry(entry)
                    return {
                        "type": "paper",
                        "paper": paper_info,
                        "is_new": paper_id not in cached_paper_ids if paper_id else True,
                        "progress": 30 + int((current_progress / len(valid_entries)) * 60)
                    }, (published_date.date(), paper_info)
                
                return {
                    "type": "progress",
                    "message": f"Processed {current_progress}/{len(valid_entries)} papers",
                    "progress": 30 + int((current_progress / len(valid_entries)) * 60)
                }, None
            
            # Process in batches to yield progress
            batch_size = 20
            for i in range(0, len(valid_entries), batch_size):
                batch = valid_entries[i:i+batch_size]
                tasks = [process_entry(entry, topic, pub_date) for entry, topic, pub_date in batch]
                
                for coro in asyncio.as_completed(tasks):
                    try:
                        update, result = await coro
                        yield update
                        if result:
                            relevant_papers.append(result)
                    except Exception as e:
                        if self.verbose:
                            print(f"[WARN] Error processing entry: {e}")
                        yield {
                            "type": "progress",
                            "message": f"Error processing entry: {str(e)}",
                            "progress": 30 + int((processed_count / len(valid_entries)) * 60)
                        }
            
            yield {
                "type": "status",
                "message": f"Found {len(relevant_papers)} relevant papers",
                "progress": 90
            }
            
            # Send email notification
            email_sent = False
            if new_relevant_papers:
                yield {
                    "type": "status",
                    "message": f"Sending email for {len(new_relevant_papers)} new papers...",
                    "progress": 95
                }
                email_sent = self.send_email_notification(new_relevant_papers)
            
            # Final result
            yield {
                "type": "complete",
                "status": "success",
                "total_processed": total_processed,
                "total_relevant": len(relevant_papers),
                "new_papers": len(new_relevant_papers),
                "cached_hits": total_cached_hits,
                "llm_calls": total_llm_calls,
                "email_sent": email_sent,
                "papers": [paper for _, paper in sorted(relevant_papers, reverse=True)],
                "progress": 100
            }
        except Exception as e:
            error_msg = f"Agent execution failed: {type(e).__name__}: {str(e)}"
            print(f"[ERROR] {error_msg}")
            yield {
                "type": "error",
                "error": error_msg,
                "status": "error",
                "total_processed": 0,
                "total_relevant": 0,
                "new_papers": 0,
                "cached_hits": 0,
                "llm_calls": 0,
                "email_sent": False,
                "papers": [],
                "progress": 0
            }


# ============================================================
# RunAgent Entrypoints
# ============================================================

def check_papers(
    topics: List[str] = None,
    max_results: int = 10,
    days_back: int = 7,
    verbose: bool = True,
    **kwargs
) -> Dict:
    """
    Main entrypoint for checking arXiv papers
    
    Args:
        topics: List of topics to search for (optional, uses defaults if not provided)
        max_results: Maximum results per topic
        days_back: How many days back to search
        verbose: Enable verbose logging
    
    Returns:
        Dictionary with results including papers found and email status
    """
    try:
        # Default topics if not provided
        if topics is None:
            topics = [
                "unstructured data analysis",
                "querying unstructured data",
                "semi structured data",
                "text to table",
                "text to relational schema",
            ]
        
        agent = ArxivAgent(
            topics=topics,
            max_results=max_results,
            days_back=days_back,
            verbose=verbose,
            cache_dir="paper_cache"  # Will be in persistent folder
        )
        
        return agent.run()
    except Exception as e:
        error_msg = f"Entrypoint execution failed: {type(e).__name__}: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return {
            "status": "error",
            "error": error_msg,
            "total_processed": 0,
            "total_relevant": 0,
            "new_papers": 0,
            "cached_hits": 0,
            "llm_calls": 0,
            "email_sent": False,
            "papers": []
        }


def check_papers_custom_topics(
    topic1: str = "",
    topic2: str = "",
    topic3: str = "",
    topic4: str = "",
    topic5: str = "",
    max_results: int = 10,
    days_back: int = 7,
    **kwargs
) -> Dict:
    """
    Entrypoint for checking papers with custom topics (easier for SDK calls)
    
    Args:
        topic1-5: Individual topic strings (easier than passing lists via SDK)
        max_results: Maximum results per topic
        days_back: How many days back to search
    
    Returns:
        Dictionary with results
    """
    try:
        topics = [t for t in [topic1, topic2, topic3, topic4, topic5] if t]
        
        if not topics:
            topics = ["unstructured data analysis"]
        
        agent = ArxivAgent(
            topics=topics,
            max_results=max_results,
            days_back=days_back,
            verbose=True,
            cache_dir="paper_cache"
        )
        
        return agent.run()
    except Exception as e:
        error_msg = f"Entrypoint execution failed: {type(e).__name__}: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return {
            "status": "error",
            "error": error_msg,
            "total_processed": 0,
            "total_relevant": 0,
            "new_papers": 0,
            "cached_hits": 0,
            "llm_calls": 0,
            "email_sent": False,
            "papers": []
        }

async def check_papers_async(
    topics: List[str] = None,
    max_results: int = 10,
    days_back: int = 7,
    verbose: bool = True,
    **kwargs
) -> Dict:
    """
    Async entrypoint for checking arXiv papers with parallel processing
    
    Args:
        topics: List of topics to search for (optional, uses defaults if not provided)
        max_results: Maximum results per topic
        days_back: How many days back to search
        verbose: Enable verbose logging
    
    Returns:
        Dictionary with results including papers found and email status
    """
    try:
        # Default topics if not provided
        if topics is None:
            topics = [
                "unstructured data analysis",
                "querying unstructured data",
                "semi structured data",
                "text to table",
                "text to relational schema",
            ]
        
        agent = ArxivAgent(
            topics=topics,
            max_results=max_results,
            days_back=days_back,
            verbose=verbose,
            cache_dir="paper_cache"
        )
        
        return await agent.run_async()
    except Exception as e:
        error_msg = f"Entrypoint execution failed: {type(e).__name__}: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return {
            "status": "error",
            "error": error_msg,
            "total_processed": 0,
            "total_relevant": 0,
            "new_papers": 0,
            "cached_hits": 0,
            "llm_calls": 0,
            "email_sent": False,
            "papers": []
        }


async def check_papers_stream(
    topics: List[str] = None,
    max_results: int = 10,
    days_back: int = 7,
    verbose: bool = True,
    **kwargs
) -> AsyncIterator[Dict]:
    """
    Streaming entrypoint for checking arXiv papers with real-time progress updates
    
    Args:
        topics: List of topics to search for (optional, uses defaults if not provided)
        max_results: Maximum results per topic
        days_back: How many days back to search
        verbose: Enable verbose logging
    
    Yields:
        Dictionary updates with type: "status", "paper", "progress", "complete", or "error"
    """
    try:
        # Default topics if not provided
        if topics is None:
            topics = [
                "unstructured data analysis",
                "querying unstructured data",
                "semi structured data",
                "text to table",
                "text to relational schema",
            ]
        
        agent = ArxivAgent(
            topics=topics,
            max_results=max_results,
            days_back=days_back,
            verbose=verbose,
            cache_dir="paper_cache"
        )
        
        async for update in agent.run_stream():
            yield update
    except Exception as e:
        error_msg = f"Entrypoint execution failed: {type(e).__name__}: {str(e)}"
        print(f"[ERROR] {error_msg}")
        yield {
            "type": "error",
            "error": error_msg,
            "status": "error",
            "total_processed": 0,
            "total_relevant": 0,
            "new_papers": 0,
            "cached_hits": 0,
            "llm_calls": 0,
            "email_sent": False,
            "papers": [],
            "progress": 0
        }
