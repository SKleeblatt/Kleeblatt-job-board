import os
import shutil
import requests
import json
import re
import csv
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

JOBS_DIR = "jobs"
CSV_FILE = "all_jobs.csv"

# מילון הקטגוריות המעודכן והמדויק
CATEGORIES = {
    "Executive R&D": ["cto", "vp r&d", "vp rd", "svp r&d", "head of r&d", "head of rd", "vp engineering", "svp engineering", "head of engineering"],
    "mobile": ["mobile", "ios", "android", "flutter", "react native", "swift", "kotlin"],
    "frontend": ["frontend", "front-end", "front end", "react", "vue", "angular", "ui/ux", "web sdk"],
    "backend": ["backend", "back-end", "back end", "python", "node", "java", "go ", "golang", "ruby"],
    "fullstack": ["fullstack", "full-stack", "full stack", "web developer"],
    "devops": ["devops", "dev-ops", "sre", "infrastructure", "cloud engineer", "platform engineer", "kubernetes"],
    "qa": ["qa ", "automation engineer", "testing", "test engineer", "quality assurance"],
    "automation": ["automation engineer", "automation", "test automation"],
    "data science": ["data scientist", "data science", "machine learning", "ml ", "deep learning", "nlp", "computer vision"],
    "ai engineer": ["ai engineer", "artificial intelligence", "generative ai"],
    "data": ["data analyst", "data engineer", "bi analyst", "analytics", "fraud intelligence", "threat analyst"],
    "security": ["security", "cyber", "infosec", "soc", "penetration", "ciso"],
    "procurement operations": ["procurement", "operations manager", "ops manager", "supply chain"],
    "product": ["product manager", "product owner", "vp product", "director of product", "product specialist"],
    "project": ["project manager", "scrum master", "delivery", "program manager"],
    "sales": ["sales", "account manager", "bizdev", "business development", "inside sales", "account executive", "presales"],
    "marketing": ["marketing", "seo", "growth", "content creator", "copywriter", "ppc", "brand"],
    "support": ["support", "customer success", "technical account manager", "tam", "helpdesk", "tier"],
    "software": ["software engineer", "software developer", "r&d", "developer", "architect", "director of r&d", "director of rd"]
}

TECH_KEYWORDS = ["React", "Vue", "Angular", "Node", "Node.js", "Python", "Java", "Go", "Golang", "Ruby", "Rails", "PHP", "Laravel", "C#", ".NET", "C++", "TypeScript", "JavaScript", "AWS", "Azure", "GCP", "Docker", "Kubernetes", "SQL", "NoSQL", "MongoDB", "PostgreSQL", "Redis", "Kafka", "GraphQL", "Swift", "Kotlin", "Flutter", "React Native", "Snowflake", "Databricks", "Spark", "Hadoop", "Terraform", "CI/CD"]

def categorize_job(title):
    t = title.lower()
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in t: 
                return cat
    return "other"

def is_in_israel(loc, title=""):
    loc_lower = loc.lower() if loc else ""
    title_lower = title.lower() if title else ""
    
    # מילים שפוסלות את המשרה מיידית (למשל משרות גלובליות או מדינות אחרות)
    blacklist = ["remote us", "remote usa", "europe", "london", "berlin", "new york", "san francisco", "india", "ukraine", "poland", "romania"]
    for word in blacklist:
        if word in loc_lower or word in title_lower:
            return False

    # מילות מפתח לאישור המיקום בישראל
    israel_keywords = [
        "israel", "ישראל", "tel aviv", "תל אביב", "herzliya", "הרצליה", 
        "haifa", "חיפה", "jerusalem", "ירושלים", "raanana", "רעננה", 
        "netanya", "נתניה", "petah tikva", "פתח תקווה", "rehovot", "רחובות",
        "yokneam", "יקנעם", "hod hasharon", "הוד השרון", "givatayim", "גבעתיים", "ramat gan", "רמת גן"
    ]
    return any(k in loc_lower for k in israel_keywords) or any(k in title_lower for k in israel_keywords)

def detect_work_model(title, location, description=""):
    text = f"{title} {location} {description}".lower()
    if any(x in text for x in ["hybrid", "היברידי", "משולב"]): return "Hybrid"
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
        return [{"title": a.get_text(strip=True), "location": "", "url": f"https://{cid}.bamboohr.com/careers/{a.get('href').split('=')[-1]}", "description": ""} for a in soup.select('.BambooHR-ATS-Jobs-Item a')]
    except: return []

def fetch_custom_site(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            soup = BeautifulSoup(page.content(), 'html.parser')
            browser.close()
            titles = ['engineer', 'developer', 'manager', 'specialist', 'analyst', 'vp', 'lead', 'expert', 'architect', 'product', 'sales', 'marketing', 'support', 'qa', 'cto', 'security', 'head']
            jobs = []
            for el in soup.find_all(['a', 'h3', 'h4', 'span'], class_=re.compile(r'job|position|career|title', re.I)):
                text = el.get_text(strip=True)
                if 5 < len(text) < 60 and any(kw in text.lower() for kw in titles):
                    link = el.get('href') if el.name == 'a' else url
                    jobs.append({"title": text, "location": "", "url": link if link.startswith('http') else url.rstrip('/') + '/' + link.lstrip('/'), "description": ""})
            return jobs
    except: return []

def load_existing_jobs():
    """טוען משרות קיימות מהקובץ הראשי כדי לשמור על תאריכים מקוריים ולמנוע כפילויות"""
    existing_jobs = {}
    if os.path.exists(CSV_FILE):
        try:
            with open(CSV_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('url'):
                        existing_jobs[row['url']] = row
        except Exception as e:
            print(f"Error loading existing CSV: {e}")
    return existing_jobs

def main():
    # 1. טעינת בסיס הנתונים הקיים
    existing_jobs = load_existing_jobs()
    
    # 2. ניקוי ויצירת תיקיית הקטגוריות מחדש לצורך חלוקה עדכנית
    if os.path.exists(JOBS_DIR): shutil.rmtree(JOBS_DIR)
    os.makedirs(JOBS_DIR)
    
    try:
        with open('companies.json', 'r', encoding='utf-8') as f: companies = json.load(f)
        with open('categories.json', 'r', encoding='utf-8') as f: sectors_map = json.load(f)
    except Exception as e:
        print(f"Error loading config files: {e}")
        return

    new_jobs_count = 0
    dev_cats = ["frontend", "backend", "fullstack", "devops", "software", "data science", "data", "ai engineer", "automation", "mobile"]

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
            title = j.get('title') or j.get('name') or j.get('text', 'No Title').strip()
            loc = j.get('location', {}).get('name', '') if isinstance(j.get('location'), dict) else j.get('location', '')
            url = j.get('absolute_url') or j.get('url_active_page') or j.get('hostedUrl') or j.get('jobUrl') or j.get('url', '#').strip()
            
            # הגנה מפני כפל: אם ה-URL כבר קיים, לא נוגעים במשרה ולא מעדכנים תאריך
            if url in existing_jobs:
                continue

            if is_in_israel(loc, title):
                # שליפת תאריך מגוונת מה-API, ואם לא קיים - תאריך הגילוי של הריצה הנוכחית
                raw_date = j.get('created_at') or j.get('postedAt') or j.get('published') or datetime.now().strftime('%Y-%m-%d')
                pub_date = raw_date[:10]
                
                cat = categorize_job(title)
                data = {
                    "company": comp_name,
                    "industry": ind,
                    "title": title,
                    "location": loc if loc else "Israel (Detected)",
                    "work_model": detect_work_model(title, loc, j.get('description', '')),
                    "date": pub_date,
                    "url": url,
                    "technologies": ", ".join(extract_technologies(title, j.get('description', ''))) if cat in dev_cats else "N/A"
                }
                existing_jobs[url] = data
                new_jobs_count += 1

    print(f"Scraping completed. Found {new_jobs_count} new jobs. Total unique jobs in file: {len(existing_jobs)}")

    # הפיכת המילון חזרה לרשימה
    all_jobs_data = list(existing_jobs.values())
    
    # מיון המשרות מהחדש ביותר לישן ביותר
    all_jobs_data.sort(key=lambda x: x['date'], reverse=True)

    # 3. כתיבה מחדש לקובץ הראשי המאוחד
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["company", "industry", "title", "location", "work_model", "date", "url", "technologies"])
        writer.writeheader()
        writer.writerows(all_jobs_data)

    # 4. חלוקה מחדש ומעודכנת לקבצי הקטגוריות בתיקייה
    categorized_jobs = {cat: [] for cat in CATEGORIES.keys()}
    categorized_jobs["other"] = []
    
    for data in all_jobs_data:
        cat = categorize_job(data['title'])
        categorized_jobs[cat].append(data)

    for cat, jobs in categorized_jobs.items():
        if not jobs: continue
        filename = f"{JOBS_DIR}/{cat.replace(' ', '_').replace('/', '_')}.csv"
        with open(filename, "w", newline='', encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["company", "industry", "title", "location", "work_model", "date", "url", "technologies"])
            writer.writeheader()
            writer.writerows(jobs)

if __name__ == "__main__":
    main()
