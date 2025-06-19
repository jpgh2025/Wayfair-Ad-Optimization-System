import pandas as pd
import numpy as np
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
import re
import nltk
from nltk.corpus import stopwords
from ..data_ingestion.models import SearchTerm, Campaign


@dataclass
class NegativeKeywordRecommendation:
    negative_keyword: str
    match_type: str  # 'exact', 'phrase'
    application_level: str  # 'campaign', 'account'
    affected_campaigns: List[str]
    wasted_spend: float
    wasted_clicks: int
    search_terms_blocked: List[str]
    rationale: str
    confidence_score: float


class NegativeKeywordGenerator:
    def __init__(self):
        self.min_spend_threshold = 10.0
        self.min_clicks_threshold = 10
        self.max_ctr_threshold = 0.5
        self.zero_conversion_clicks_threshold = 50
        
        try:
            self.stop_words = set(stopwords.words('english'))
        except:
            self.stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                              'of', 'with', 'by', 'from', 'about', 'as', 'into', 'through'}
        
        self.irrelevant_patterns = [
            r'\b(cheap|budget|discount|clearance|wholesale)\b',
            r'\b(free|gratis|no cost)\b',
            r'\b(used|second hand|refurbished|pre-owned)\b',
            r'\b(diy|homemade|make your own)\b',
            r'\b(repair|fix|broken|parts)\b',
            r'\b(vs|versus|compare|comparison)\b',
            r'\b(review|complaint|problem|issue)\b'
        ]
        
        self.competitor_patterns = [
            r'\b(amazon|ikea|target|walmart|costco)\b',
            r'\b(home depot|lowes|overstock)\b'
        ]
    
    def generate_negative_keywords(self, search_terms: List[SearchTerm], 
                                 campaigns: List[Campaign]) -> List[NegativeKeywordRecommendation]:
        st_df = pd.DataFrame([vars(st) for st in search_terms])
        camp_df = pd.DataFrame([vars(c) for c in campaigns])
        
        recommendations = []
        
        zero_conversion_terms = self._find_zero_conversion_terms(st_df)
        recommendations.extend(zero_conversion_terms)
        
        low_quality_terms = self._find_low_quality_terms(st_df)
        recommendations.extend(low_quality_terms)
        
        irrelevant_terms = self._find_irrelevant_terms(st_df)
        recommendations.extend(irrelevant_terms)
        
        competitor_terms = self._find_competitor_terms(st_df)
        recommendations.extend(competitor_terms)
        
        pattern_based_negatives = self._find_pattern_based_negatives(st_df)
        recommendations.extend(pattern_based_negatives)
        
        recommendations = self._deduplicate_recommendations(recommendations)
        
        recommendations.sort(key=lambda x: x.wasted_spend, reverse=True)
        
        return recommendations
    
    def _find_zero_conversion_terms(self, search_terms: pd.DataFrame) -> List[NegativeKeywordRecommendation]:
        recommendations = []
        
        zero_conv = search_terms[
            (search_terms['conversions'] == 0) &
            (search_terms['clicks'] >= self.zero_conversion_clicks_threshold) &
            (search_terms['spend'] >= self.min_spend_threshold)
        ].copy()
        
        exact_negatives = zero_conv.groupby('search_term').agg({
            'spend': 'sum',
            'clicks': 'sum',
            'campaign_id': lambda x: list(set(x))
        }).reset_index()
        
        for _, term in exact_negatives.iterrows():
            rec = NegativeKeywordRecommendation(
                negative_keyword=term['search_term'],
                match_type='exact',
                application_level='account',
                affected_campaigns=term['campaign_id'],
                wasted_spend=term['spend'],
                wasted_clicks=term['clicks'],
                search_terms_blocked=[term['search_term']],
                rationale=f"No conversions from {term['clicks']} clicks, ${term['spend']:.2f} spent",
                confidence_score=0.95
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _find_low_quality_terms(self, search_terms: pd.DataFrame) -> List[NegativeKeywordRecommendation]:
        recommendations = []
        
        low_quality = search_terms[
            (search_terms['ctr'] < self.max_ctr_threshold) &
            (search_terms['impressions'] >= 1000) &
            (search_terms['conversions'] == 0)
        ].copy()
        
        for _, term in low_quality.iterrows():
            if self._is_generic_term(term['search_term']):
                rec = NegativeKeywordRecommendation(
                    negative_keyword=term['search_term'],
                    match_type='phrase',
                    application_level='campaign',
                    affected_campaigns=[term['campaign_id']],
                    wasted_spend=term['spend'],
                    wasted_clicks=term['clicks'],
                    search_terms_blocked=[term['search_term']],
                    rationale=f"Very low CTR {term['ctr']:.2f}% with {term['impressions']} impressions",
                    confidence_score=0.8
                )
                recommendations.append(rec)
        
        return recommendations
    
    def _find_irrelevant_terms(self, search_terms: pd.DataFrame) -> List[NegativeKeywordRecommendation]:
        recommendations = []
        
        for pattern in self.irrelevant_patterns:
            matching_terms = search_terms[
                search_terms['search_term'].str.contains(pattern, case=False, regex=True)
            ].copy()
            
            if len(matching_terms) > 0:
                pattern_spend = matching_terms['spend'].sum()
                pattern_clicks = matching_terms['clicks'].sum()
                
                if pattern_spend >= self.min_spend_threshold:
                    keyword_match = re.search(pattern, matching_terms.iloc[0]['search_term'], re.IGNORECASE)
                    if keyword_match:
                        negative_keyword = keyword_match.group()
                        
                        rec = NegativeKeywordRecommendation(
                            negative_keyword=negative_keyword,
                            match_type='phrase',
                            application_level='account',
                            affected_campaigns=list(set(matching_terms['campaign_id'].tolist())),
                            wasted_spend=pattern_spend,
                            wasted_clicks=pattern_clicks,
                            search_terms_blocked=matching_terms['search_term'].tolist()[:5],
                            rationale=f"Irrelevant term pattern: '{negative_keyword}'",
                            confidence_score=0.9
                        )
                        recommendations.append(rec)
        
        return recommendations
    
    def _find_competitor_terms(self, search_terms: pd.DataFrame) -> List[NegativeKeywordRecommendation]:
        recommendations = []
        
        for pattern in self.competitor_patterns:
            matching_terms = search_terms[
                search_terms['search_term'].str.contains(pattern, case=False, regex=True)
            ].copy()
            
            if len(matching_terms) > 0:
                competitor_match = re.search(pattern, matching_terms.iloc[0]['search_term'], re.IGNORECASE)
                if competitor_match:
                    competitor_name = competitor_match.group()
                    
                    rec = NegativeKeywordRecommendation(
                        negative_keyword=competitor_name,
                        match_type='phrase',
                        application_level='account',
                        affected_campaigns=list(set(matching_terms['campaign_id'].tolist())),
                        wasted_spend=matching_terms['spend'].sum(),
                        wasted_clicks=matching_terms['clicks'].sum(),
                        search_terms_blocked=matching_terms['search_term'].tolist()[:5],
                        rationale=f"Competitor brand term: '{competitor_name}'",
                        confidence_score=1.0
                    )
                    recommendations.append(rec)
        
        return recommendations
    
    def _find_pattern_based_negatives(self, search_terms: pd.DataFrame) -> List[NegativeKeywordRecommendation]:
        recommendations = []
        
        poor_performers = search_terms[
            (search_terms['spend'] >= self.min_spend_threshold) &
            (search_terms['conversions'] == 0)
        ].copy()
        
        word_performance = {}
        for _, term in poor_performers.iterrows():
            words = self._extract_meaningful_words(term['search_term'])
            for word in words:
                if word not in word_performance:
                    word_performance[word] = {'spend': 0, 'clicks': 0, 'conversions': 0, 
                                            'campaigns': set(), 'terms': []}
                word_performance[word]['spend'] += term['spend']
                word_performance[word]['clicks'] += term['clicks']
                word_performance[word]['conversions'] += term['conversions']
                word_performance[word]['campaigns'].add(term['campaign_id'])
                word_performance[word]['terms'].append(term['search_term'])
        
        for word, stats in word_performance.items():
            if (stats['spend'] >= self.min_spend_threshold * 3 and 
                stats['conversions'] == 0 and 
                stats['clicks'] >= self.zero_conversion_clicks_threshold):
                
                rec = NegativeKeywordRecommendation(
                    negative_keyword=word,
                    match_type='phrase',
                    application_level='campaign' if len(stats['campaigns']) == 1 else 'account',
                    affected_campaigns=list(stats['campaigns']),
                    wasted_spend=stats['spend'],
                    wasted_clicks=stats['clicks'],
                    search_terms_blocked=stats['terms'][:5],
                    rationale=f"Common word in non-converting terms: '{word}'",
                    confidence_score=0.7
                )
                recommendations.append(rec)
        
        return recommendations
    
    def _is_generic_term(self, search_term: str) -> bool:
        words = search_term.lower().split()
        
        if len(words) == 1 and words[0] in ['furniture', 'decor', 'home', 'office', 'bedroom', 'living', 'kitchen']:
            return True
        
        if len(words) <= 2 and all(word in self.stop_words or len(word) <= 3 for word in words):
            return True
        
        return False
    
    def _extract_meaningful_words(self, search_term: str) -> List[str]:
        words = re.findall(r'\b\w+\b', search_term.lower())
        
        meaningful_words = [
            word for word in words 
            if word not in self.stop_words and 
            len(word) > 3 and 
            not word.isdigit()
        ]
        
        return meaningful_words
    
    def _deduplicate_recommendations(self, recommendations: List[NegativeKeywordRecommendation]) -> List[NegativeKeywordRecommendation]:
        seen_keywords = {}
        deduplicated = []
        
        for rec in sorted(recommendations, key=lambda x: x.confidence_score, reverse=True):
            key = (rec.negative_keyword.lower(), rec.match_type)
            
            if key not in seen_keywords:
                seen_keywords[key] = rec
                deduplicated.append(rec)
            else:
                existing = seen_keywords[key]
                existing.wasted_spend += rec.wasted_spend
                existing.wasted_clicks += rec.wasted_clicks
                existing.affected_campaigns = list(set(existing.affected_campaigns + rec.affected_campaigns))
                existing.search_terms_blocked = list(set(existing.search_terms_blocked + rec.search_terms_blocked))[:10]
        
        return deduplicated