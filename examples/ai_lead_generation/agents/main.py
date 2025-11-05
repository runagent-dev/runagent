#!/usr/bin/env python
"""
RunAgent-compatible entry points for AI Lead Generation Agent
"""
import os
import requests
from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import json
import csv
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()


class QuoraUserInteractionSchema(BaseModel):
    username: str = Field(description="The username of the user who posted the question or answer")
    bio: str = Field(description="The bio or description of the user")
    post_type: str = Field(description="The type of post, either 'question' or 'answer'")
    timestamp: str = Field(description="When the question or answer was posted")
    upvotes: int = Field(default=0, description="Number of upvotes received")
    links: List[str] = Field(default_factory=list, description="Any links included in the post")


class QuoraPageSchema(BaseModel):
    interactions: List[QuoraUserInteractionSchema] = Field(
        description="List of all user interactions (questions and answers) on the page"
    )


def search_quora_urls(query: str, firecrawl_api_key: str, num_links: int = 3) -> List[str]:
    """Search for relevant Quora URLs based on query"""
    url = "https://api.firecrawl.dev/v1/search"
    headers = {
        "Authorization": f"Bearer {firecrawl_api_key}",
        "Content-Type": "application/json"
    }
    
    search_query = f"quora websites where people are looking for {query} services"
    print(f"  🔍 Search query: {search_query}")
    
    payload = {
        "query": search_query,
        "limit": num_links,
        "lang": "en",
        "location": "United States",
        "timeout": 60000,
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"  📡 Search API status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  📡 Search success: {data.get('success')}")
            
            if data.get("success"):
                results = data.get("data", [])
                urls = [result["url"] for result in results]
                print(f"  ✅ Found {len(urls)} URLs:")
                for i, found_url in enumerate(urls, 1):
                    print(f"     {i}. {found_url}")
                return urls
        else:
            print(f"  ❌ Search API error: {response.text}")
            
    except Exception as e:
        print(f"  ❌ Error searching URLs: {e}")
    
    return []


def extract_leads_with_openai(url: str, page_content: str, openai_api_key: str) -> List[dict]:
    """Use OpenAI to intelligently extract lead information from page content"""
    try:
        client = OpenAI(api_key=openai_api_key)
        
        prompt = f"""Analyze this Quora page content and extract information about users who are asking questions or providing answers related to the topic.

Page URL: {url}

Page Content:
{page_content[:8000]}  # Limit content to avoid token limits

Extract the following information for each user you find:
1. Username (if visible)
2. Bio/Description (if available)
3. Whether they asked a question or provided an answer
4. Timestamp (if available)
5. Number of upvotes (if visible)
6. Any relevant links they shared

Return a JSON array of users. If you can't find specific information, use reasonable defaults like "Unknown" or "Not specified".

Example format:
[
  {{
    "username": "John Doe",
    "bio": "Software Engineer at Tech Corp",
    "post_type": "question",
    "timestamp": "2 days ago",
    "upvotes": 15,
    "links": []
  }}
]

If no users are clearly identifiable, return at least one entry with the page URL and basic information."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a lead generation expert who extracts user information from web pages."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Handle different possible response structures
        if isinstance(result, dict) and 'users' in result:
            return result['users']
        elif isinstance(result, list):
            return result
        elif isinstance(result, dict):
            # If it's a dict but not with 'users' key, wrap it
            return [result]
        else:
            return []
            
    except Exception as e:
        print(f"  ⚠️  OpenAI extraction failed: {str(e)}")
        return []


def extract_leads_from_urls(urls: List[str], firecrawl_api_key: str, openai_api_key: str = None) -> List[dict]:
    """Extract user information from Quora URLs using Firecrawl + OpenAI"""
    user_info_list = []
    firecrawl_app = FirecrawlApp(api_key=firecrawl_api_key)
    use_openai = openai_api_key is not None
    
    for url in urls:
        try:
            print(f"  📊 Extracting from: {url}")
            
            # First, try to scrape the page content
            scrape_response = firecrawl_app.scrape_url(
                url=url,
                params={'formats': ['markdown', 'html']}
            )
            
            if not scrape_response.get('success'):
                print(f"  ❌ Failed to scrape {url}")
                # Create basic fallback
                user_info_list.append({
                    "website_url": url,
                    "user_info": [{
                        'username': 'Quora User',
                        'bio': 'Lead from Quora - Manual review needed',
                        'post_type': 'discussion',
                        'timestamp': 'Recent',
                        'upvotes': 0,
                        'links': [url]
                    }]
                })
                continue
            
            page_content = scrape_response.get('markdown', '') or scrape_response.get('html', '')
            
            if not page_content:
                print(f"  ⚠️  No content extracted from {url}")
                continue
            
            print(f"  ✅ Scraped {len(page_content)} characters")
            
            # Use OpenAI to intelligently extract user information
            if use_openai:
                print(f"  🤖 Using OpenAI to extract lead information...")
                interactions = extract_leads_with_openai(url, page_content, openai_api_key)
                
                if interactions and len(interactions) > 0:
                    print(f"  ✅ OpenAI extracted {len(interactions)} leads")
                    user_info_list.append({
                        "website_url": url,
                        "user_info": interactions
                    })
                else:
                    print(f"  ⚠️  OpenAI found no leads, creating basic entry")
                    user_info_list.append({
                        "website_url": url,
                        "user_info": [{
                            'username': 'Quora User',
                            'bio': 'Active in discussion',
                            'post_type': 'discussion',
                            'timestamp': 'Recent',
                            'upvotes': 0,
                            'links': [url]
                        }]
                    })
            else:
                # Without OpenAI, create basic entry from URL
                print(f"  ℹ️  No OpenAI key provided, creating basic entry")
                user_info_list.append({
                    "website_url": url,
                    "user_info": [{
                        'username': 'Quora User',
                        'bio': 'Lead from Quora discussion',
                        'post_type': 'discussion',
                        'timestamp': 'Recent',
                        'upvotes': 0,
                        'links': [url]
                    }]
                })
                    
        except Exception as e:
            print(f"  ❌ Error processing {url}: {str(e)}")
            # Always create a fallback entry
            user_info_list.append({
                "website_url": url,
                "user_info": [{
                    'username': 'Quora User',
                    'bio': 'Lead from Quora - Manual review needed',
                    'post_type': 'discussion',
                    'timestamp': 'Recent',
                    'upvotes': 0,
                    'links': [url]
                }]
            })
            continue
    
    print(f"\n📊 Total URLs processed: {len(urls)}")
    print(f"📊 URLs with data extracted: {len(user_info_list)}")
    
    return user_info_list


def format_leads_data(user_info_list: List[dict]) -> List[dict]:
    """Format extracted data into flattened structure"""
    flattened_data = []
    
    print(f"\n🔧 Formatting {len(user_info_list)} URL data entries...")
    
    for info in user_info_list:
        website_url = info["website_url"]
        user_info = info["user_info"]
        
        print(f"  📄 Processing {website_url}: {len(user_info)} interactions")
        
        for interaction in user_info:
            # Handle both dict and object types
            if isinstance(interaction, dict):
                username = interaction.get("username", "Unknown")
                bio = interaction.get("bio", "")
                post_type = interaction.get("post_type", "")
                timestamp = interaction.get("timestamp", "")
                upvotes = interaction.get("upvotes", 0)
                links = interaction.get("links", [])
            else:
                # Handle Pydantic model objects
                username = getattr(interaction, "username", "Unknown")
                bio = getattr(interaction, "bio", "")
                post_type = getattr(interaction, "post_type", "")
                timestamp = getattr(interaction, "timestamp", "")
                upvotes = getattr(interaction, "upvotes", 0)
                links = getattr(interaction, "links", [])
            
            flattened_interaction = {
                "Website URL": website_url,
                "Username": username,
                "Bio": bio,
                "Post Type": post_type,
                "Timestamp": timestamp,
                "Upvotes": upvotes,
                "Links": ", ".join(links) if isinstance(links, list) else str(links),
            }
            flattened_data.append(flattened_interaction)
    
    print(f"  ✅ Formatted {len(flattened_data)} total lead entries\n")
    return flattened_data


def save_to_csv(data: List[dict], filename: str = None) -> str:
    """Save lead data to CSV file"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"leads_{timestamp}.csv"
    
    try:
        # Ensure we have data
        if not data:
            return None
            
        # Write to CSV
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ["Website URL", "Username", "Bio", "Post Type", "Timestamp", "Upvotes", "Links"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        
        return filename
        
    except Exception as e:
        print(f"Error saving to CSV: {e}")
        return None


def generate_leads(
    search_query: str = "AI customer support chatbots",
    num_links: int = 3,
    firecrawl_api_key: str = None,
    openai_api_key: str = None
) -> Dict[str, Any]:
    """
    RunAgent entry point: Generate leads from Quora and save to CSV
    
    Args:
        search_query: What kind of leads to search for
        num_links: Number of Quora URLs to process (1-10)
        firecrawl_api_key: Firecrawl API key (defaults to env var)
        openai_api_key: OpenAI API key for intelligent extraction (optional, defaults to env var)
    
    Returns:
        Dictionary with lead generation results and CSV filename
    """
    # Load from environment variables if not provided
    firecrawl_api_key = firecrawl_api_key or os.getenv("FIRECRAWL_API_KEY")
    openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    
    if not firecrawl_api_key:
        return {
            "success": False,
            "error": "Missing FIRECRAWL_API_KEY. Please set it in .env file or pass as parameter."
        }
    
    if openai_api_key:
        print("🤖 OpenAI integration enabled for intelligent extraction")
    else:
        print("ℹ️  OpenAI key not provided - using basic extraction")
    
    try:
        print(f"🎯 Searching for leads: {search_query}")
        
        # Step 1: Search for relevant Quora URLs
        print(f"🔍 Searching for {num_links} relevant Quora URLs...")
        urls = search_quora_urls(search_query, firecrawl_api_key, num_links)
        
        if not urls:
            return {
                "success": False,
                "error": "No relevant URLs found"
            }
        
        print(f"✅ Found {len(urls)} URLs")
        
        # Step 2: Extract lead information
        print("📊 Extracting lead information from URLs...")
        user_info_list = extract_leads_from_urls(urls, firecrawl_api_key, openai_api_key)
        
        if not user_info_list:
            return {
                "success": False,
                "error": "No leads extracted from URLs"
            }
        
        # Step 3: Format the data
        print("🔧 Formatting lead data...")
        formatted_data = format_leads_data(user_info_list)
        
        print(f"✅ Extracted {len(formatted_data)} leads")
        
        # Step 4: Save to CSV
        print("📝 Saving to CSV file...")
        csv_filename = save_to_csv(formatted_data)
        
        if not csv_filename:
            return {
                "success": False,
                "error": "Failed to create CSV file",
                "leads_count": len(formatted_data),
                "leads_data": formatted_data
            }
        
        print(f"🎉 Success! CSV file created: {csv_filename}")
        
        return {
            "success": True,
            "search_query": search_query,
            "urls_processed": len(urls),
            "leads_count": len(formatted_data),
            "csv_filename": csv_filename,
            "csv_path": os.path.abspath(csv_filename),
            "openai_used": openai_api_key is not None,
            "leads_data": formatted_data
        }
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


if __name__ == "__main__":
    # Test the function
    result = generate_leads(
        search_query="AI video editing software",
        num_links=2
    )
    print(json.dumps(result, indent=2))