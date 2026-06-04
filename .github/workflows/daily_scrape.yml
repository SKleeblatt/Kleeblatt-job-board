name: Update Job List

on:
  schedule:
    - cron: '0 8 * * *'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-latest
    
    env:
      FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: 'true'

    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0 # מביא את כל ההיסטוריה כדי למנוע התנגשויות

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Install Playwright Browsers
        run: python -m playwright install --with-deps chromium

      - name: Run scraping script
        run: python scrape_jobs.py

      # במקום התוסף שנכשל, אנחנו מריצים פקודות גיט ישירות ומאלצים דחיקה (Force Push)
      - name: Commit and Push changes manually
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"
          
          # הוספת קובץ ה-README ותיקיית jobs למעקב
          git add README.md jobs/*.md || true
          
          # בדיקה האם בכלל יש שינויים שצריך לעדכן
          if git diff --staged --quiet; then
            echo "No changes to commit"
          else
            git commit -m "Updated job board and categories automatically"
            # פקודת הקסם: מאלצת את השרת לקבל את השינויים ודורסת את חוסר הסנכרון
            git push origin main --force
          fi
