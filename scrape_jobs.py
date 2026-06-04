import os, requests, json, re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

JOBS_DIR = "jobs"

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

TECH_KEYWORDS = ["React", "Vue", "Angular", "Node", "Node.js", "Python", "Java", "Go", "Golang", "Ruby", "Rails", "PHP", "Laravel", "C#", ".NET", "C++", "TypeScript", "JavaScript", "AWS", "Azure", "GCP", "Docker", "Kubernetes", "SQL", "NoSQL", "MongoDB", "PostgreSQL", "Redis", "Kafka", "GraphQL", "Swift", "Kotlin", "Flutter", "React Native", "Snowflake", "Databricks", "Spark", "Hadoop", "Terraform", "CI/CD"]

def categorize_job(title):
    t = title.lower()
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in t: return cat
    return "other"

def is_in_israel(loc):
    if not loc: return False
    return any(k in loc.lower() for k in ["israel", "tel aviv", "herzliya", "haifa", "jerusalem", "raanana", "netanya", "remote", "anywhere", "ישראל"])

def detect_work_model(title, location, description=""):
    text = f"{title} {location} {description}".lower()
    if any(x in text for x in ["hybrid", "היברידי", "משולב"]): return "Hybrid"
    if any(x in text for x in ["remote", "מהבית", "anywhere"]): return "Remote"
    if any(x in text for x in ["on-site", "onsite", "מהמשרד"]): return "On-site"
    return "Not Specified"

def extract_technologies(title, description=""):
    text = f"{title} {description}"
    found = [t for t in TECH_KEYWORDS if re.search(r'\b' + re.escape(t) + r'\b', text, re.IGNORECASE)]
    return found if found else ["Not Specified"]

def fetch_greenhouse(cid):
    try:
        res = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{cid}/jobs?content=true", timeout=10)
        return res.json().get('jobs', []) if res.status_code == 200 else []
    except: return []

def fetch_comeet(cid):
    try:
        res = requests.get(f"https://www.comeet.co/careers-api/2.0/company/{cid}/positions?token=&details=true", timeout=10)
        return res.json() if res.status_code == 200 else []
    except: return []

def fetch_lever(cid):
    try:
        res = requests.get(f"https://api.lever.co/v0/postings/{cid}", timeout=10)
        return res.json() if res.status_code == 200 else []
    except: return []

def fetch_ashby(cid):
    try:
        res = requests.post("https://api.ashbyhq.com/react-api/v1/widgets/embed", json={"organizationId": cid}, timeout=10)
        return res.json().get("jobPostings", []) if res.status_code == 200 else []
    except: return []

def fetch_bamboohr(cid):
    try:
        res = requests.get(f"https://{cid}.bamboohr.com/jobs/embed2.php", timeout=10)
        if res.status_code != 200: return []
        soup = BeautifulSoup(res.text, 'html.parser')
        return [{"title": a.get_text(strip=True), "location": "Israel/Remote", "url": f"https://{cid}.bamboohr.com/careers/{a.get('href').split('=')[-1]}", "description": ""} for a in soup.select('.BambooHR-ATS-Jobs-Item a')]
    except: return []

def fetch_custom_site(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            soup = BeautifulSoup(page.content(), 'html.parser')
            browser.close()
            titles = ['engineer', 'developer', 'manager', 'specialist', 'analyst', 'vp', 'lead', 'expert', 'architect', 'product', 'sales', 'marketing', 'support', 'qa', 'cto']
            jobs = []
            for el in soup.find_all(['a', 'h3', 'h4', 'span'], class_=re.compile(r'job|position|career|title', re.I)):
                text = el.get_text(strip=True)
                if 5 < len(text) < 60 and any(kw in text.lower() for kw in titles):
                    link = el.get('href') if el.name == 'a' else url
                    jobs.append({"title": text, "location": "Israel/Remote", "url": link if link.startswith('http') else url.rstrip('/') + '/' + link.lstrip('/'), "description": ""})
            return jobs
    except: return []

def main():
    if not os.path.exists(JOBS_DIR): os.makedirs(JOBS_DIR)
    try:
        with open('companies.json', 'r', encoding='utf-8') as f: companies = json.load(f)
        with open('categories.json', 'r', encoding='utf-8') as f: sectors_map = json.load(f)
    except: return

    categorized_jobs = {cat: [] for cat in CATEGORIES.keys()}
    categorized_jobs["other"] = []
    dev_cats = ["frontend", "backend", "fullstack", "devops", "software", "data science", "data"]

    for company in companies:
        comp_type, comp_id, comp_name = company.get('type', '').lower(), company.get('id'), company.get('name')
        ind = sectors_map.get(str(company.get('category_id', '')), "Technology")
        
        raw_jobs = []
        if comp_type == 'greenhouse': raw_jobs = fetch_greenhouse(comp_id)
        elif comp_type == 'comeet': raw_jobs = fetch_comeet(comp_id)
        elif comp_type == 'lever': raw_jobs = fetch_lever(comp_id)
        elif comp_type == 'ashby': raw_jobs = fetch_ashby(comp_id)
        elif comp_type == 'bamboohr': raw_jobs = fetch_bamboohr(comp_id)
        elif comp_type == 'custom': raw_jobs = fetch_custom_site(company.get('url'))

        for j in raw_jobs:
            title = j.get('title') or j.get('name') or j.get('text', 'No Title')
            loc = j.get('location', {}).get('name', 'Israel') if isinstance(j.get('location'), dict) else j.get('location', 'Israel')
            if is_in_israel(loc):
                cat = categorize_job(title)
                data = {
                    "company": comp_name,
                    "industry": ind,
