import requests
import json
from datetime import datetime

def fetch_greenhouse(company_id):
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_id}/jobs"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get('jobs', [])
    except: pass
    return []

def fetch_comeet(company_id):
    url = f"https://www.comeet.co/careers-api/2.0/company/{company_id}/positions?token=&details=true"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
    except: pass
    return []

def fetch_lever(company_id):
    url = f"https://api.lever.co/v0/postings/{company_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
    except: pass
    return []

def main():
    # ניסיון לטעון את קובץ החברות
    try:
        with open('companies.json', 'r') as f:
            companies = json.load(f)
    except Exception as e:
        with open("README.md", "w") as f:
            f.write(f"# Error reading companies.json\n{e}")
        return

    # בניית התוכן
    content = "# 🛠️ דוח אבחון תקלות\n\n"
    content += f"**זמן הרצה:** {datetime.now().strftime('%H:%M')}\n\n"
    content += "| חברה | משרה | מיקום (כפי שהתקבל) |\n"
    content += "|---|---|---|\n"
    
    debug_log = "\n\n### 🔍 לוג בדיקה:\n"

    for company in companies:
        jobs = []
        try:
            if company['type'] == 'greenhouse':
                raw_jobs = fetch_greenhouse(company['id'])
                # המרה לפורמט אחיד
                for j in raw_jobs:
                    jobs.append({
                        "title": j['title'],
                        "location": j.get('location', {}).get('name', 'Unknown'),
                        "url": j['absolute_url']
                    })
                    
            elif company['type'] == 'comeet':
                raw_jobs = fetch_comeet(company['id'])
                for j in raw_jobs:
                    jobs.append({
                        "title": j['name'],
                        "location": j.get('location', {}).get('name', 'Unknown'),
                        "url": j['url_active_page']
                    })
                    
            elif company['type'] == 'lever':
                raw_jobs = fetch_lever(company['id'])
                for j in raw_jobs:
                    jobs.append({
                        "title": j['text'],
                        "location": j.get('categories', {}).get('location', 'Unknown'),
                        "url": j['hostedUrl']
                    })

            debug_log += f"- **{company['name']}**: נמצאו {len(jobs)} משרות.\n"

            # הוספה לטבלה (בלי סינון!)
            for job in jobs:
                content += f"| {company['name']} | {job['title']} | {job['location']} |\n"

        except Exception as e:
            debug_log += f"- **{company['name']}**: שגיאה - {e}\n"

    # שמירה
    full_content = content + debug_log
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(full_content)

if __name__ == "__main__":
    main()
