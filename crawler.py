import sys
import time
import json
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Creo un set: https://docs.python.org/3/tutorial/datastructures.html#sets
# Questo mi permette di aggiungere in tempo O1 (nei casi pratici)
# e verificare la presenza di una chiave sempre in tempo 01.
# Posso fare lo stesso usando i dict, mentre le liste sono
# molto meno efficienti (On per la verifica)
ignored = {
    "index.html",
    "https://books.toscrape.com/index.html",
}

# L'URL da cui partire
base_url = "https://books.toscrape.com/"

financial_keys = (
    'Price (excl. tax)',
    'Price (incl. tax)',
    'Tax'
)
numerical_keys = (
    "Number of reviews",
)

data = []


def get_parent_url(url):
    """Get the parent of the given URL

    e.g. https://www.example.com/abc/cde.html -> https://www.example.com/abc/
    """
    *parent_parts, _ = url.split("/")
    return "/".join(parent_parts)


def rows_to_dict(rows):
    """Convert a sequence of rows of an HTML table to a dict"""
    rows_data = {el.th.text: el.td.text for el in rows}
    for key, val in rows_data.items():
        if key in financial_keys:
            # Correggi il dato e lo trasformo in decimale
            # 'Â£51.77' -> 51.77
            # Per farlo escludo i primi due caratteri
            rows_data[key] = float(val[2:])
        if key in numerical_keys:
            # Converti il dato in un numero intero
            rows_data[key] = int(val)
    return rows_data

def crawl(url):
    """Crawl the page at the given URL
    Any tables will be added as dicts to the
    module-level name "data".

    Perform the crawl using the breadth-first
    algorithm (BFS).
    """

    # Prendo la URL base
    parent_url = get_parent_url(url)

    # Invio una chiamata GET usando l'URL
    response = requests.get(url)

    status_code = response.status_code
    if status_code != 200:
        raise Exception(f"Il server ha risposto con uno status code inaspettato: {status_code}")

    # Faccio il parsing del HTML della pagina
    soup = BeautifulSoup(response.text, features="html.parser")

    # Cerco tutti gli element tr (table row) nella pagina (se ci sono)
    rows = soup.find_all("tr")

    # Se li trovo, li converto in un dict e li aggiungo ai dati
    row_data = rows_to_dict(rows)
    if row_data:
        data.append(row_data)
        # Aspetto un secondo prima di proseguire
        # in modo da non caricare troppo il server
        time.sleep(1)

    # Ora cerco tutti i link all'interno della prima sezione della pagina
    links = soup.find_all("section")[0].find_all("a")
    print(f"Crawled: {url} and found {len(links)} new links and {len(rows)} table rows.", file=sys.stderr)
    for link in links:
        # Prendo il link (nell'attributo HREF)
        link_rel = link.attrs["href"]

        # Ignora i link che tornano indietro
        if ".." in link_rel:
            continue

        # Se non è un link assoluto (che comincia con "http")...
        if not link_rel.startswith("http"):
            # ... lo rendo assoluto usando la URL base
            url = "/".join([parent_url, link_rel])
        else:
            url = link_rel

        # I link esterni vanno ignorati
        if not url.startswith(base_url):
            continue

        # Se ho già incontrato il link, lo ignoro
        if url in ignored:
            continue

        # Aggiungo la URL alla lista da ignorare
        ignored.add(url)

        # Chiamata ricorsiva
        crawl(url)


# Faccio partire il crawl
try:
    crawl(base_url)
except KeyboardInterrupt:
    pass

# Creo e stampo il dataframe
df = pd.DataFrame(data)
print(df)

# Salvo i dati JSON in un file per poterli utilizzare dopo
with open("books.json", "w") as fd:
    fd.write(json.dumps(data))