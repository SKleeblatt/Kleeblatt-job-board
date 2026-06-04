import os
import requests
import json
import re
import csv
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

JOBS_DIR = "jobs"
CSV_FILE = "all_jobs.csv"

# [CATEGORIES ו-TECH_KEYWORDS נשארים אותו דבר כפי שהגדרנו קודם]
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

# ... (פונקציות העזר: categorize_job, is_in_israel, detect_work_model, extract_technologies, fetch_* נשארות ללא שינוי)

def main():
    if not os.path.exists(JOBS_DIR): os.makedirs(JOBS_DIR)
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
        
        # [לוגיקת ה-fetch נשארת ללא שינוי]
        # ... (כאן תבוא הלוגיקה של איסוף המשרות לתוך raw_jobs)

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

    # 1. כתיבה ל-CSV (קובץ אחד לכל המשרות)
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["company", "industry", "title", "location", "work_model", "date", "url", "technologies"])
        writer.writeheader()
        writer.writerows(all_jobs_data)

    # 2. כתיבה ל-Markdown (קבצים נפרדים בתוך תיקיית jobs)
    for cat, jobs in categorized_jobs.items():
        if not jobs: continue
        with open(f"{JOBS_DIR}/{cat.replace(' ', '_').replace('/', '_')}.md", "w", encoding="utf-8") as f:
            f.write(f"# Open Positions in {cat.title()}\n\n")
            for j in jobs:
                f.write(f"### [{j['title']}]({j['url']})\n")
                f.write(f"- **Company:** {j['company']}\n")
                f.write(f"- **Date:** {j['date']}\n")
                f.write(f"- **Location:** {j['location']}\n")
                f.write(f"- **Model:** {j['work_model']}\n")
                if j["technologies"] != "N/A": f.write(f"- **Tech:** {j['technologies']}\n")
                f.write("\n---\n\n")

if __name__ == "__main__":
    main()
