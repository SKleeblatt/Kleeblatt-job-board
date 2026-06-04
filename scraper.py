import json
import os
import re
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

COMPANIES_FILE = "companies.json"
OUTPUT_FILE = "jobs_output.json"

def extract_slug_from_url(url, pattern):
    """מחלץ את מזהה החברה (Slug) מתוך כתובת ה-URL"""
    match = re.search(pattern, url, re.IGNORECASE)
    if match:
        return match.group(1).split('/')[0].split('?')[0]
    return None

# ==========================================
# סקרייפרים מבוססי API (מהירים ויציבים)
# ==========================================

def scrape_comeet(url, company_name):
    # דוגמה לקישור: https://www.comeet.com/jobs/buildots/36.004
    # ה-pattern תופס את מה שאחרי jobs/
    company_id = extract_slug_from_url(url, r"comeet\.com/jobs/([^/]+)")
    if not company_id:
        return []
        
    jobs = []
    api_url = f"https://www.comeet.com/v1.0/c/{company_id}/competitions"
    try:
        res = requests.get(api_url, timeout=10)
        if res.status_code == 200:
            for pos in res.json():
                jobs.append({
                    "company": company_name,
                    "title": pos.get("name"),
                    "location": pos.get("location", {}).get("name", "Unknown"),
                    "link": f"https://www.comeet.com/jobs/{company_id}/{pos.get('uid')}",
                    "department": pos.get("department", ""),
                    "source": "Comeet"
                })
    except Exception as e:
        print(f"[-] Error Comeet ({company_name}): {e}")
    return jobs

def scrape_greenhouse(url, company_name):
    # דוגמה לקישור: https://job-boards.greenhouse.io/similarweb
    company_id = extract_slug_from_url(url, r"greenhouse\.io/([^/]+)")
    if not company_id:
        return []
        
    jobs = []
    # לגרסה החדשה והישנה של Greenhouse יש API ציבורי זהה
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{company_id}/jobs"
    try:
        res = requests.get(api_url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for pos in data.get("jobs", []):
                jobs.append({
                    "company": company_name,
                    "title": pos.get("title"),
                    "location": pos.get("location", {}).get("name", "Unknown"),
                    "link": pos.get("absolute_url"),
                    "department": pos.get("departments", [{}])[0].get("name", "") if pos.get("departments") else "",
                    "source": "Greenhouse"
                })
    except Exception as e:
        print(f"[-] Error Greenhouse ({company_name}): {e}")
    return jobs

def scrape_lever(url, company_name):
    # דוגמה לקישור: https://jobs.lever.co/lendbuzz או jobs.eu.lever.co
    company_id = extract_slug_from_url(url, r"lever\.co/([^/]+)")
    if not company_id:
        return []
        
    jobs = []
    api_url = f"https://api.lever.co/v0/postings/{company_id}?mode=json"
    try:
        res = requests.get(api_url, timeout=10)
        if res.status_code == 200:
            for post in res.json():
                jobs.append({
                    "company": company_name,
                    "title": post.get("text"),
                    "location": post.get("categories", {}).get("location", "Unknown"),
                    "link": post.get("hostedUrl"),
                    "department": post.get("categories", {}).get("team", ""),
                    "source": "Lever"
                })
    except Exception as e:
        print(f"[-] Error Lever ({company_name}): {e}")
    return jobs

def scrape_ashby(url, company_name):
    # דוגמה לקישור: https://jobs.ashbyhq.com/honeybook
    company_id = extract_slug_from_url(url, r"ashbyhq\.com/([^/]+)")
    if not company_id:
        return []
        
    jobs = []
    api_url = "https://api.ashbyhq.com/react-api/v1/widgets/embed"
    try:
        res = requests.post(api_url, json={"organizationId": company_id}, timeout=10)
        if res.status_code == 200:
            for post in res.json().get("jobPostings", []):
                jobs.append({
                    "company": company_name,
                    "title": post.get("title"),
                    "location": post.get("location"),
                    "link": post.get("jobUrl"),
                    "department": post.get("department"),
                    "source": "Ashby"
                })
    except Exception as e:
        print(f"[-] Error Ashby ({company_name}): {e}")
    return jobs

def scrape_bamboohr(url, company_name):
    # דוגמה לקישור: https://solitics.bamboohr.com/careers
    company_id = extract_slug_from_url(url, r"([^/.]+)\.bamboohr\.com")
    if not company_id:
        return []
        
    jobs = []
    api_url = f"https://{company_id}.bamboohr.com/jobs/embed2.php"
    try:
        res = requests.get(api_url, timeout=10)
        if res.status_code == 200:
            # BambooHR מחזירה לעיתים קרובות JSON מוטמע בתוך מבנה פנימי, או שניתן לקרוא את ה-API הציבורי שלהם
            soup = BeautifulSoup(res.text, 'html.parser')
            # חילוץ ישיר מה-DOM של ה-Embed
            for row in soup.select('.BambooHR-ATS-Jobs-Item a'):
                jobs.append({
                    "company": company_name,
                    "title": row.get_text(strip=True),
                    "location": "Israel/Remote",
                    "link": f"https://{company_id}.bamboohr.com/careers/" + row.get('href').split('=')[-1],
                    "department": "Unknown",
                    "source": "BambooHR"
                })
    except Exception as e:
        print(f"[-] Error BambooHR ({company_name}): {e}")
    return jobs

# ==========================================
# סקרייפר גנרי לאתרים עצמאיים (Playwright)
# ==========================================

def scrape_fallback_site(url, company_name):
    """
    כאשר האתר אינו משתמש ב-ATS מוכר, נשתמש בדפדפן עצמאי
    כדי לנסות לחלץ כותרות וקישורים שנראים כמו משרות.
    """
    jobs = []
    # נמנע מסריקת לינקדאין או גוגל פורמס בשלב זה כדי לא להיחסם
    if "linkedin.com" in url or "forms.gle" in url:
        print(f"[!] Skipping social/form link for {company_name}: {url}")
        return jobs

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            
            # טעינת האתר עם התחשבות בביצועים
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000) # המתנה קלה לאלמנטים דינמיים
            
            soup = BeautifulSoup(page.content(), 'html.parser')
            browser.close()
            
            # מחפשים אלמנטים נפוצים של כותרות משרות (קישורים בתוך רשימות, כותרות h3/h4)
            found_elements = soup.find_all(['a', 'h3', 'h4', 'span'], class_=re.compile(r'job|position|career|title', re.I))
            
            for el in found_elements:
                text = el.get_text(strip=True)
                # סינון טקסטים קצרים מדי או ארוכים מדי או מילים לא רלוונטיות
                if 5 < len(text) < 60 and any(keyword in text.lower() for keyword in ['engineer', 'developer', 'manager', 'specialist', 'analyst', 'vp', 'lead', 'expert', 'architect']):
                    link = url
                    if el.name == 'a' and el.get('href'):
                        link = el.get('href') if el.get('href').startswith('http') else url.rstrip('/') + '/' + el.get('href').lstrip('/')
                    
                    jobs.append({
                        "company": company_name,
                        "title": text,
                        "location": "Check website",
                        "link": link,
                        "department": "General",
                        "source": "Custom / Playwright Scan"
                    })
                    
            # הסרת כפילויות מקומיות
            jobs = [dict(t) for t in {tuple(d.items()) for d in jobs}]
    except Exception as e:
        print(f"[-] Error Playwright Fallback ({company_name}): {e}")
    return jobs

# ==========================================
# פונקציה מרכזית (Main Loop)
# ==========================================

def main():
    if not os.path.exists(COMPANIES_FILE):
        print(f"[X] {COMPANIES_FILE} not found! Please make sure it exists.")
        return
        
    with open(COMPANIES_FILE, "r", encoding="utf-8") as f:
        companies_data = json.load(f)
        
    all_discovered_jobs = []
    
    print(f"[+] Loaded {len(companies_data)} companies. Starting automation...")
    
    for company in companies_data:
        name = company.get("name")
        url = company.get("careers_url") or company.get("url") # וידוא תאימות למפתח שלך ב-JSON
        
        if not url:
            print(f"[!] No URL found for {name}, skipping.")
            continue
            
        print(f"\n[*] Processing: {name} | {url}")
        jobs_found = []
        
        # זיהוי המערכת לפי ה-URL והפעלת המנגנון הנכון
        if "comeet.com" in url:
            jobs_found = scrape_comeet(url, name)
        elif "greenhouse.io" in url:
            jobs_found = scrape_greenhouse(url, name)
        elif "lever.co" in url:
            jobs_found = scrape_lever(url, name)
        elif "ashbyhq.com" in url:
            jobs_found = scrape_ashby(url, name)
        elif "bamboohr.com" in url:
            jobs_found = scrape_bamboohr(url, name)
        else:
            # אם החברה משתמשת באתר עצמאי, ננסה לסרוק אותו באופן חכם
            jobs_found = scrape_fallback_site(url, name)
            
        print(f"[✓] Found {len(jobs_found)} jobs for {name}")
        all_discovered_jobs.extend(jobs_found)

    # שמירת כל הדאטה שהצטבר בקובץ פלט אחד מסודר
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_discovered_jobs, f, indent=4, ensure_ascii=False)
        
    print(f"\n[+++] Success! Total of {len(all_discovered_jobs)} jobs written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
