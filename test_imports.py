#!/usr/bin/env python3
"""Test script to verify all imports work correctly"""

try:
    print("Testing imports...")
    
    # Test data models
    from data_ingestion.models import Campaign, Keyword, SearchTerm, Product
    print("✓ Data models imported successfully")
    
    # Test parsers
    from data_ingestion.report_parser import WayfairReportParser
    print("✓ Report parser imported successfully")
    
    # Test analyzers
    from analyzers.keyword_analyzer import KeywordExpansionTool
    from analyzers.bid_optimizer import BidOptimizationEngine
    from analyzers.budget_allocator import BudgetAllocationOptimizer
    from analyzers.negative_keyword_finder import NegativeKeywordGenerator
    from analyzers.product_analyzer import ProductPerformanceAnalyzer
    print("✓ All analyzers imported successfully")
    
    # Test output generators
    from output_generators.bulk_upload_formatter import WayfairBulkUploadFormatter
    from output_generators.dashboard_builder import DashboardBuilder
    print("✓ Output generators imported successfully")
    
    # Test main
    from main import WSPOptimizer
    print("✓ Main optimizer imported successfully")
    
    # Test app
    from app import app
    print("✓ Flask app imported successfully")
    
    print("\n✅ All imports successful! The application should work correctly.")
    
except ImportError as e:
    print(f"\n❌ Import error: {e}")
    print("Please check the import paths.")