
## Model

The classification model is based on the pretrained [XLM-RoBERTa](https://huggingface.co/FacebookAI/xlm-roberta-base) model, which has been
[fine-tuned in Google Colab](https://colab.research.google.com/drive/1VDhGyNRNagAKRrjhcfAQ5bo7VLIwDpjr?usp=sharing). This fine-tuning process can also be replicated locally with the same code.

For fine-tuning a collection of labelled crawled texts is being used from domains that were reported in [web-bugs](https://github.com/webcompat/web-bugs/issues) repository. All texts are located in `unsupported_max_256.json` 

## Install dependencies

NOTE: When installing on MacOS with M1 Chip, make sure to install these dependencies using Rosetta terminal.

```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

In addition, a PostgreSQL database server needs to be set up and running locally.

## Data source and tables

For the top 100k I've used CrUX data and created a temporary table:

```
CREATE OR REPLACE TABLE `cr-ux-366917.test.global_100k_jan_2024` AS
SELECT
  DISTINCT origin, experimental.popularity.rank as rank
FROM
  `chrome-ux-report.all.202401`
WHERE experimental.popularity.rank <= 100000;
```

Example tables/scripts to create and import data are located in `postgres.py`.


## Crawling and classifying scripts

The scripts are intended to run in parallel in separate terminals (crawling is faster than classifying)

### Start crawling script

```sh
python3 crawl_global.py
```

### Start classifying script

```sh
python3 classify_global.py
```
