"""
Generation of a beautiful HTML report visualizing evaluation results.
"""

import json
from datetime import datetime


def generate_html_report(
    report_json_path: str = "evaluation/results/evaluation_report.json",
):
    """Creates an HTML report with metric visualization."""

    with open(report_json_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    metrics_no_rerank = report["metrics_without_reranker"]
    metrics_with_rerank = report["metrics_with_reranker"]
    improvements = report["improvements_percent"]
    test_count = report["test_queries_count"]

    # Prepare data for charts
    metric_names = list(metrics_no_rerank.keys())
    values_no_rerank = [metrics_no_rerank[m] for m in metric_names]
    values_with_rerank = [metrics_with_rerank[m] for m in metric_names]

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RAG Evaluation Report</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
        }}

        h1 {{
            color: #2d3748;
            font-size: 2.5em;
            margin-bottom: 10px;
            text-align: center;
        }}

        .subtitle {{
            text-align: center;
            color: #718096;
            margin-bottom: 30px;
            font-size: 1.1em;
        }}

        .info-box {{
            background: #f7fafc;
            border-left: 4px solid #4299e1;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 8px;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}

        .metric-card h3 {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 10px;
        }}

        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }}

        .metric-improvement {{
            font-size: 0.9em;
            opacity: 0.9;
        }}

        .improvement-positive {{
            color: #48bb78;
        }}

        .improvement-negative {{
            color: #f56565;
        }}

        .chart-container {{
            margin-bottom: 40px;
            background: #f7fafc;
            padding: 20px;
            border-radius: 15px;
        }}

        .chart-title {{
            font-size: 1.5em;
            color: #2d3748;
            margin-bottom: 15px;
            text-align: center;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}

        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}

        th {{
            background: #4299e1;
            color: white;
            font-weight: 600;
        }}

        tr:hover {{
            background: #f7fafc;
        }}

        .footer {{
            text-align: center;
            margin-top: 40px;
            color: #718096;
            padding-top: 20px;
            border-top: 2px solid #e2e8f0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 RAG System Evaluation Report</h1>
        <div class="subtitle">Performance Comparison: With vs Without Reranker</div>
        <div class="subtitle">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>

        <div class="info-box">
            <strong>📊 Testing Information:</strong><br>
            Total Test Queries: <strong>{test_count}</strong><br>
            Reranker Model: <strong>cross-encoder/ms-marco-MiniLM-L-6-v2</strong><br>
            Top-K Results: <strong>5</strong>
        </div>

        <h2 style="margin-bottom: 20px; color: #2d3748;">📈 Key Metrics</h2>

        <div class="metrics-grid">
            <div class="metric-card">
                <h3>MRR (Mean Reciprocal Rank)</h3>
                <div class="metric-value">{metrics_with_rerank['mrr']:.4f}</div>
                <div class="metric-improvement">
                    <span class="{'improvement-positive' if improvements['mrr'] > 0 else 'improvement-negative'}">
                        {'+' if improvements['mrr'] > 0 else ''}{improvements['mrr']:.2f}% with Reranker
                    </span>
                </div>
            </div>

            <div class="metric-card">
                <h3>MAP@5 (Mean Average Precision)</h3>
                <div class="metric-value">{metrics_with_rerank['map@5']:.4f}</div>
                <div class="metric-improvement">
                    <span class="{'improvement-positive' if improvements['map@5'] > 0 else 'improvement-negative'}">
                        {'+' if improvements['map@5'] > 0 else ''}{improvements['map@5']:.2f}% with Reranker
                    </span>
                </div>
            </div>

            <div class="metric-card">
                <h3>NDCG@5</h3>
                <div class="metric-value">{metrics_with_rerank['ndcg@5']:.4f}</div>
                <div class="metric-improvement">
                    <span class="{'improvement-positive' if improvements['ndcg@5'] > 0 else 'improvement-negative'}">
                        {'+' if improvements['ndcg@5'] > 0 else ''}{improvements['ndcg@5']:.2f}% with Reranker
                    </span>
                </div>
            </div>
        </div>

        <div class="chart-container">
            <div class="chart-title">Metric Comparison: Without vs With Reranker</div>
            <div id="comparisonChart"></div>
        </div>

        <div class="chart-container">
            <div class="chart-title">Metric Improvement with Reranker (%)</div>
            <div id="improvementChart"></div>
        </div>

        <h2 style="margin-top: 40px; margin-bottom: 20px; color: #2d3748;">📋 Detailed Metrics Table</h2>

        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Without Reranker</th>
                    <th>With Reranker</th>
                    <th>Improvement (%)</th>
                </tr>
            </thead>
            <tbody>
"""

    # Add table rows
    for metric in metric_names:
        no_rerank_val = metrics_no_rerank[metric]
        with_rerank_val = metrics_with_rerank[metric]
        improvement = improvements[metric]
        improvement_color = (
            "green" if improvement > 0 else "red" if improvement < 0 else "gray"
        )

        html_content += f"""
                <tr>
                    <td><strong>{metric}</strong></td>
                    <td>{no_rerank_val:.4f}</td>
                    <td>{with_rerank_val:.4f}</td>
                    <td style="color: {improvement_color}; font-weight: bold;">
                        {'+' if improvement > 0 else ''}{improvement:.2f}%
                    </td>
                </tr>
"""

    # JavaScript for charts
    metric_names_json = json.dumps(metric_names)
    values_no_rerank_json = json.dumps(values_no_rerank)
    values_with_rerank_json = json.dumps(values_with_rerank)
    improvements_list = [improvements[m] for m in metric_names]
    improvements_json = json.dumps(improvements_list)

    html_content += f"""
            </tbody>
        </table>

        <div class="footer">
            <p>🚀 AI Recruitment Assistant - RAG System Evaluation</p>
            <p>Powered by LangGraph, OpenAI, and sentence-transformers</p>
        </div>
    </div>

    <script>
        // Metric Comparison Chart
        var trace1 = {{
            x: {metric_names_json},
            y: {values_no_rerank_json},
            name: 'Without Reranker',
            type: 'bar',
            marker: {{
                color: 'rgb(158, 202, 225)',
            }}
        }};

        var trace2 = {{
            x: {metric_names_json},
            y: {values_with_rerank_json},
            name: 'With Reranker',
            type: 'bar',
            marker: {{
                color: 'rgb(102, 126, 234)',
            }}
        }};

        var data = [trace1, trace2];

        var layout = {{
            barmode: 'group',
            yaxis: {{
                title: 'Metric Value',
                range: [0, 1]
            }},
            xaxis: {{
                title: 'Metrics'
            }},
            plot_bgcolor: 'white',
            paper_bgcolor: '#f7fafc',
        }};

        Plotly.newPlot('comparisonChart', data, layout);

        // Improvement Chart
        var colors = {improvements_json}.map(val => val > 0 ? 'rgb(72, 187, 120)' : 'rgb(245, 101, 101)');

        var trace3 = {{
            x: {metric_names_json},
            y: {improvements_json},
            type: 'bar',
            marker: {{
                color: colors,
            }}
        }};

        var layout2 = {{
            yaxis: {{
                title: 'Improvement (%)',
                zeroline: true,
                zerolinewidth: 2,
                zerolinecolor: 'gray'
            }},
            xaxis: {{
                title: 'Metrics'
            }},
            plot_bgcolor: 'white',
            paper_bgcolor: '#f7fafc',
        }};

        Plotly.newPlot('improvementChart', [trace3], layout2);
    </script>
</body>
</html>
"""

    # Save HTML report
    output_file = "evaluation/results/evaluation_report.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ HTML report saved: {output_file}")
    print("🌐 Open the file in a browser to view")

    return output_file


if __name__ == "__main__":
    generate_html_report()
