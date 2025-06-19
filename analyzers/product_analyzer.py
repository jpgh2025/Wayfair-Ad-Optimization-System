import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from data_ingestion.models import Product, Campaign, Keyword


class ProductTier(Enum):
    STAR = "Star"
    POTENTIAL = "Potential"
    WORKER = "Worker"
    CULL = "Cull"


@dataclass
class ProductRecommendation:
    sku: str
    product_name: str
    current_tier: ProductTier
    recommended_action: str
    bid_multiplier: float
    budget_allocation_percentage: float
    rationale: str
    expected_impact: Dict[str, float]
    priority: int  # 1-5, 1 being highest


@dataclass
class ProductSegmentation:
    stars: List[Product]
    potentials: List[Product]
    workers: List[Product]
    culls: List[Product]
    tier_metrics: Dict[str, Dict[str, float]]


class ProductPerformanceAnalyzer:
    def __init__(self, target_roas: float = 3.0, min_volume_threshold: int = 10):
        self.target_roas = target_roas
        self.min_volume_threshold = min_volume_threshold
        self.high_roas_threshold = 4.0
        self.low_roas_threshold = 2.0
        self.volume_percentile_threshold = 70
        
    def analyze_products(self, products: List[Product], campaigns: List[Campaign],
                        keywords: List[Keyword]) -> Tuple[ProductSegmentation, List[ProductRecommendation]]:
        prod_df = pd.DataFrame([vars(p) for p in products])
        
        prod_df = self._enrich_product_metrics(prod_df)
        
        segmentation = self._segment_products(prod_df)
        
        recommendations = self._generate_recommendations(segmentation, prod_df, campaigns, keywords)
        
        return segmentation, recommendations
    
    def _enrich_product_metrics(self, products: pd.DataFrame) -> pd.DataFrame:
        products['volume_score'] = products['revenue'] + products['clicks'] * 0.1
        
        products['volume_percentile'] = products['volume_score'].rank(pct=True) * 100
        
        products['efficiency_score'] = products['roas'] * products['true_roas']
        
        products['scalability_score'] = np.where(
            products['inventory_level'].notna(),
            products['inventory_level'] / products['conversions'].clip(lower=1),
            100
        )
        
        products['growth_potential'] = (
            (products['roas'] / self.target_roas).clip(upper=2) * 30 +
            (100 - products['volume_percentile']) * 0.3 +
            products['scalability_score'].clip(upper=100) * 0.4
        )
        
        return products
    
    def _segment_products(self, products: pd.DataFrame) -> ProductSegmentation:
        stars = products[
            (products['roas'] >= self.target_roas) &
            (products['volume_percentile'] >= self.volume_percentile_threshold)
        ]
        
        potentials = products[
            (products['roas'] >= self.target_roas) &
            (products['volume_percentile'] < self.volume_percentile_threshold) &
            (products['clicks'] >= self.min_volume_threshold)
        ]
        
        workers = products[
            (products['roas'] < self.target_roas) &
            (products['roas'] >= self.low_roas_threshold) &
            (products['volume_percentile'] >= self.volume_percentile_threshold)
        ]
        
        culls = products[
            ~products.index.isin(stars.index) &
            ~products.index.isin(potentials.index) &
            ~products.index.isin(workers.index)
        ]
        
        tier_metrics = {
            'stars': self._calculate_tier_metrics(stars),
            'potentials': self._calculate_tier_metrics(potentials),
            'workers': self._calculate_tier_metrics(workers),
            'culls': self._calculate_tier_metrics(culls)
        }
        
        return ProductSegmentation(
            stars=[p for p in products.loc[stars.index].to_dict('records')],
            potentials=[p for p in products.loc[potentials.index].to_dict('records')],
            workers=[p for p in products.loc[workers.index].to_dict('records')],
            culls=[p for p in products.loc[culls.index].to_dict('records')],
            tier_metrics=tier_metrics
        )
    
    def _calculate_tier_metrics(self, tier_df: pd.DataFrame) -> Dict[str, float]:
        if len(tier_df) == 0:
            return {
                'count': 0,
                'total_spend': 0,
                'total_revenue': 0,
                'avg_roas': 0,
                'avg_margin': 0
            }
        
        return {
            'count': len(tier_df),
            'total_spend': tier_df['spend'].sum(),
            'total_revenue': tier_df['revenue'].sum(),
            'avg_roas': tier_df['roas'].mean(),
            'avg_margin': tier_df['margin'].mean()
        }
    
    def _generate_recommendations(self, segmentation: ProductSegmentation, 
                                products: pd.DataFrame,
                                campaigns: List[Campaign],
                                keywords: List[Keyword]) -> List[ProductRecommendation]:
        recommendations = []
        
        for product_dict in segmentation.stars:
            product = pd.Series(product_dict)
            rec = self._create_star_recommendation(product, products)
            recommendations.append(rec)
        
        for product_dict in segmentation.potentials:
            product = pd.Series(product_dict)
            rec = self._create_potential_recommendation(product, products)
            recommendations.append(rec)
        
        for product_dict in segmentation.workers:
            product = pd.Series(product_dict)
            rec = self._create_worker_recommendation(product, products)
            recommendations.append(rec)
        
        for product_dict in segmentation.culls:
            product = pd.Series(product_dict)
            rec = self._create_cull_recommendation(product, products)
            recommendations.append(rec)
        
        recommendations.sort(key=lambda x: x.priority)
        
        return recommendations
    
    def _create_star_recommendation(self, product: pd.Series, all_products: pd.DataFrame) -> ProductRecommendation:
        bid_multiplier = 1.2 if product['roas'] > self.high_roas_threshold else 1.1
        
        current_budget_share = product['spend'] / all_products['spend'].sum()
        recommended_budget_share = current_budget_share * 1.5
        
        expected_impact = {
            'revenue_increase': product['revenue'] * 0.3,
            'volume_increase': product['clicks'] * 0.25,
            'market_share_gain': 5.0
        }
        
        rationale = f"Star performer: ROAS {product['roas']:.1f}x, #{int(product['volume_percentile'])}th percentile volume"
        
        if product.get('inventory_level', 0) < product['conversions'] * 7:
            rationale += " (Monitor inventory levels)"
            bid_multiplier *= 0.9
        
        return ProductRecommendation(
            sku=product['sku'],
            product_name=product['product_name'],
            current_tier=ProductTier.STAR,
            recommended_action="Scale aggressively with dedicated campaign",
            bid_multiplier=bid_multiplier,
            budget_allocation_percentage=recommended_budget_share * 100,
            rationale=rationale,
            expected_impact=expected_impact,
            priority=1
        )
    
    def _create_potential_recommendation(self, product: pd.Series, all_products: pd.DataFrame) -> ProductRecommendation:
        bid_multiplier = 1.15
        
        current_budget_share = product['spend'] / all_products['spend'].sum()
        recommended_budget_share = current_budget_share * 2.0
        
        expected_impact = {
            'revenue_increase': product['revenue'] * 0.5,
            'volume_increase': product['clicks'] * 0.6,
            'tier_upgrade_probability': 0.7
        }
        
        rationale = f"High potential: ROAS {product['roas']:.1f}x but low volume (percentile: {product['volume_percentile']:.0f})"
        
        return ProductRecommendation(
            sku=product['sku'],
            product_name=product['product_name'],
            current_tier=ProductTier.POTENTIAL,
            recommended_action="Increase exposure through higher bids and budget",
            bid_multiplier=bid_multiplier,
            budget_allocation_percentage=recommended_budget_share * 100,
            rationale=rationale,
            expected_impact=expected_impact,
            priority=2
        )
    
    def _create_worker_recommendation(self, product: pd.Series, all_products: pd.DataFrame) -> ProductRecommendation:
        bid_multiplier = 0.9 if product['roas'] < self.low_roas_threshold else 0.95
        
        current_budget_share = product['spend'] / all_products['spend'].sum()
        recommended_budget_share = current_budget_share * 0.8
        
        expected_impact = {
            'efficiency_gain': (self.target_roas - product['roas']) * product['spend'],
            'spend_reduction': product['spend'] * 0.2
        }
        
        rationale = f"Volume driver but below target: ROAS {product['roas']:.1f}x vs target {self.target_roas}x"
        
        return ProductRecommendation(
            sku=product['sku'],
            product_name=product['product_name'],
            current_tier=ProductTier.WORKER,
            recommended_action="Optimize for efficiency - reduce bids gradually",
            bid_multiplier=bid_multiplier,
            budget_allocation_percentage=recommended_budget_share * 100,
            rationale=rationale,
            expected_impact=expected_impact,
            priority=3
        )
    
    def _create_cull_recommendation(self, product: pd.Series, all_products: pd.DataFrame) -> ProductRecommendation:
        if product['conversions'] == 0 and product['clicks'] > 50:
            action = "Pause immediately"
            bid_multiplier = 0.0
            budget_percentage = 0.0
        elif product['roas'] < 1.0:
            action = "Reduce bids by 50% or pause"
            bid_multiplier = 0.5
            budget_percentage = 0.5
        else:
            action = "Test with minimal budget"
            bid_multiplier = 0.7
            budget_percentage = 1.0
        
        expected_impact = {
            'spend_savings': product['spend'] * 0.8,
            'efficiency_improvement': 10.0
        }
        
        rationale = f"Poor performer: ROAS {product['roas']:.1f}x, low volume"
        
        return ProductRecommendation(
            sku=product['sku'],
            product_name=product['product_name'],
            current_tier=ProductTier.CULL,
            recommended_action=action,
            bid_multiplier=bid_multiplier,
            budget_allocation_percentage=budget_percentage,
            rationale=rationale,
            expected_impact=expected_impact,
            priority=4 if bid_multiplier > 0 else 5
        )