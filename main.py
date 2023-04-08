
import sqlite3

import os
import re
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from typing import Generator

STOP_WORDS = set(stopwords.words('english'))
SHITRAG_DB = os.getenv('SHITRAG_DB')

def preprocess_headline(headline: str) -> Generator[str, None, None]:
    tokens = [token.lower() for token in word_tokenize(headline)]

    # Remove stopwords
    tokens = [token for token in tokens if token not in STOP_WORDS]

    # Lemmatization
    lemmatizer = WordNetLemmatizer()
    lemmatized_tokens = [lemmatizer.lemmatize(token) for token in tokens]

    for token in lemmatized_tokens:
        subbed = (
            token
                .replace('"', '')
                .replace("'", '')
        )

        if re.search(r'^[a-zA-Z0-9\.]+$', subbed):
            yield subbed

def read_headlines():
    conn = sqlite3.connect('/home/rg/shitrag.db')
    cursor = conn.cursor()

    for row in cursor.execute('select title from headline'):
        yield row

dicts = {}

idx = 0

for headline in read_headlines():
    idx += 1

    if idx % 1000 == 0:
        print("\033c", end="")
        print(idx)

    eep = list(preprocess_headline(headline[0]))

    for word in eep:
        if word not in dicts:
            dicts[word] = 0

        dicts[word] += 1

# get top 100 words
top_words = sorted(dicts.items(), key=lambda x: x[1], reverse=True)[:100]
print(top_words)