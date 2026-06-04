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

# Core stack keywords for technology extraction in development roles
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
    if "hybrid" in combined_text or "היברידי" in combined_text or "משולב" in combined_text:
        return "Hybrid"
    elif "remote" in combined_text or "מהבית" in combined_text or "anywhere" in combined_text:
        return "Remote"
    elif "on-site" in combined_text or "onsite" in combined_text or "מהמשרד" in combined_text:
        return "On-site"
    return "Not Specified (Likely On-site/Hybrid)"

def extract_technologies(title, description=""):
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
    if not url or any(k in url for k in ["linkedin.com", "forms.gle"]): return jobs
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({"User-Agent": "Mozilla/5.0"})
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)
            soup = BeautifulSoup(page.content(), 'html.parser')
            browser.close()
            
            elements = soup.find_all(['a', 'h3', 'h4', 'span'], class_=re.compile(r'job|position|career|title', re.I))
            titles = ['engineer', 'developer', 'manager', 'specialist', 'analyst', 'vp', 'lead', 'expert', 'architect', 'product', 'sales', 'marketing', 'support', 'qa', 'cto']
            for el in elements:
                text = el.get_text(strip=True)
                if 5 < len(text) < 60 and any(kw in text.lower() for kw in titles):
                    link = url
                    if el.name == 'a' and el.get('href'):
                        href = el.get('href')
                        link = href if href.startswith('http') else url.rstrip('/') + '/' + href.lstrip('/')
                    jobs.append({"title": text, "location": "Israel/Remote", "url": link, "description": ""})
            jobs = [dict(t) for t in {tuple(d.items()) for d in jobs}]
    except: pass
    return jobs

# ==========================================
# Main Orchestrator
# ==========================================

def main():
    if not os.path.exists(JOBS_DIR): os.makedirs(JOBS_DIR)
    
    # Load companies and categories configuration files safely
    try:
        with open('companies.json', 'r', encoding='utf-8') as f: 
            companies = json.load(f)
        with open('categories.json', 'r', encoding='utf-8') as f: 
            sectors_map = json.load(f)
    except Exception as e:
        with open("README.md", "w", encoding='utf-8') as f: 
            f.write(f"# Configuration Error: {e}")
        return

    categorized_jobs = {cat: [] for cat in CATEGORIES.keys()}
    categorized_jobs["other"] = []
    debug_log = "### 🔍 Scraping Progress & Logs:\n"

    dev_categories = ["frontend", "backend", "fullstack", "devops", "software", "data science", "data"]

    for company in companies:
        comp_jobs = []
        comp_type = company.get('type', '').lower()
        comp_id = company.get('id')
        comp_name = company.get('name')
        comp_url = company.get('url') or company.get('careers_url')
        
        # Determine the company industry sector using categories.json
        industry_id = str(company.get('category_id', company.get('category', '')))
        industry_name = sectors_map.get(industry_id, "Technology")

        try:
            if comp_type == 'greenhouse' and comp_id:
                for j in fetch_greenhouse(comp_id):
                    loc = j.get('location', {}).get('name', 'Israel')
                    if is_in_israel(loc):
                        comp_jobs.append({"title": j['title'], "location": loc, "url": j['absolute_url'], "description": j.get('content', '')})
                        
            elif comp_type == 'comeet' and comp_id:
                for j in fetch_comeet(comp_id):
                    loc = j.get('location', {}).get('name', 'Israel')
                    if is_in_israel(loc):
                        comp_jobs.append({"title": j['name'], "location": loc, "url": j.get('url_active_page'), "description": j.get('description', '')})

            elif comp_type == 'lever' and comp_id:
                for j in fetch_lever(comp_id):
                    loc = j.get('categories', {}).get('location', 'Israel')
                    if is_in_israel(loc):
                        comp_jobs.append({"title": j['text'], "location": loc, "url": j['hostedUrl'], "description": j.get('descriptionPlain', '')})

            elif comp_type == 'ashby' and comp_id:
                for j in fetch_ashby(comp_id):
                    loc = j.get('location', 'Israel')
                    if is_in_israel(loc):
                        comp_jobs.append({"title": j['title'], "location": loc, "url": j['jobUrl'], "description": j.get('descriptionHtml', '')})

            elif comp_type == 'bamboohr' and comp_id:
                comp_jobs = fetch_bamboohr(comp_id)

            elif comp_type == 'custom' and comp_url:
                comp_jobs = fetch_custom_site(comp_url)

            # Processing individual job entries with sector context
            for job in comp_jobs:
                cat = categorize_job(job['title'])
                work_model = detect_work_model(job['title'], job['location'], job.get('description', ''))
                
                job_data = {
                    "company": comp_name,
                    "industry": industry_name,
                    "title": job['title'],
                    "location": job['location'],
                    "work_model": work_model,
                    "url": job['url']
                }
                
                if cat in dev_categories:
                    job_data["technologies"] = extract_technologies(job['title'], job.get('description', ''))
                
                categorized_jobs[cat].append(job_data)

        except Exception as e:
            debug_log += f"- Error scraping {comp_name}: {str(e)}\n"

    # Creating clean English Markdown files per category inside /jobs folder
    for cat, jobs in categorized_jobs.items():
        if not jobs:
            continue
            
        filename = f"{JOBS_DIR}/{cat.replace(' ', '_').replace('/', '_')}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Open Positions in {cat.title()}\n\n")
            f.write(f"Last updated: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
            
            for j in jobs:
                f.write(f"### [{j['title']}]({j['url']})\n")
                f.write(f"- **Company:** {j['company']}\n")
                f.write(f"- **Industry Sector:** {j['industry']}\n")
                f.write(f"- **Location:** {j['location']}\n")
                f.write(f"- **Work Model:** {j['work_model']}\n")
                
                if "technologies" in j:
                    tech_str = ", ".join(j["technologies"])
                    f.write(f"- **Technologies Stack:** {tech_str}\n")
                
                f.write("\n---\n\n")

    # Saving execution metrics inside the root README.md file
    with open("README.md", "w", encoding="utf-8") as f:
        f.write("# 🚀 Automated Israel Tech Job Board\n\n")
        f.write(f"Last execution context: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
        f.write("### Available Tracks:\n")
        for cat in categorized_jobs.keys():
            if len(categorized_jobs[cat]) > 0:
                f.write(f"- [{cat.title()}](jobs/{cat.replace(' ', '_')}.md) ({len(categorized_jobs[cat])} jobs found)\n")
        f.write("\n" + debug_log)

if __name__ == "__main__":
    main()
