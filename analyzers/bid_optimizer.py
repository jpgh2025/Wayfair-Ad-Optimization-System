import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from ..data_ingestion.models import Keyword, Campaign, Product


@dataclass
class BidRecommendation:
    keyword_id: str
    keyword_text: str
    current_bid: float
    recommended_bid: float
    bid_change_percentage: float
    action: str  # 'increase', 'decrease', 'pause', 'maintain'
    rationale: str
    expected_impact: Dict[str, float]


class BidOptimizationEngine:
    def __init__(self, target_roas: float = 3.0, target_acos: float = 33.3):
        self.target_roas = target_roas
        self.target_acos = target_acos
        self.max_bid_change = 0.30  # 30% max change per cycle
        self.min_bid = 0.50
        self.max_bid = 10.00
        self.pause_threshold_clicks = 100
        self.pause_threshold_ctr = 0.10
        
    def optimize_bids(self, keywords: List[Keyword], campaigns: List[Campaign],
                     products: Optional[List[Product]] = None) -> List[BidRecommendation]:
        kw_df = pd.DataFrame([vars(k) for k in keywords])
        camp_df = pd.DataFrame([vars(c) for c in campaigns])
        
        kw_df = pd.merge(kw_df, camp_df[['campaign_id', 'campaign_name']], on='campaign_id', how='left')
        
        recommendations = []
        
        for _, keyword in kw_df.iterrows():
            recommendation = self._analyze_keyword_bid(keyword, kw_df)
            if recommendation:
                recommendations.append(recommendation)
        
        high_impact_first = sorted(recommendations, 
                                 key=lambda x: abs(x.expected_impact.get('revenue_change', 0)), 
                                 reverse=True)
        
        return high_impact_first
    
    def _analyze_keyword_bid(self, keyword: pd.Series, all_keywords: pd.DataFrame) -> Optional[BidRecommendation]:
        if keyword['impressions'] < 10:
            return None
        
        current_roas = keyword['roas']
        current_ctr = keyword['ctr']
        current_cr = keyword['conversion_rate']
        current_bid = keyword['current_bid']
        
        if keyword['clicks'] >= self.pause_threshold_clicks and keyword['conversions'] == 0:
            return self._create_pause_recommendation(keyword)
        
        if current_ctr < self.pause_threshold_ctr and keyword['impressions'] > 1000:
            return self._create_pause_recommendation(keyword, reason="CTR too low")
        
        target_cpc = self._calculate_target_cpc(keyword)
        current_cpc = keyword['spend'] / keyword['clicks'] if keyword['clicks'] > 0 else current_bid
        
        bid_ratio = target_cpc / current_cpc if current_cpc > 0 else 1.0
        
        if bid_ratio > 1.1:
            return self._create_increase_recommendation(keyword, target_cpc, all_keywords)
        elif bid_ratio < 0.9:
            return self._create_decrease_recommendation(keyword, target_cpc)
        else:
            return None
    
    def _calculate_target_cpc(self, keyword: pd.Series) -> float:
        if keyword['conversions'] == 0:
            avg_order_value = 100.0
            estimated_cr = 0.01
        else:
            avg_order_value = keyword['revenue'] / keyword['conversions']
            estimated_cr = keyword['conversion_rate'] / 100
        
        target_cpc = (avg_order_value * estimated_cr) / self.target_roas
        
        if keyword['roas'] > self.target_roas * 1.5:
            target_cpc *= 1.2
        elif keyword['roas'] < self.target_roas * 0.5:
            target_cpc *= 0.7
        
        return max(self.min_bid, min(target_cpc, self.max_bid))
    
    def _create_increase_recommendation(self, keyword: pd.Series, target_bid: float, 
                                      all_keywords: pd.DataFrame) -> BidRecommendation:
        current_bid = keyword['current_bid']
        
        max_increase = current_bid * (1 + self.max_bid_change)
        recommended_bid = min(target_bid, max_increase)
        recommended_bid = round(recommended_bid, 2)
        
        bid_change_pct = ((recommended_bid - current_bid) / current_bid) * 100
        
        competitor_avg_bid = self._get_competitor_avg_bid(keyword, all_keywords)
        if competitor_avg_bid and recommended_bid < competitor_avg_bid * 0.8:
            recommended_bid = min(competitor_avg_bid * 0.9, max_increase)
            recommended_bid = round(recommended_bid, 2)
        
        expected_impact = self._calculate_expected_impact(keyword, current_bid, recommended_bid)
        
        rationale = self._generate_increase_rationale(keyword, target_bid, competitor_avg_bid)
        
        return BidRecommendation(
            keyword_id=keyword['keyword_id'],
            keyword_text=keyword['keyword_text'],
            current_bid=current_bid,
            recommended_bid=recommended_bid,
            bid_change_percentage=round(bid_change_pct, 1),
            action='increase',
            rationale=rationale,
            expected_impact=expected_impact
        )
    
    def _create_decrease_recommendation(self, keyword: pd.Series, target_bid: float) -> BidRecommendation:
        current_bid = keyword['current_bid']
        
        max_decrease = current_bid * (1 - self.max_bid_change)
        recommended_bid = max(target_bid, max_decrease, self.min_bid)
        recommended_bid = round(recommended_bid, 2)
        
        bid_change_pct = ((recommended_bid - current_bid) / current_bid) * 100
        
        expected_impact = self._calculate_expected_impact(keyword, current_bid, recommended_bid)
        
        rationale = self._generate_decrease_rationale(keyword, target_bid)
        
        return BidRecommendation(
            keyword_id=keyword['keyword_id'],
            keyword_text=keyword['keyword_text'],
            current_bid=current_bid,
            recommended_bid=recommended_bid,
            bid_change_percentage=round(bid_change_pct, 1),
            action='decrease',
            rationale=rationale,
            expected_impact=expected_impact
        )
    
    def _create_pause_recommendation(self, keyword: pd.Series, reason: str = "No conversions") -> BidRecommendation:
        return BidRecommendation(
            keyword_id=keyword['keyword_id'],
            keyword_text=keyword['keyword_text'],
            current_bid=keyword['current_bid'],
            recommended_bid=0.0,
            bid_change_percentage=-100.0,
            action='pause',
            rationale=f"{reason}. {keyword['clicks']} clicks, ${keyword['spend']:.2f} spent",
            expected_impact={'spend_savings': keyword['spend'] / 30}  # Daily average
        )
    
    def _get_competitor_avg_bid(self, keyword: pd.Series, all_keywords: pd.DataFrame) -> Optional[float]:
        similar_keywords = all_keywords[
            (all_keywords['keyword_text'].str.contains(keyword['keyword_text'].split()[0], case=False)) &
            (all_keywords['keyword_id'] != keyword['keyword_id']) &
            (all_keywords['impressions'] > 100)
        ]
        
        if len(similar_keywords) > 0:
            return similar_keywords['current_bid'].median()
        return None
    
    def _calculate_expected_impact(self, keyword: pd.Series, current_bid: float, new_bid: float) -> Dict[str, float]:
        bid_ratio = new_bid / current_bid if current_bid > 0 else 1.0
        
        impression_multiplier = 1 + (bid_ratio - 1) * 0.5
        click_multiplier = impression_multiplier * (1 + (bid_ratio - 1) * 0.2)
        
        expected_impressions = keyword['impressions'] * impression_multiplier
        expected_clicks = keyword['clicks'] * click_multiplier
        expected_spend = expected_clicks * new_bid
        expected_conversions = expected_clicks * (keyword['conversion_rate'] / 100)
        expected_revenue = expected_conversions * (keyword['revenue'] / keyword['conversions'] if keyword['conversions'] > 0 else 100)
        
        return {
            'impression_change': expected_impressions - keyword['impressions'],
            'click_change': expected_clicks - keyword['clicks'],
            'spend_change': expected_spend - keyword['spend'],
            'revenue_change': expected_revenue - keyword['revenue'],
            'roas_change': (expected_revenue / expected_spend if expected_spend > 0 else 0) - keyword['roas']
        }
    
    def _generate_increase_rationale(self, keyword: pd.Series, target_bid: float, 
                                   competitor_avg: Optional[float]) -> str:
        reasons = []
        
        if keyword['roas'] > self.target_roas:
            reasons.append(f"ROAS {keyword['roas']:.1f}x exceeds target")
        
        if keyword['conversion_rate'] > 2.0:
            reasons.append(f"High conversion rate {keyword['conversion_rate']:.1f}%")
        
        current_position = self._estimate_position(keyword)
        if current_position and current_position > 3:
            reasons.append(f"Low ad position (est. #{current_position})")
        
        if competitor_avg and keyword['current_bid'] < competitor_avg * 0.8:
            reasons.append(f"Below competitor avg ${competitor_avg:.2f}")
        
        return "; ".join(reasons) if reasons else "Opportunity to capture more profitable traffic"
    
    def _generate_decrease_rationale(self, keyword: pd.Series, target_bid: float) -> str:
        reasons = []
        
        if keyword['roas'] < self.target_roas:
            reasons.append(f"ROAS {keyword['roas']:.1f}x below target")
        
        if keyword['conversion_rate'] < 0.5:
            reasons.append(f"Low conversion rate {keyword['conversion_rate']:.1f}%")
        
        current_acos = (keyword['spend'] / keyword['revenue'] * 100) if keyword['revenue'] > 0 else 100
        if current_acos > self.target_acos:
            reasons.append(f"ACoS {current_acos:.1f}% exceeds target")
        
        return "; ".join(reasons) if reasons else "Reducing spend to improve efficiency"
    
    def _estimate_position(self, keyword: pd.Series) -> Optional[int]:
        if keyword['impressions'] == 0:
            return None
        
        ctr = keyword['ctr']
        if ctr > 5.0:
            return 1
        elif ctr > 3.0:
            return 2
        elif ctr > 1.5:
            return 3
        elif ctr > 0.8:
            return 4
        else:
            return 5