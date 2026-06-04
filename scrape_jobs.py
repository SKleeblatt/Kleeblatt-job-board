import os, requests, json, re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

JOBS_DIR = "jobs"

# Technical job role categories
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
    combined_text = f"{title} {location} {description}".lower()
    if any(x in combined_text for x in ["hybrid", "היברידי", "משולב"]): return "Hybrid"
    if any(x in combined_text for x in ["remote", "מהבית", "anywhere"]): return "Remote"
    if any(x in combined_text for x in ["on-site", "onsite", "מהמשרד"]): return "On-site"
    return "Not Specified"

def extract_technologies(title, description=""):
    combined_text = f"{title} {description}"
    found_tech = []
    for tech in TECH_KEYWORDS:
        if re.search(r'\b' + re.escape(tech) + r'\b', combined_text, re.IGNORECASE):
            found_tech.append(tech)
    return found_tech if found_tech else ["Not Specified"]

def fetch_greenhouse(cid):
    try:
        res = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{cid}/jobs?content=true", timeout=10)
        if res.status_code == 200:
            return res.json().get('jobs', [])
    except: pass
    return []

def fetch_comeet(cid):
    try:
        res = requests.get(f"https://www.comeet.co/careers-api/2.0/company/{cid}/positions?token=&details=true", timeout=10)
        if res.status_code == 200:
            return res.json()
    except: pass
    return []

def fetch_lever(cid):
    try:
        res = requests.get(f"https://api.lever.co/v0/postings/{cid}", timeout=10)
        if res.status_code == 200:
            return res.json()
    except: pass
    return []

def fetch_ashby(cid):
    try:
        res = requests.post("https://api.ashbyhq.com/react-api/v1/widgets/embed", json={"organizationId": cid}, timeout=10)
        if res.status_code == 200:
            return res.json().get("jobPostings", [])
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
    if not url or any(k in url for k in ["linkedin.com", "forms.gle"]):
        return jobs
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            soup = BeautifulSoup(page.content(), 'html.parser')
            browser.close()
            elements = soup.find_all(['a', 'h3', 'h4', 'span'], class_=re.compile(r'job|position|career|title', re.I))
            titles = ['engineer', 'developer', 'manager', 'specialist', 'analyst', 'vp', 'lead', 'expert', 'architect', 'product', 'sales', 'marketing', 'support', 'qa', 'cto']
            for el in elements:
                text = el.get_text(strip=True)
                if 5 < len(text) < 60 and any(kw in text.lower() for kw in titles):
                    link = el.get('href') if el.name == 'a' else url
                    jobs.append({"title": text, "location": "Israel/Remote", "url": link if link.startswith('http') else url.rstrip('/') + '/' + link.lstrip('/'), "description": ""})
    except: pass
    return list({tuple(d.items()) for d in jobs})

def main():
    if not os.path.exists(JOBS_DIR): os.makedirs(JOBS_DIR)
    try:
        with open('companies.json', 'r', encoding='utf-8') as f: companies = json.load(f)
        with open('categories.json', 'r', encoding='utf-8') as f: sectors_map = json.load(f)
    except: return

    categorized_jobs = {cat: [] for cat in CATEGORIES.keys()}
    categorized_jobs["other"] = []
    dev_categories = ["frontend", "backend", "fullstack", "devops", "software", "data science", "data"]

    for company in companies:
        comp_jobs = []
        comp_type, comp_id, comp_name = company.get('type', '').lower(), company.get('id'), company.get('name')
        comp_url = company.get('url') or company.get('careers_url')
        industry_name = sectors_map.get(str(company.get('category_id', '')), "Technology")
        
        try:
            if comp_type == 'greenhouse':
                for j in fetch_greenhouse(comp_id):
                    if is_in_israel(j.get('location', {}).get('name', '')):
                        comp_jobs.append({"title": j['title'], "location": j['location']['name'], "url": j['absolute_url'], "description": j.get('content', '')})
            elif comp_type == 'comeet':
                for j in fetch_comeet(comp_id):
                    if is_in_israel(j.get('location', {})):
                        comp_jobs.append({"title": j['name'], "location": j['location'], "url": j.get('url_active_page'), "description": j.get('description', '')})
            elif comp_type == 'lever':
                for j in fetch_lever(comp_id):
                    if is_in_israel(j.get('categories', {}).get('location', '')):
                        comp_jobs.append({"title": j['text'], "location": j['categories']['location'], "url": j['hostedUrl'], "description": j.get('descriptionPlain', '')})
            elif comp_type == 'ashby':
                for j in fetch_ashby(comp_id):
                    if is_in_israel(j.get('location', '')):
                        comp_jobs.append({"title": j['title'], "location": j['location'], "url": j['jobUrl'], "description": j.get('descriptionHtml', '')})
            elif comp_type == 'bamboohr': comp_jobs = fetch_bamboohr(comp_id)
            elif comp_type == 'custom': comp_jobs = fetch_custom_site(comp_url)

            for job in comp_jobs:
                cat = categorize_job(job['title'])
                job_data = {
                    "company": comp_name, "industry": industry_name, "title": job['title'],
                    "location": job['location'], "work_model": detect
