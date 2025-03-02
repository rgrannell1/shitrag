
doc = """Usage:
  analyse.py compute_embeddings
  analyse.py compute_headline_clusters
  analyse.py compute_cluster_topics

Options:
  -h --help     Show this screen.
"""

import json
import sqlite3
import concurrent
import hdbscan
import numpy as np
from ollama import embed
from sklearn.manifold import TSNE
from docopt import docopt
db = sqlite3.connect('shitrag-py.db')

MODEL = 'deepseek-r1:1.5b'

def read_embeddings():
  """Read embedding data from the database"""

  cursor = db.cursor()
  cursor.execute("select href, embedding from embeddings")

  for href, embedding in cursor.fetchall():
    yield href, json.loads(embedding)[0]


def read_headlines(no_embeddings=False):
  """Read headline data from the database"""

  cursor = db.cursor()

  if no_embeddings:
    cursor.execute("select href, title from headline where href not in (select href from embeddings)")
  else:
    cursor.execute("select href, title from headline")

  for href, title in cursor.fetchall():
    yield href, title

def compute_embeddings():
  """Compute LLM embeddings for each headline"""

  def process_headline(headline):
      res = embed(model=MODEL, input=headline)
      embeddings = res['embeddings']
      return (headline[0], json.dumps(embeddings), MODEL)

  def insert_embeddings(results):
      cursor = db.cursor()
      cursor.executemany("""
          INSERT INTO embeddings (href, embedding, model)
          VALUES (?, ?, ?)
      """, results)
      db.commit()

  headlines = list(read_headlines(no_embeddings=True))
  batch_size = 10

  with concurrent.futures.ThreadPoolExecutor() as executor:
      for i in range(0, len(headlines), batch_size):
          print(f'running batch {i/batch_size} (computed {i} embeddings)')
          batch = headlines[i:i+batch_size]
          results = list(executor.map(process_headline, batch))
          insert_embeddings(results)





def compute_headline_clusters():
  """Compute and save clusters based on a reduced-dimension embedding space.
  These clusters than then be used when topic modelling"""

  data = list(read_embeddings())

  embeddings_data = np.array([datum[1] for datum in data])

  tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, len(embeddings_data) - 1))
  embeddings_lower_dim = tsne.fit_transform(embeddings_data)
  clusterer = hdbscan.HDBSCAN(min_cluster_size=50, gen_min_span_tree=True)
  labels = clusterer.fit_predict(embeddings_lower_dim)

  for label, data in zip(labels, data):
    href = data[0]

    cursor = db.cursor()
    cursor.execute("""
    insert into clusters (href, cluster)
    values (?, ?)
    """, (href, label))
    db.commit()


def compute_cluster_topics():
  """Compute topics for each cluster"""

  pass


if __name__ == '__main__':
    arguments = docopt(doc)

    if arguments['compute_embeddings']:
        compute_embeddings()
    elif arguments['compute_headline_clusters']:
        compute_headline_clusters()
    elif arguments['compute_cluster_topics']:
        compute_cluster_topics()
