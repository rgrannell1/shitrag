import puppeteer from "puppeteer";
import sqlite3 from "promised-sqlite3";

function daysInMonth(year, month) {
  return new Date(year, month, 0).getDate();
}

const ENDPOINT = process.env.SHITRAG_ENDPOINT;
if (!ENDPOINT) {
  console.error('🗞️ | ENDPOINT not provided');
  process.exit(1);
}

const SHITRAG_DB = process.env.SHITRAG_DB;
if (!SHITRAG_DB) {
  console.error('🗞️ | SHITRAG_DB not provided');
  process.exit(1);
}

const USER_AGENT =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3312.0 Safari/537.36"';

async function* fetchHeadlines(url, year, month, day) {
  if (url.includes('undefined')) {
    throw new Error('undefined in ' + url);
  }

  const args = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-infobars",
    "--window-position=0,0",
    "--ignore-certifcate-errors",
    "--ignore-certifcate-errors-spki-list",
    `--user-agent="${USER_AGENT}"`,
  ];

  const options = {
    args,
    headless: true,
    ignoreHTTPSErrors: true,
    userDataDir: "./tmp",
  };

  const browser = await puppeteer.launch(options);
  const page = await browser.newPage();

  try {
    await page.goto(url, { waitUntil: "networkidle2" });
  } catch (err) {
    throw new Error(`🗞️ | Failed to fetch ${url}`, {cause: err});
    await browser.close();
    return;
  }

  const links = await page.$$(".archive-articles a");

  for (const link of links) {
    const title = await link.evaluate((node) => node.textContent);
    const href = await link.evaluate((node) => node.getAttribute("href"));
    yield { year, month, day, title, href };
  }

  await browser.close();
}

async function insertPages(db) {
  const currentYear = new Date().getFullYear();
  const currentMonth = new Date().getMonth() + 1;
  const currentDay = new Date().getDate();

  for (let year = currentYear; year >= 1994; year--) {
    for (let month = 1; month <= 12; month++) {
      const days = daysInMonth(year, month);

      for (let day = 1; day <= days; day++) {
        if (year === currentYear && month >= currentMonth && day > currentDay) {
          continue;
        }

        const monthString = `${month}`.padStart(2, "0");
        const dayString = `${day}`.padStart(2, "0");

        const url =
          `${ENDPOINT}${year}${monthString}${dayString}.html`;

        await db.run(
          "insert or ignore into page values (?, ?, ?, ?, ?)",
          url,
          "NOT_SAVED",
          year,
          month,
          day,
        );
      }
    }
  }
}

async function insertPageHeadlines(db, href, year, month, day) {
  for await (const headline of fetchHeadlines(href, year, month, day)) {
    await db.run(
      "insert or ignore into headline values (?, ?, ?, ?, ?, ?)",
      href,
      headline.href,
      headline.title,
      headline.year,
      headline.month,
      headline.day,
    );
  }

  await db.run('update page set status = "SAVED" where id = ?', href);
}

async function retrieveHeadlines(db) {
  const rows = await db.all(
    'select id, year, month, day from page where status = "NOT_SAVED"',
  );

  for (const row of rows) {
    const { id, year, month, day } = row;

    console.log(`🗞️ | Scraping the shitrrag for ${year}-${month}-${day}`);

    await insertPageHeadlines(db, id, year, month, day);

    console.clear();
  }
}

const PAGE_TABLE = `
create table if not exists page (
  id        text primary key not null,
  status    text not null,
  year      integer not null,
  month     integer not null,
  day       integer not null
  );
  `;
const HEADLINE_TABLE = `
  create table if not exists headline (
    archive  text not null,
    href     text not null,
    title    text not null,
    year     integer not null,
    month    integer not null,
    day      integer not null
    );
  `;
const TITLE_TABLE = `
  create virtual table if not exists title_fts using fts5 (
    title
  );
  `;

const db = new sqlite3.PromisedDatabase();
await db.open(SHITRAG_DB);

await db.run(PAGE_TABLE);
await db.run(HEADLINE_TABLE);
await db.run(TITLE_TABLE);

await insertPages(db);
await retrieveHeadlines(db);

await db.run(`
insert into title_fts select title from headline;
`);
