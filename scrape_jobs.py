import requests
import json
from datetime import datetime

# --- פונקציות למשיכת משרות ---

def fetch_greenhouse(company_id):
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_id}/jobs"
    try:
        response = requests.get(url)
        if response.status_code != 200: return []
        jobs = []
        for j in response.json().get('jobs', []):
            jobs.append({
                "title": j['title'],
                "location": j.get('location', {}).get('name', ''),
                "url": j['absolute_url']
            })
        return jobs
    except: return []

def fetch_comeet(company_id):
    url = f"https://www.comeet.co/careers-api/2.0/company/{company_id}/positions?token=&details=true"
    try:
        response = requests.get(url)
        if response.status_code != 200: return []
        jobs = []
        for j in response.json():
            jobs.append({
                "title": j['name'],
                "location": j.get('location', {}).get('name', ''),
                "url": j['url_active_page']
            })
        return jobs
    except: return []

def fetch_lever(company_id):
    url = f"https://api.lever.co/v0/postings/{company_id}"
    try:
        response = requests.get(url)
        if response.status_code != 200: return []
        jobs = []
        for j in response.json():
            jobs.append({
                "title": j['text'],
                "location": j.get('categories', {}).get('location', ''),
                "url": j['hostedUrl']
            })
        return jobs
    except: return []

# --- הלוגיקה הראשית ---

def main():
    try:
        with open('companies.json', 'r') as f:
            companies = json.load(f)
    except:
        print("Could not load companies.json")
        return

    markdown_content = "# 🦄 לוח משרות הייטק (ישראל)\n"
    markdown_content += f"**עודכן לאחרונה:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
    markdown_content += "| חברה | משרה | מיקום | לינק |\n"
    markdown_content += "|---|---|---|---|\n"

    for company in companies:
        print(f"Scraping {company['name']}...")
        jobs = []
        
        if company['type'] == 'greenhouse':
            jobs = fetch_greenhouse(company['id'])
        elif company['type'] == 'comeet':
            jobs = fetch_comeet(company['id'])
        elif company['type'] == 'lever':
            jobs = fetch_lever(company['id'])

        for job in jobs:
            # סינון חכם לישראל
            loc = job['location'].lower()
            if 'israel' in loc or 'tel aviv' in loc or 'herzliya' in loc or 'haifa' in loc or 'jerusalem' in loc or 'ישראל' in loc:
                markdown_content += f"| {company['name']} | {job['title']} | {job['location']} | [לינק]({job['url']}) |\n"

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    print("Done!")

if __name__ == "__main__":
    main()
