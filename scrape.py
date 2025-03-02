import os
import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime

SHITRAG_DB = os.getenv('SHITRAG_DB')
if not SHITRAG_DB:
    raise ValueError('SHITRAG_DB is not set')

ENDPOINT = os.getenv('SHITRAG_ENDPOINT')
if not ENDPOINT:
    raise ValueError('SHITRAG_ENDPOINT is not set')

def days_in_month(year, month):
    """Return the number of days in the given month of the given year."""
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)

    return (next_month - datetime(year, month, 1)).days

conn = sqlite3.connect(SHITRAG_DB)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS page (
  id TEXT PRIMARY KEY NOT NULL,
  status TEXT NOT NULL,
  year INTEGER NOT NULL,
  month INTEGER NOT NULL,
  day INTEGER NOT NULL
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS headline (
  archive TEXT NOT NULL,
  href TEXT NOT NULL,
  title TEXT NOT NULL,
  year INTEGER NOT NULL,
  month INTEGER NOT NULL,
  day INTEGER NOT NULL
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS embeddings (
  href TEXT NOT NULL,
  embedding TEXT NOT NULL,
  model TEXT NOT NULL
);
""")

def fetch_headlines(url, year, month, day):
    """Fetch headlines from the given URL and yield them."""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.select('.archive-articles a')

    for link in links:
        href = link.get('href')
        title = link.get_text()
        yield {'year': year, 'month': month, 'day': day, 'title': title, 'href': href}

def insert_pages():
    """Insert pages into the database."""
    current_year = datetime.now().year
    current_month = datetime.now().month
    current_day = datetime.now().day

    for year in range(current_year, 1994, -1):
        for month in range(1, 13):
            days = days_in_month(year, month)
            for day in range(1, days + 1):
                if year == current_year and month == current_month and day > current_day:
                    continue

                month_str = f'{month:02}'
                day_str = f'{day:02}'
                url = f'{ENDPOINT}{year}{month_str}{day_str}.html'
                cursor.execute("INSERT OR IGNORE INTO page (id, status, year, month, day) VALUES (?, 'NOT_SAVED', ?, ?, ?)", (url, year, month, day))
                conn.commit()


def insert_page_headlines(url, year, month, day):
    """Insert headlines into the database."""
    pages = 0
    for headline in fetch_headlines(url, year, month, day):
        cursor.execute("INSERT OR IGNORE INTO headline VALUES (?, ?, ?, ?, ?, ?)", (url, headline['href'], headline['title'], year, month, day))
        pages += 1
    cursor.execute("UPDATE page SET status = 'SAVED' WHERE id = ?", (url,))
    conn.commit()
    return pages

def retrieve_headlines():
    """Retrieve headlines from pages marked as 'NOT_SAVED'."""
    cursor.execute("SELECT * FROM page WHERE status = 'NOT_SAVED'")
    rows = cursor.fetchall()
    pages = 0

    print('📰 | Scraping headlines from the shitrag')

    for row in rows:
        id, _, year, month, day = row

        # if the month is in the future, skip it
        if datetime(year, month, day) > datetime.now():
            continue

        print(f'🗞️ | Scraping the trash published on {year}-{month}-{day} | Collected {pages} headlines ({id})')
        pages += insert_page_headlines(id, year, month, day)

insert_pages()
retrieve_headlines()

conn.commit()
conn.close()
