#!/usr/bin/env python3
import os
import sys
import yaml
import logging
from datetime import datetime
from pathlib import Path
import click
import pandas as pd
from typing import Dict, List, Optional

from data_ingestion.report_parser import WayfairReportParser
from data_ingestion.data_validator import DataValidator
from data_ingestion.report_merger import ReportMerger

from analyzers.keyword_analyzer import KeywordExpansionTool
from analyzers.bid_optimizer import BidOptimizationEngine
from analyzers.budget_allocator import BudgetAllocationOptimizer
from analyzers.negative_keyword_finder import NegativeKeywordGenerator
from analyzers.product_analyzer import ProductPerformanceAnalyzer

from output_generators.bulk_upload_formatter import WayfairBulkUploadFormatter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/wsp_optimizer_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WSPOptimizer:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.load_configs()
        self.parser = WayfairReportParser()
        self.validator = DataValidator()
        self.merger = ReportMerger()
        self.formatter = WayfairBulkUploadFormatter()
        
    def load_configs(self):
        with open(f"{self.config_dir}/thresholds.yaml", 'r') as f:
            self.thresholds = yaml.safe_load(f)
        
        with open(f"{self.config_dir}/targets.yaml", 'r') as f:
            self.targets = yaml.safe_load(f)
    
    def run_full_optimization(self, report_paths: Dict[str, str]):
        logger.info("Starting WSP optimization process...")
        
        # Step 1: Parse and validate data
        logger.info("Parsing reports...")
        campaigns = self.parser.parse_campaign_performance_report(report_paths['campaigns'])
        keywords = self.parser.parse_keyword_optimization_report(report_paths['keywords'])
        search_terms = self.parser.parse_search_term_research_report(report_paths['search_terms'])
        products = self.parser.parse_product_performance_report(report_paths['products'])
        
        # Step 2: Validate data
        logger.info("Validating data...")
        validations = [
            self.validator.validate_campaigns(campaigns),
            self.validator.validate_keywords(keywords),
            self.validator.validate_search_terms(search_terms),
            self.validator.validate_products(products),
            self.validator.validate_cross_references(campaigns, keywords, search_terms)
        ]
        
        for is_valid, messages in validations:
            if not is_valid:
                logger.error(f"Validation errors: {messages}")
                raise ValueError("Data validation failed")
            elif messages:
                for msg in messages:
                    logger.warning(msg)
        
        # Step 3: Merge data for analysis
        logger.info("Merging data...")
        self.merger.load_data(campaigns, keywords, search_terms, products)
        
        # Step 4: Run optimizations
        all_recommendations = {}
        
        # Keyword expansion
        logger.info("Running keyword expansion analysis...")
        keyword_tool = KeywordExpansionTool(
            target_roas=self.thresholds['performance_thresholds']['target_roas']
        )
        keyword_recommendations = keyword_tool.analyze_search_terms(
            search_terms, keywords, campaigns
        )
        all_recommendations['keywords'] = keyword_recommendations
        logger.info(f"Generated {len(keyword_recommendations)} keyword recommendations")
        
        # Bid optimization
        logger.info("Running bid optimization...")
        bid_optimizer = BidOptimizationEngine(
            target_roas=self.thresholds['performance_thresholds']['target_roas'],
            target_acos=self.thresholds['performance_thresholds']['target_acos']
        )
        bid_recommendations = bid_optimizer.optimize_bids(keywords, campaigns, products)
        all_recommendations['bids'] = bid_recommendations
        logger.info(f"Generated {len(bid_recommendations)} bid recommendations")
        
        # Budget allocation
        logger.info("Running budget optimization...")
        budget_optimizer = BudgetAllocationOptimizer()
        budget_recommendations = budget_optimizer.optimize_budgets(campaigns, keywords)
        all_recommendations['budgets'] = budget_recommendations
        logger.info(f"Generated {len(budget_recommendations)} budget recommendations")
        
        # Negative keywords
        logger.info("Finding negative keywords...")
        negative_finder = NegativeKeywordGenerator()
        negative_recommendations = negative_finder.generate_negative_keywords(
            search_terms, campaigns
        )
        all_recommendations['negative_keywords'] = negative_recommendations
        logger.info(f"Generated {len(negative_recommendations)} negative keyword recommendations")
        
        # Product analysis
        logger.info("Analyzing product performance...")
        product_analyzer = ProductPerformanceAnalyzer(
            target_roas=self.thresholds['performance_thresholds']['target_roas']
        )
        segmentation, product_recommendations = product_analyzer.analyze_products(
            products, campaigns, keywords
        )
        all_recommendations['products'] = product_recommendations
        logger.info(f"Segmented {len(products)} products and generated recommendations")
        
        # Step 5: Generate outputs
        logger.info("Generating output files...")
        self._generate_outputs(all_recommendations, segmentation)
        
        # Step 6: Create summary report
        summary = self._create_summary_report(all_recommendations, campaigns, keywords, products)
        logger.info("Optimization complete!")
        
        return summary, all_recommendations
    
    def _generate_outputs(self, recommendations: Dict, segmentation):
        # Create individual CSV files
        if recommendations['keywords']:
            campaign_mapping = {c.campaign_id: c.campaign_name for c in self.merger.campaigns_df.to_dict('records')}
            self.formatter.format_keyword_upload(recommendations['keywords'], campaign_mapping)
        
        if recommendations['bids']:
            self.formatter.format_bid_changes(recommendations['bids'])
        
        if recommendations['negative_keywords']:
            self.formatter.format_negative_keywords(recommendations['negative_keywords'])
        
        if recommendations['budgets']:
            self.formatter.format_budget_changes(recommendations['budgets'])
        
        # Create master Excel file
        master_file = self.formatter.create_master_upload_file(recommendations)
        logger.info(f"Created master upload file: {master_file}")
    
    def _create_summary_report(self, recommendations: Dict, campaigns, keywords, products) -> Dict:
        summary = {
            'timestamp': datetime.now().isoformat(),
            'current_state': {
                'total_campaigns': len(campaigns),
                'total_keywords': len(keywords),
                'total_products': len(products),
                'overall_roas': sum(c.revenue for c in campaigns) / sum(c.total_spend for c in campaigns) if campaigns else 0,
                'total_spend': sum(c.total_spend for c in campaigns),
                'total_revenue': sum(c.revenue for c in campaigns)
            },
            'recommendations_summary': {
                'new_keywords': len(recommendations.get('keywords', [])),
                'bid_changes': len(recommendations.get('bids', [])),
                'budget_changes': len(recommendations.get('budgets', [])),
                'negative_keywords': len(recommendations.get('negative_keywords', []))
            },
            'expected_impact': self._calculate_expected_impact(recommendations)
        }
        
        return summary
    
    def _calculate_expected_impact(self, recommendations: Dict) -> Dict:
        impact = {
            'revenue_increase': 0,
            'spend_savings': 0,
            'roas_improvement': 0
        }
        
        if 'bids' in recommendations:
            for rec in recommendations['bids']:
                impact['revenue_increase'] += rec.expected_impact.get('revenue_change', 0)
        
        if 'negative_keywords' in recommendations:
            for rec in recommendations['negative_keywords']:
                impact['spend_savings'] += rec.wasted_spend
        
        if 'budgets' in recommendations:
            for rec in recommendations['budgets']:
                impact['revenue_increase'] += rec.expected_impact.get('monthly_revenue_change', 0)
        
        return impact


@click.command()
@click.option('--campaigns', '-c', required=True, help='Path to campaign performance report')
@click.option('--keywords', '-k', required=True, help='Path to keyword optimization report')
@click.option('--search-terms', '-s', required=True, help='Path to search term research report')
@click.option('--products', '-p', required=True, help='Path to product performance report')
@click.option('--output-dir', '-o', default='reports', help='Output directory for results')
def main(campaigns, keywords, search_terms, products, output_dir):
    """
    Wayfair Sponsored Products Optimizer
    
    Analyzes WSP performance data and generates optimization recommendations.
    """
    os.makedirs('logs', exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    report_paths = {
        'campaigns': campaigns,
        'keywords': keywords,
        'search_terms': search_terms,
        'products': products
    }
    
    try:
        optimizer = WSPOptimizer()
        summary, recommendations = optimizer.run_full_optimization(report_paths)
        
        # Save summary
        summary_path = f"{output_dir}/optimization_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
        with open(summary_path, 'w') as f:
            yaml.dump(summary, f, default_flow_style=False)
        
        logger.info(f"Summary saved to: {summary_path}")
        
        # Print key metrics
        print("\n" + "="*50)
        print("WSP OPTIMIZATION SUMMARY")
        print("="*50)
        print(f"Current ROAS: {summary['current_state']['overall_roas']:.2f}x")
        print(f"Total Spend: ${summary['current_state']['total_spend']:,.2f}")
        print(f"Total Revenue: ${summary['current_state']['total_revenue']:,.2f}")
        print("\nRecommendations:")
        print(f"- New Keywords: {summary['recommendations_summary']['new_keywords']}")
        print(f"- Bid Changes: {summary['recommendations_summary']['bid_changes']}")
        print(f"- Budget Changes: {summary['recommendations_summary']['budget_changes']}")
        print(f"- Negative Keywords: {summary['recommendations_summary']['negative_keywords']}")
        print("\nExpected Impact:")
        print(f"- Revenue Increase: ${summary['expected_impact']['revenue_increase']:,.2f}")
        print(f"- Spend Savings: ${summary['expected_impact']['spend_savings']:,.2f}")
        print("="*50)
        
    except Exception as e:
        logger.error(f"Optimization failed: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()