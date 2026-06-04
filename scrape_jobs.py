import requests
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ==========================================
# פונקציות ה-Fetch (מערכות גיוס מובנות)
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

# ==========================================
# פונקציית סריקה לאתרים עצמאיים (Custom/Playwright)
# ==========================================

def fetch_custom_site(url):
    """סורק אתרים דינמיים ועצמאיים ומחלץ משרות לפי מילות מפתח"""
    jobs = []
    if not url or "linkedin.com" in url or "forms.gle" in url:
        return jobs

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)  # המתנה קלה לטעינת אלמנטים דינמיים
            
            soup = BeautifulSoup(page.content(), 'html.parser')
            browser.close()
            
            # חיפוש אלמנטים עם קלאסים שמזכירים משרות
            found_elements = soup.find_all(['a', 'h3', 'h4', 'span'], class_=re.compile(r'job|position|career|title', re.I))
            
            for el in found_elements:
                text = el.get_text(strip=True)
                # סינון חכם של כותרות משרות רלוונטיות מהתחום הטכנולוגי/ניהולי
                if 5 < len(text) < 60 and any(kw in text.lower() for kw in ['engineer', 'developer', 'manager', 'specialist', 'analyst', 'vp', 'lead', 'expert', 'architect', 'product']):
                    link = url
                    if el.name == 'a' and el.get('href'):
                        link = el.get('href') if el.get('href').startswith('http') else url.rstrip('/') + '/' + el.get('href').lstrip('/')
                    
                    jobs.append({
                        "title": text,
                        "location": "Check Website",
                        "url": link
                    })
            
            # הסרת כפילויות מקומיות
            jobs = [dict(t) for t in {tuple(d.items()) for d in jobs}]
    except Exception as e:
        print(f"Error custom scanning {url}: {e}")
    return jobs

# ==========================================
# הפונקציה המרכזית
# ==========================================

def main():
    # ניסיון לטעון את קובץ החברות
    try:
        with open('companies.json', 'r', encoding='utf-8') as f:
            companies = json.load(f)
    except Exception as e:
        with open("README.md", "w", encoding='utf-8') as f:
            f.write(f"# Error reading companies.json\n{e}")
        return

    # בניית התוכן של ה-README
    content = "# 🛠️ דוח אבחון תקלות ומשרות עדכניות\n\n"
    content += f"**זמן הרצה אחרון:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    content += "| חברה | משרה | מיקום (כפי שהתקבל) | קישור |\n"
    content += "|---|---|---|---|\n"
    
    debug_log = "\n\n### 🔍 לוג בדיקה והתקדמות הסריקה:\n"

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
                    jobs.append({
                        "title": j['title'],
                        "location": j.get('location', {}).get('name', 'Unknown'),
                        "url": j['absolute_url']
                    })
                    
            elif comp_type == 'comeet' and comp_id:
                raw_jobs = fetch_comeet(comp_id)
                for j in raw_jobs:
                    jobs.append({
                        "title": j['name'],
                        "location": j.get('location', {}).get('name', 'Unknown'),
                        "url": j.get('url_active_page') or comp_url
                    })
                    
            elif comp_type == 'lever' and comp_id:
                raw_jobs = fetch_lever(comp_id)
                for j in raw_jobs:
                    jobs.append({
                        "title": j['text'],
                        "location": j.get('categories', {}).get('location', 'Unknown'),
                        "url": j['hostedUrl']
                    })

            elif comp_type == 'ashby' and comp_id:
                raw_jobs = fetch_ashby(comp_id)
                for j in raw_jobs:
                    jobs.append({
                        "title": j.get('title'),
                        "location": j.get('location', 'Unknown'),
                        "url": j.get('jobUrl')
                    })

            elif comp_type == 'bamboohr' and comp_id:
                jobs = fetch_bamboohr(comp_id) # הפונקציה כבר מחזירה פורמט אחיד
                
            elif comp_type == 'custom' or (comp_url and not comp_id):
                # תמיכה באתרים עצמאיים (כמו BioCatch) באמצעות Playwright
                raw_jobs = fetch_custom_site(comp_url)
                for j in raw_jobs:
                    jobs.append({
                        "title": j['title'],
                        "location": j['location'],
                        "url": j['url']
                    })

            debug_log += f"- **{comp_name}** ({comp_type or 'custom'}): נמצאו {len(jobs)} משרות.\n"

            # הוספה לטבלת ה-README
            for job in jobs:
                # הוספנו עמודת קישור לטבלה כדי שיהיה קל ללחוץ ולהגיע למשרה
                content += f"| {comp_name} | {job['title']} | {job['location']} | [הגש מועמדות]({job['url']}) |\n"

        except Exception as e:
            debug_log += f"- **{comp_name}**: שגיאה במהלך הסריקה - {e}\n"

    # שמירה ועדכון ה-README.md
    full_content = content + debug_log
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(full_content)

if __name__ == "__main__":
    main()
