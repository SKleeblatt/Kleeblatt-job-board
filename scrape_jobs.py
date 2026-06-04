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

# [CATEGORIES ו-TECH_KEYWORDS נשארים ללא שינוי כפי שהגדרנו]
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
    # הוסרו "remote" ו-"anywhere" כדי לוודא שרק משרות פיזיות בישראל נשמרות
    return any(k in loc.lower() for k in ["israel", "tel aviv", "herzliya", "haifa", "jerusalem", "raanana", "netanya", "ישראל"])

def detect_work_model(title, location, description=""):
    text = f"{title} {location} {description}".lower()
    if any(x in text for x in ["hybrid", "היברידי", "משולב"]): return "Hybrid"
    # הערה: עדיין נזהה remote במידה וזה רשום בתיאור המשרה עצמה
    if any(x in text for x in ["remote", "מהבית"]): return "Remote"
    if any(x in text for x in ["on-site", "onsite", "מהמשרד"]): return "On-site"
    return "Not Specified"

def extract_technologies(title, description=""):
    text = f"{title} {description}"
    found = [t for t in TECH_KEYWORDS if re.search(r'\b' + re.escape(t) + r'\b', text, re.IGNORECASE)]
    return found if found else ["Not Specified"]

# [פונקציות ה-fetch (fetch_greenhouse, fetch_comeet וכו') נשארות ללא שינוי]
# (השמטתי אותן כאן רק כדי לשמור על אורך הודעה סביר, אבל תשתמשי באלו מהקוד הקודם)

def main():
    if os.path.exists(JOBS_DIR):
        shutil.rmtree(JOBS_DIR)
    os.makedirs(JOBS_DIR)
    
    try:
        with open('companies.json', 'r', encoding='utf-8') as f: companies = json.load(f)
        with open('categories.json', 'r', encoding='utf-8') as f: sectors_map = json.load(f)
    except: return

    all_jobs_data = []
    categorized_jobs = {cat: [] for cat in CATEGORIES.keys()}
    categorized_jobs["other"] = []
    dev_cats = ["frontend", "backend", "fullstack", "devops", "software", "data science", "data"]

    for company in companies:
        comp_type, comp_id, comp_name = company.get('type', '').lower(), company.get('id'), company.get('name')
        ind = sectors_map.get(str(company.get('category_id', '')), "Technology")
        
        # [לוגיקת ה-raw_jobs נשארת כפי שהייתה]
        # ...

        for j in raw_jobs:
            title = j.get('title') or j.get('name') or j.get('text', 'No Title')
            loc = j.get('location', {}).get('name', 'Israel') if isinstance(j.get('location'), dict) else j.get('location', 'Israel')
            pub_date = j.get('created_at', datetime.now().strftime('%Y-%m-%d'))[:10]
            
            if is_in_israel(loc):
                cat = categorize_job(title)
                data = {
                    "company": comp_name,
                    "industry": ind,
                    "title": title,
                    "location": loc,
                    "work_model": detect_work_model(title, loc, j.get('description', '')),
                    "date": pub_date,
                    "url": j.get('absolute_url') or j.get('url_active_page') or j.get('hostedUrl') or j.get('jobUrl') or j.get('url', '#'),
                    "technologies": ", ".join(extract_technologies(title, j.get('description', ''))) if cat in dev_cats else "N/A"
                }
                categorized_jobs[cat].append(data)
                all_jobs_data.append(data)

    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["company", "industry", "title", "location", "work_model", "date", "url", "technologies"])
        writer.writeheader()
        writer.writerows(all_jobs_data)

    for cat, jobs in categorized_jobs.items():
        if not jobs: continue
        filename = f"{JOBS_DIR}/{cat.replace(' ', '_').replace('/', '_')}.csv"
        with open(filename, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["company", "industry", "title", "location", "work_model", "date", "url", "technologies"])
            writer.writeheader()
            writer.writerows(jobs)

if __name__ == "__main__":
    main()
