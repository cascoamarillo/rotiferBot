#!/usr/bin/env python3
"""
Rotifer Literature Bot for Bluesky
Searches PubMed for recent rotifer papers and posts them to Bluesky
"""

import os
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class BlueskyBot:
    def __init__(self, handle: str, password: str):
        self.handle = handle
        self.session = None
        self.base_url = "https://bsky.social/xrpc"
        self.authenticate(password)
    
    def authenticate(self, password: str):
        """Authenticate with Bluesky and get access token"""
        response = requests.post(
            f"{self.base_url}/com.atproto.server.createSession",
            json={"identifier": self.handle, "password": password}
        )
        
        if response.status_code != 200:
            raise Exception(f"Authentication failed: {response.text}")
        
        self.session = response.json()
        print(f"✅ Authenticated as {self.handle}")
    
    def create_post(self, text: str) -> bool:
        """Create a post on Bluesky with proper hashtag and link formatting"""
        if not self.session:
            raise Exception("Not authenticated")
        
        # Ensure post is under character limit
        if len(text) > 300:
            text = text[:297] + "..."
        
        record = {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": datetime.now().isoformat() + "Z",
            "langs": ["en"]
        }
        
        # Add facets for hashtags and links
        facets = []
        text_bytes = text.encode('utf-8')
        
        # Find hashtags
        hashtag_text = "#Rotifersky"
        hashtag_start = text.find(hashtag_text)
        if hashtag_start >= 0:
            # Convert to byte positions
            byte_start = len(text[:hashtag_start].encode('utf-8'))
            byte_end = len(text[:hashtag_start + len(hashtag_text)].encode('utf-8'))
            
            facets.append({
                "index": {
                    "byteStart": byte_start,
                    "byteEnd": byte_end
                },
                "features": [{
                    "$type": "app.bsky.richtext.facet#tag",
                    "tag": "Rotifersky"
                }]
            })
        
        # Find DOI links
        doi_pattern = "https://doi.org/"
        doi_start = text.find(doi_pattern)
        if doi_start >= 0:
            # Find end of URL (look for end of text or newline)
            doi_end = len(text)
            for i in range(doi_start, len(text)):
                if text[i] in ['\n', '\r', ' ']:
                    doi_end = i
                    break
            
            # Convert to byte positions
            byte_start = len(text[:doi_start].encode('utf-8'))
            byte_end = len(text[:doi_end].encode('utf-8'))
            
            facets.append({
                "index": {
                    "byteStart": byte_start,
                    "byteEnd": byte_end
                },
                "features": [{
                    "$type": "app.bsky.richtext.facet#link",
                    "uri": text[doi_start:doi_end]
                }]
            })
        
        # Find PubMed links as fallback (only if no DOI)
        elif text.find("https://pubmed.ncbi.nlm.nih.gov/") >= 0:
            pubmed_pattern = "https://pubmed.ncbi.nlm.nih.gov/"
            pubmed_start = text.find(pubmed_pattern)
            pubmed_end = len(text)
            for i in range(pubmed_start, len(text)):
                if text[i] in ['\n', '\r', ' ']:
                    pubmed_end = i
                    break
            
            # Convert to byte positions
            byte_start = len(text[:pubmed_start].encode('utf-8'))
            byte_end = len(text[:pubmed_end].encode('utf-8'))
                    
            facets.append({
                "index": {
                    "byteStart": byte_start,
                    "byteEnd": byte_end
                },
                "features": [{
                    "$type": "app.bsky.richtext.facet#link", 
                    "uri": text[pubmed_start:pubmed_end]
                }]
            })
        
        if facets:
            record["facets"] = facets
        
        response = requests.post(
            f"{self.base_url}/com.atproto.repo.createRecord",
            headers={
                "Authorization": f"Bearer {self.session['accessJwt']}",
                "Content-Type": "application/json"
            },
            json={
                "repo": self.session["did"],
                "collection": "app.bsky.feed.post",
                "record": record
            }
        )
        
        if response.status_code == 200:
            print(f"✅ Posted: {text[:50]}...")
            return True
        else:
            print(f"❌ Failed to post: {response.text}")
            return False

class PubMedSearcher:
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def search_rotifer_papers(self, days_back: int = 7) -> List[Dict]:
        """Search for recent rotifer papers on PubMed"""
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        date_range = f"{start_date.strftime('%Y/%m/%d')}:{end_date.strftime('%Y/%m/%d')}"
        
        # Build search query
        search_terms = "(rotifer[Title/Abstract] OR rotifers[Title/Abstract] OR bdelloid[Title/Abstract])"
        query = f"{search_terms} AND {date_range}[Publication Date]"
        
        print(f"🔍 Searching PubMed for: {query}")
        
        # Step 1: Search for PMIDs
        search_params = {
            'db': 'pubmed',
            'term': query,
            'retmax': 10,  # Limit to prevent spam
            'sort': 'pub date',
            'retmode': 'xml'
        }
        
        search_response = requests.get(f"{self.base_url}/esearch.fcgi", params=search_params)
        
        if search_response.status_code != 200:
            print(f"❌ PubMed search failed: {search_response.text}")
            return []
        
        # Parse PMIDs from search results
        pmids = self._extract_pmids(search_response.text)
        print(f"📚 Found {len(pmids)} papers")
        
        if not pmids:
            return []
        
        # Step 2: Fetch details for each paper
        papers = self._fetch_paper_details(pmids)
        return papers
    
    def _extract_pmids(self, xml_text: str) -> List[str]:
        """Extract PMIDs from PubMed search results"""
        try:
            root = ET.fromstring(xml_text)
            pmids = []
            for id_elem in root.findall(".//Id"):
                pmids.append(id_elem.text)
            return pmids
        except ET.ParseError:
            print("❌ Error parsing PubMed XML")
            return []
    
    def _fetch_paper_details(self, pmids: List[str]) -> List[Dict]:
        """Fetch detailed information for papers"""
        if not pmids:
            return []
        
        # Fetch details
        fetch_params = {
            'db': 'pubmed',
            'id': ','.join(pmids),
            'retmode': 'xml',
            'rettype': 'abstract'
        }
        
        response = requests.get(f"{self.base_url}/efetch.fcgi", params=fetch_params)
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch paper details: {response.text}")
            return []
        
        return self._parse_paper_details(response.text)
    
    def _parse_paper_details(self, xml_text: str) -> List[Dict]:
        """Parse paper details from PubMed XML"""
        papers = []
        
        try:
            root = ET.fromstring(xml_text)
            
            for article in root.findall(".//PubmedArticle"):
                paper = {}
                
                # Title
                title_elem = article.find(".//ArticleTitle")
                paper['title'] = title_elem.text if title_elem is not None else "No title"
                
                # Authors (first author only for brevity)
                author_list = article.find(".//AuthorList")
                if author_list is not None:
                    first_author = author_list.find(".//Author")
                    if first_author is not None:
                        last_name = first_author.find("LastName")
                        if last_name is not None:
                            paper['first_author'] = last_name.text
                
                # Journal
                journal_elem = article.find(".//Journal/Title")
                if journal_elem is not None:
                    paper['journal'] = journal_elem.text
                
                # Publication date
                pub_date = article.find(".//PubDate")
                if pub_date is not None:
                    year_elem = pub_date.find("Year")
                    if year_elem is not None:
                        paper['year'] = year_elem.text
                
                # PMID for URL
                pmid_elem = article.find(".//PMID")
                if pmid_elem is not None:
                    paper['pmid'] = pmid_elem.text
                    paper['pubmed_url'] = f"https://pubmed.ncbi.nlm.nih.gov/{pmid_elem.text}/"
                
                # DOI (preferred for links)
                doi_elem = article.find(".//ArticleId[@IdType='doi']")
                if doi_elem is not None:
                    paper['doi'] = doi_elem.text
                    paper['doi_url'] = f"https://doi.org/{doi_elem.text}"
                
                # Abstract (for keyword detection)
                abstract_elem = article.find(".//AbstractText")
                if abstract_elem is not None:
                    paper['abstract'] = abstract_elem.text or ""
                else:
                    paper['abstract'] = ""
                
                papers.append(paper)
                
        except ET.ParseError as e:
            print(f"❌ Error parsing paper details: {e}")
        
        return papers

def format_paper_post(paper: Dict) -> str:
    """Format paper data into a Bluesky post"""
    # Create engaging hook based on abstract content
    hooks = {
        'bdelloid': '🧬 Ancient asexual rotifers',
        'cryptobiosis': '💤 Surviving complete desiccation',
        'parthenogenesis': '🥚 Clonal reproduction',
        'wheel organ': '🌊 Filter-feeding masters',
        'desiccation': '🏜️ Extreme drought survival',
        'radiation': '☢️ DNA repair champions',
        'evolution': '🔬 Evolutionary insights'
    }
    
    hook = "#Rotifersky"  # default
    abstract_lower = paper.get('abstract', '').lower()
    
    for keyword, description in hooks.items():
        if keyword in abstract_lower:
            hook = description
            break
    
    # Build post text
    title = paper.get('title', 'Untitled')
    if len(title) > 120:
        title = title[:117] + "..."
    
    author = paper.get('first_author', '')
    author_text = f" • {author} et al." if author else ""
    
    journal = paper.get('journal', '')
    year = paper.get('year', '')
    journal_text = f" • {journal}" if journal else ""
    year_text = f" ({year})" if year else ""
    
    # Prefer DOI link over PubMed URL
    url = paper.get('doi_url') or paper.get('pubmed_url', '')
    
    post = f"{hook}\n\n{title}{author_text}{journal_text}{year_text}\n\n{url}"
    
    return post

def load_posted_papers() -> set:
    """Load list of already posted papers from file"""
    try:
        with open('posted_papers.json', 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_posted_paper(paper_id: str):
    """Save identifier of posted paper to avoid duplicates"""
    posted = load_posted_papers()
    posted.add(paper_id)
    with open('posted_papers.json', 'w') as f:
        json.dump(list(posted), f)

def main():
    # Get credentials from environment variables
    handle = os.getenv('BLUESKY_HANDLE')
    password = os.getenv('BLUESKY_PASSWORD')
    
    if not handle or not password:
        print("❌ Missing BLUESKY_HANDLE or BLUESKY_PASSWORD environment variables")
        return
    
    print("🤖 Starting Rotifer Literature Bot")
    
    # Initialize components
    try:
        bot = BlueskyBot(handle, password)
        searcher = PubMedSearcher()
        
        # Load already posted papers
        posted_papers = load_posted_papers()
        print(f"📋 Already posted {len(posted_papers)} papers")
        
        # Search for new papers
        papers = searcher.search_rotifer_papers(days_back=30)
        
        if not papers:
            print("📭 No new rotifer papers found")
            return
        
        # Post new papers (max 1 per run to avoid spamming small community)
        posted_count = 0
        max_posts = 1
        
        for paper in papers:
            pmid = paper.get('pmid', '')
            doi = paper.get('doi', '')
            title = paper.get('title', '')
            
            # Use DOI as backup identifier if PMID is missing
            paper_id = pmid if pmid else doi if doi else title[:50]
            
            if paper_id in posted_papers:
                print(f"⏭️ Skipping already posted paper: {paper_id}")
                continue
            
            if posted_count >= max_posts:
                print(f"📝 Reached max posts ({max_posts}) for this run")
                break
            
            # Format and post
            post_text = format_paper_post(paper)
            print(f"🔄 Attempting to post paper: {paper_id}")
            
            if bot.create_post(post_text):
                save_posted_paper(paper_id)
                posted_count += 1
                print(f"✅ Successfully posted and saved: {paper_id}")
            else:
                print(f"❌ Failed to post: {paper_id}")
            
        print(f"✅ Posted {posted_count} new papers")
        
    except Exception as e:
        print(f"❌ Bot error: {e}")

if __name__ == "__main__":
    main()
