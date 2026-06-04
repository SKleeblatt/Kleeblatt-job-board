import os
import requests
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# הגדרת תיקיית היעד לקטגוריות
JOBS_DIR = "jobs"

# מילון קטגוריות ומילות מפתח למיון חכם (לפי סדר עדיפות)
CATEGORIES = {
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

def categorize_job(title):
    """מנתח את כותרת המשרה ומשייך אותה לקטגוריה המתאימה ביותר"""
    title_lower = title.lower()
    for category, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in title_lower:
                return category
    return "other"

def is_in_israel(location_text):
    """פונקציית סינון חדשה: בודקת אם המיקום הוא בישראל או שלט רחוק"""
    if not location_text:
        return False
    loc_lower = location_text.lower()
    # רשימת מילות מפתח שמעידות על משרה רלוונטית בישראל
    israel_keywords = ["israel", "tel aviv", "herzliya", "haifa", "jerusalem", "raanana", "netanya", "remote", "anywhere"]
    return any(kw in loc_lower for kw in israel_keywords)

# ==========================================
# פונקציות ה-Fetch
# ==========================================

def fetch_greenhouse(company_id):
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_id}/jobs"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json().get('jobs', [])
    except: pass
    return []

def fetch_comeet(company_id):
    url = f"https://www.comeet.co/careers-api/2.0/company/{company_id}/positions?token=&details=true"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except: pass
    return []

def fetch_lever(company_id):
    url = f"https://api.lever.co/v0/postings/{company_id}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except: pass
    return []

def fetch_ashby(company_id):
    url = "https://api.ashbyhq.com/react-api/v1/widgets/embed"
    try:
        response = requests.post(url, json={"organizationId": company_id}, timeout=10)
        if response.status_code == 200:
            return response.json().get("jobPostings", [])
    except: pass
    return []

def fetch_bamboohr(company_id):
    url = f"https://{company_id}.bamboohr.com/jobs/embed2.php"
    jobs = []
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for row in soup.select('.BambooHR-ATS-Jobs-Item a'):
                jobs.append({
                    "title": row.get_text(strip=True),
                    "location": "Israel/Remote",
                    "url": f"https://{company_id}.bamboohr.com/careers/" + row.get('href').split('=')[-1]
                })
    except: pass
    return jobs

def fetch_custom_site(url):
    jobs = []
    if not url or "linkedin.com" in url or "forms.gle" in url:
        return jobs
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)
            soup = BeautifulSoup(page.content(), 'html.parser')
            browser.close()
            
            found_elements = soup.find_all(['a', 'h3', 'h4', 'span'], class_=re.compile(r'job|position|career|title', re.I))
            for el in found_elements:
                text = el.get_text(strip=True)
                if 5 < len(text) < 60 and any(kw in text.lower() for kw in ['engineer', 'developer', 'manager', 'specialist', 'analyst', 'vp', 'lead', 'expert', 'architect', 'product', 'sales', 'marketing', 'support', 'qa']):
                    link = url
                    if el.name == 'a' and el.get('href'):
                        link = el.get('href') if el.get('href').startswith('http') else url.rstrip('/') + '/' + el.get('href').lstrip('/')
                    jobs.append({"title": text, "location": "Israel/Remote", "url": link})
            jobs = [dict(t) for t in {tuple(d.items()) for d in jobs}]
    except Exception as e:
        print(f"Error custom scanning {url}: {e}")
    return jobs

# ==========================================
# הפונקציה המרכזית
# ==========================================

def main():
    if not os.path.exists(JOBS_DIR):
        os.makedirs(JOBS_DIR)

    try:
        with open('companies.json', 'r', encoding='utf-8') as f:
            companies = json.load(f)
    except Exception as e:
        with open("README.md", "w", encoding='utf-8') as f:
            f.write(f"# Error reading companies.json\n\n{e}")
        return

    categorized_jobs = {cat: [] for cat in CATEGORIES.keys()}
    categorized_jobs["other"] = []
    
    debug_log = "### 🔍 לוג בדיקה והתקדמות הסריקה:\n"

    for company in companies:
        jobs = []
        comp_type = company.get('type', '').lower()
        comp_id = company.get('id')
        comp_name = company.get('name')
        comp_url = company.get('url') or company.get('careers_url')

        try:
            if comp_type == 'greenhouse' and comp_id:
                raw_jobs = fetch_greenhouse(comp_id)
                for j in raw_jobs:
                    loc = j.get('location', {}).get('name', 'Unknown')
                    if is_in_israel(loc):
                        jobs.append({"title": j['title'], "location": loc, "url": j['absolute_url']})
            elif comp_type == 'comeet' and comp_id:
                raw_jobs = fetch_comeet(comp_id)
                for j in raw_jobs:
                    loc = j.get('location', {}).get('name', 'Unknown')
                    if is_in_israel(loc):
                        jobs.append({"title": j['name'], "location": loc, "url": j.get('url_active_page') or comp_url})
            elif comp_type == 'lever' and comp_id:
                raw_jobs = fetch_lever(comp_id)
                for j in raw_jobs:
                    loc = j.get('categories', {}).get('location', 'Unknown')
                    if is_in_israel(loc):
                        jobs.append({"title": j['text'], "location": loc, "url": j['hostedUrl']})
            elif comp_type == 'ashby' and comp_id:
                raw_jobs = fetch_ashby(comp_id)
                for j in raw_jobs:
                    loc = j.get('location', 'Unknown')
                    if is_in_israel(loc):
                        jobs.append({"title": j.get('title'), "location": loc, "url": j.get('jobUrl')})
            elif comp_type == 'bamboohr' and comp_id:
                # בבמבוהו"ר בד"כ זה מראש מסונן לעמוד החברה הישראלי, נשמור רק את מה שרלוונטי
                raw_jobs = fetch_bamboohr(comp_id)
                for j in raw_jobs:
                    if is_in_israel(j['location']):
                        jobs.append(j)
            elif comp_type == 'custom' or (comp_url and not comp_id):
                raw_jobs = fetch_custom_site(comp_url)
                for j in raw_jobs:
                    if is_in_israel(j['location']):
                        jobs.append(j)

            debug_log += f"- **{comp_name}** ({comp_type or 'custom'}): נמצאו {len(jobs)} משרות רלוונטיות בישראל.\n"

            for job in jobs:
                category = categorize_job(job['title'])
                categorized_jobs[category].append({
                    "company": comp_name,
                    "title": job['title'].replace('|', '-'),
                    "location": job['location'].replace('|', '-'),
                    "url": job['url']
                })
        except Exception as e:
            debug_log += f"- **{comp_name}**: שגיאה במהלך הסריקה - {e}\n"

    # כתיבת קבצי הקטגוריות
    for category, job_list in categorized_jobs.items():
        cat_file_path = os.path.join(JOBS_DIR, f"{category.replace(' ', '_')}.md")
        
        if not job_list:
            if os.path.exists(cat_file_path):
                os.remove(cat_file_path)
            continue
            
        cat_content = f"# 💼 משרות בקטגוריית {category.upper()}\n\n"
        cat_content += f"עודכן לאחרונה: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        cat_content += "| חברה | משרה | מיקום | קישור |\n"
        cat_content += "| :--- | :--- | :--- | :--- |\n"
        
        for job in job_list:
            cat_content += f"| {job['company']} | {job['title']} | {job['location']} | [הגש מועמדות]({job['url']}) |\n"
            
        with open(cat_file_path, "w",
