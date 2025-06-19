# Wayfair Sponsored Products (WSP) Optimizer

A comprehensive optimization suite for Wayfair Sponsored Products that analyzes advertising performance data and provides actionable recommendations to maximize ROAS and sales growth.

## Overview

The WSP Optimizer addresses key challenges in Wayfair advertising:
- Limited keyword coverage (only 4 keywords targeting 789 search terms)
- Suboptimal bid strategies across 47 campaigns
- Inefficient budget allocation across 46 products
- Need for systematic performance optimization

## Features

### 1. Keyword Expansion & Mining Tool
- Identifies high-performing search terms not currently targeted
- Generates keyword recommendations with match types and suggested bids
- Prioritizes keywords by opportunity score
- Creates Wayfair-compatible bulk upload files

### 2. Bid Optimization Engine
- Calculates optimal bids based on ROAS targets
- Adjusts bids considering conversion rates and competition
- Identifies keywords to pause (>100 clicks, 0 conversions)
- Caps bid changes at ±30% per cycle for stability

### 3. Budget Allocation Optimizer
- Identifies campaigns hitting budget caps with strong ROAS
- Redistributes spend from poor to high performers
- Provides phased implementation plans
- Considers market opportunity and inventory levels

### 4. Negative Keyword Generator
- Finds search terms with high spend and zero conversions
- Identifies irrelevant terms using NLP analysis
- Groups negatives by theme for campaign/account level application
- Detects competitor brand terms automatically

### 5. Product Performance Analyzer
- Segments products into performance tiers:
  - **Stars**: High ROAS, high volume
  - **Potentials**: High ROAS, low volume (need exposure)
  - **Workers**: Low ROAS, high volume (reduce bids)
  - **Culls**: Low ROAS, low volume (consider pausing)
- Provides tier-specific optimization strategies

### 6. Executive Dashboard & Reporting
- Interactive visualizations of performance metrics
- Automated weekly report generation
- Tracks optimization impact over time
- Exports presentation-ready reports

## Installation

1. Clone the repository:
```bash
cd "/Users/guest/Wayfair Report Downloader/wsp-optimizer"
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Download NLTK data (for negative keyword analysis):
```python
import nltk
nltk.download('stopwords')
```

## Usage

### Basic Usage

Run the optimizer with your Wayfair report files:

```bash
python main.py \
  --campaigns path/to/campaign_performance.csv \
  --keywords path/to/keyword_optimization.csv \
  --search-terms path/to/search_term_research.csv \
  --products path/to/product_performance.csv \
  --output-dir reports
```

### Expected Report Formats

The optimizer expects CSV files with the following columns:

**Campaign Performance Report:**
- Campaign ID, Campaign Name, Status, Daily Budget
- Impressions, Clicks, Conversions, Spend, Revenue, ROAS

**Keyword Optimization Report:**
- Keyword ID, Keyword Text, Match Type, Campaign ID
- Current Bid, Impressions, Clicks, Conversions, Spend, Revenue

**Search Term Research Report:**
- Search Term, Keyword ID (optional), Campaign ID
- Impressions, Clicks, Conversions, Spend, Revenue, Supplier Share

**Product Performance Report:**
- SKU, Product Name, Wholesale Cost, Retail Price
- Impressions, Clicks, Conversions, Spend, Revenue, Inventory Level

## Configuration

### Thresholds (config/thresholds.yaml)
- Adjust ROAS targets, CTR thresholds, bid limits
- Configure opportunity scoring weights
- Set confidence score thresholds

### Business Targets (config/targets.yaml)
- Define campaign-specific targets
- Set product tier budget allocations
- Configure optimization frequency

## Output Files

The optimizer generates several output files:

1. **Bulk Upload Files** (reports/bulk_uploads/)
   - keyword_upload_[timestamp].csv
   - bid_changes_[timestamp].csv
   - negative_keywords_[timestamp].csv
   - budget_changes_[timestamp].csv

2. **Master Excel File**
   - wayfair_bulk_upload_[date].xlsx (all recommendations in one file)

3. **Dashboard & Reports** (reports/dashboards/)
   - executive_dashboard_[timestamp].html
   - detailed_report_[timestamp].html

4. **Summary Report**
   - optimization_summary_[timestamp].yaml

## Optimization Logic

The system follows this decision tree:
1. **Expand keyword coverage** to capture missed opportunities
2. **Optimize bids** on existing keywords based on performance
3. **Reallocate budgets** to highest-performing areas
4. **Clean up** with negative keywords and product optimization

## Success Metrics

The optimizer tracks:
- Overall ROAS improvement
- Keyword coverage increase (from 4 to potentially 100+ keywords)
- Wasted spend reduction through negative keywords
- Revenue growth from optimizations

## Best Practices

1. **Run Weekly**: Execute optimizations weekly for best results
2. **Review Recommendations**: Always review recommendations before implementing
3. **Phase Implementation**: Start with high-confidence recommendations
4. **Monitor Impact**: Track performance changes after implementing recommendations
5. **Adjust Targets**: Update configuration based on business goals

## Troubleshooting

### Common Issues

1. **Validation Errors**: Check that report formats match expected columns
2. **No Recommendations**: Verify minimum thresholds in config files
3. **Memory Issues**: Process large reports in batches if needed

### Logging

Check logs in the `logs/` directory for detailed execution information.

## Architecture

```
wsp-optimizer/
├── data_ingestion/       # Report parsing and validation
├── analyzers/           # Optimization engines
├── output_generators/   # Report and file generation
├── config/             # Configuration files
├── main.py            # Main orchestration script
└── requirements.txt   # Python dependencies
```

## Future Enhancements

- Machine learning for bid prediction
- Seasonality detection and adjustment
- A/B testing framework
- Real-time optimization via API integration
- Multi-account support

## License

Proprietary - For use with Wayfair Sponsored Products only.