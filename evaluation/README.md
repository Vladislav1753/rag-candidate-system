# Evaluation System

This directory contains tools for evaluating the quality of the RAG candidate search system.

## 📁 Structure

- `test_queries.py` - Generation of synthetic test queries based on real data
- `metrics.py` - Implementation of quality metrics (Precision, Recall, MRR, NDCG, MAP)
- `run_evaluation.py` - Main script for running the evaluation
- `generate_report.py` - Generation of an HTML report with visualization

## 🚀 Quick Start

### 1. Generating Test Queries

```bash
python evaluation/test_queries.py

```

The script will create the `evaluation/test_queries.json` file with synthetic queries generated based on real candidates in the database.

**Query Generation Strategies:**

* By profession (title) and experience
* By skills
* By location + profession
* Complex queries (profession + multiple skills)

### 2. Running the Evaluation

```bash
python evaluation/run_evaluation.py

```

The script will perform:

* Loading of test queries
* Candidate search WITHOUT reranker
* Candidate search WITH reranker
* Calculation of quality metrics
* Comparison of results
* Saving results to JSON

**Results are saved in:** `evaluation/results/evaluation_report.json`

### 3. Generating the HTML Report

```bash
python evaluation/generate_report.py

```

Creates a beautiful HTML report with:

* Interactive charts (Plotly)
* Metric comparison table
* Visualization of improvements

**The report is available at:** `evaluation/results/evaluation_report.html`

## 📊 Metrics

### Precision@K

The fraction of relevant documents among the top-K results.

```
Precision@K = (Relevant in top-K) / K

```

### Recall@K

The fraction of found relevant documents out of all relevant documents.

```
Recall@K = (Relevant in top-K) / (Total Relevant)

```

### MRR (Mean Reciprocal Rank)

The average inverse rank of the first relevant document.

```
MRR = (1 / N) * Σ (1 / rank_i)

```

where `rank_i` is the position of the first relevant result for query i.

### NDCG@K (Normalized Discounted Cumulative Gain)

Ranking quality metric taking into account the positions of relevant documents.

```
NDCG@K = DCG@K / IDCG@K

```

### MAP@K (Mean Average Precision)

The mean average precision across all queries, considering the order of relevant results.

## 🎯 Usage Example

### Full evaluation cycle:

```bash
# 1. Generate test queries (done once)
python evaluation/test_queries.py

# 2. Run evaluation
python evaluation/run_evaluation.py

# 3. Generate HTML report
python evaluation/generate_report.py

# 4. Open the report in a browser
start evaluation/results/evaluation_report.html  # Windows

```

## 📝 test_queries.json Format

```json
[
  {
    "query": "Senior Python Developer with 5+ years experience",
    "relevant_candidates": ["uuid-1", "uuid-2", "uuid-3"],
    "description": "Search by title and experience: Python Developer",
    "filters": {
      "location": "San Francisco",
      "min_experience": 5
    }
  }
]

```

## 🔧 Configuration

### Changing the Number of Results

In `run_evaluation.py`:

```python
# Change top_k
k_values = [1, 3, 5, 10]  # Default is [1, 3, 5]

```

### Changing the Reranker Model

In `run_evaluation.py`:

```python
reranker = RerankerService(model_name="cross-encoder/ms-marco-MiniLM-L-12-v2")

```

## 📈 Interpreting Results

* **MRR > 0.7** - excellent, relevant results are at the top
* **NDCG@5 > 0.6** - good ranking quality
* **MAP@5 > 0.5** - the system works satisfactorily
* **Improvement > 10%** - reranker significantly improves results

## 🐛 Troubleshooting

### Database Connection Error

Ensure that:

1. The database is running (`docker compose up -d`)
2. Environment variables in `.env` are correct
3. The database contains candidates for testing

### Few Test Queries

Increase the limit in `test_queries.py`:

```python
rows = await conn.fetch("""...""" LIMIT 100)  # Was 50

```

## 📚 Additional Information

* [Information Retrieval Metrics](https://en.wikipedia.org/wiki/Evaluation_measures_(information_retrieval))
* [Cross-Encoders for Reranking](https://www.sbert.net/examples/applications/cross-encoder/README.html)
