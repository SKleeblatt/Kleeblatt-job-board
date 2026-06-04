import os, requests, json, re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

JOBS_DIR = "jobs"

# Categories with management tech included
CATEGORIES = {
    "management tech": ["cto", "vp r&d", "vp rd", "director of r&d", "director of rd", "head of r&d", "head of rd", "vp engineering"],
    "frontend": ["frontend", "front-end", "front end", "react", "vue", "angular", "ui/ux", "web sdk"],
    "backend": ["backend", "back-end", "back end", "python", "node", "java", "go ", "golang", "ruby"],
    "fullstack": ["fullstack", "full-stack", "full stack", "web developer"],
    "devops": ["devops", "dev-ops", "sre", "infrastructure", "cloud engineer", "platform engineer", "kubernetes"],
    "qa": ["qa ", "automation engineer", "testing", "test engineer", "quality assurance"],
    "data science": ["data scientist", "data science", "machine learning", "ml ", "ai engineer", "deep learning", "nlp", "computer vision"],
    "data": ["data analyst", "data engineer", "bi analyst", "analytics", "fraud intelligence", "threat analyst"],
    "product": ["product manager", "product owner", "vp product", "director of product", "product specialist"],
    "project": ["project manager", "scrum master", "delivery", "program manager", "operations manager"],
    "sales": ["sales", "account manager", "bizdev", "business development", "inside sales", "account executive", "presales", "pre-sales"],
    "marketing": ["marketing", "seo", "growth", "content creator", "copywriter", "ppc", "brand"],
    "support": ["support", "customer success", "technical account manager", "tam", "helpdesk", "tier"],
    "software": ["software engineer", "software developer", "r&d", "developer", "architect"]
}

# Technical stack keywords for tech jobs extraction
TECH_KEYWORDS = [
    "React", "Vue", "Angular", "Node", "Node.js", "Python", "Java", "Go", "Golang", 
    "Ruby", "Rails", "PHP", "Laravel", "C#", ".NET", "C++", "TypeScript", "JavaScript", 
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "SQL", "NoSQL", "MongoDB", "PostgreSQL", 
    "Redis", "Kafka", "GraphQL", "Swift", "Kotlin", "Flutter", "React Native", "Snowflake",
    "Databricks", "Spark", "Hadoop", "Terraform", "CI/CD"
]

def categorize_job(title):
    t = title.lower()
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in t: return cat
    return "other"

def is_in_israel(loc):
    if not loc: return False
    l = loc.lower()
    kw = ["israel", "tel aviv", "herzliya", "haifa", "jerusalem", "raanana", "netanya", "remote", "anywhere", "ישראל"]
    return any(k in l for k in kw)

def detect_work_model(title, location, description=""):
    """
    Detects whether the job is On-site, Remote, or Hybrid based on text keywords.
    """
    combined_text = f"{title} {location} {description}".lower()
    
    if "hybrid" in combined_text or "היברידי" in combined_text or "משולב" in combined_text:
        return "Hybrid"
    elif "remote" in combined_text or "מהבית" in combined_text or "anywhere" in combined_text:
        return "Remote"
    elif "on-site" in combined_text or "onsite" in combined_text or "מהמשרד" in combined_text:
        return "On-site"
    
    return "Not Specified (Likely On-site/Hybrid)"

def extract_technologies(title, description=""):
    """
    Extracts technologies mentioned in the title or description.
    """
    combined_text = f"{title} {description}"
    found_tech = []
    
    for tech in TECH_KEYWORDS:
        pattern = r'\b' + re.escape(tech) + r'\b'
        if re.search(pattern, combined_text, re.IGNORECASE):
            found_tech.append(tech)
            
    return found_tech if found_tech else ["Not Specified"]

# ==========================================
# Fetch Functions (Secure & Compact)
# ==========================================

def fetch_greenhouse(cid):
    try:
        res = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{cid}/jobs?content=true", timeout=10)
        if res.status_code == 200: return res.json().get('jobs', [])
    except: pass
    return []

def fetch_comeet(cid):
    try:
        res = requests.get(f"https://www.comeet.co/careers-api/2.0/company/{cid}/positions?token=&details=true", timeout=10)
        if res.status_code == 200: return res.json()
    except: pass
    return []

def fetch_lever(cid):
    try:
        res = requests.get(f"https://api.lever.co/v0/postings/{cid}", timeout=10)
        if res.status_code == 200: return res.json()
    except: pass
    return []

def fetch_ashby(cid):
    try:
        res = requests.post("https://api.ashbyhq.com/react-api/v1/widgets/embed", json={"organizationId": cid}, timeout=10)
        if res.status_code == 200: return res.json().get("jobPostings", [])
    except: pass
    return []

def fetch_bamboohr(cid):
    jobs = []
    try:
        res = requests.get(f"https://{cid}.bamboohr.com/jobs/embed2.php", timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for row in soup.select('.BambooHR-ATS-Jobs-Item a'):
                jid = row.get('href').split('=')[-1]
                jobs.append({
                    "title": row.get_text(strip=True),
                    "location": "Israel/Remote",
                    "url": f"https://{cid}.bamboohr.com/careers/{jid}",
                    "description": ""
                })
    except: pass
    return jobs

def fetch_custom_site(url):
    jobs = []
    if not url or any(k in url for k in
