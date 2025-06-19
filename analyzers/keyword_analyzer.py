import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
import re
from dataclasses import dataclass
from ..data_ingestion.models import SearchTerm, Keyword, Campaign


@dataclass
class KeywordRecommendation:
    keyword_text: str
    match_type: str
    suggested_bid: float
    expected_impressions: int
    expected_roas: float
    opportunity_score: float
    rationale: str
    source_search_terms: List[str]


class KeywordExpansionTool:
    def __init__(self, target_roas: float = 3.0):
        self.target_roas = target_roas
        self.min_impressions_threshold = 50
        self.min_supplier_share = 5.0
        
    def analyze_search_terms(self, search_terms: List[SearchTerm], 
                           existing_keywords: List[Keyword],
                           campaigns: List[Campaign]) -> List[KeywordRecommendation]:
        st_df = pd.DataFrame([vars(st) for st in search_terms])
        kw_df = pd.DataFrame([vars(kw) for kw in existing_keywords])
        camp_df = pd.DataFrame([vars(c) for c in campaigns])
        
        existing_keyword_texts = set(kw_df['keyword_text'].str.lower())
        
        untargeted_terms = st_df[st_df['keyword_id'].isna()].copy()
        
        untargeted_terms = untargeted_terms[
            (untargeted_terms['impressions'] >= self.min_impressions_threshold) |
            (untargeted_terms['conversions'] > 0)
        ]
        
        recommendations = []
        
        high_value_terms = untargeted_terms[
            (untargeted_terms['roas'] >= self.target_roas) |
            (untargeted_terms['conversions'] > 0)
        ].copy()
        
        for _, term in high_value_terms.iterrows():
            recommendations.extend(self._generate_keyword_variations(term, existing_keyword_texts, kw_df))
        
        high_volume_terms = untargeted_terms[
            (untargeted_terms['impressions'] >= 500) &
            (untargeted_terms['supplier_share'] <= 20)
        ].copy()
        
        for _, term in high_volume_terms.iterrows():
            if term['search_term'].lower() not in [r.keyword_text.lower() for r in recommendations]:
                recommendations.extend(self._generate_keyword_variations(term, existing_keyword_texts, kw_df))
        
        recommendations.sort(key=lambda x: x.opportunity_score, reverse=True)
        
        return recommendations[:100]
    
    def _generate_keyword_variations(self, search_term_data: pd.Series, 
                                   existing_keywords: set,
                                   keyword_df: pd.DataFrame) -> List[KeywordRecommendation]:
        recommendations = []
        search_term = search_term_data['search_term']
        
        exact_keyword = search_term.lower()
        if exact_keyword not in existing_keywords:
            exact_rec = self._create_recommendation(
                search_term_data, exact_keyword, 'exact', keyword_df
            )
            recommendations.append(exact_rec)
        
        phrase_variations = self._generate_phrase_variations(search_term)
        for phrase in phrase_variations:
            if phrase.lower() not in existing_keywords:
                phrase_rec = self._create_recommendation(
                    search_term_data, phrase, 'phrase', keyword_df
                )
                recommendations.append(phrase_rec)
        
        broad_variations = self._generate_broad_variations(search_term)
        for broad in broad_variations:
            if broad.lower() not in existing_keywords and len(broad.split()) <= 3:
                broad_rec = self._create_recommendation(
                    search_term_data, broad, 'broad', keyword_df
                )
                recommendations.append(broad_rec)
        
        return recommendations
    
    def _generate_phrase_variations(self, search_term: str) -> List[str]:
        words = search_term.split()
        variations = []
        
        if len(words) > 2:
            for i in range(len(words) - 1):
                variations.append(' '.join(words[i:i+2]))
        
        core_words = [w for w in words if len(w) > 3 and w not in ['with', 'for', 'and', 'the']]
        if len(core_words) >= 2:
            variations.append(' '.join(core_words[:2]))
        
        return list(set(variations))
    
    def _generate_broad_variations(self, search_term: str) -> List[str]:
        words = search_term.split()
        variations = []
        
        core_words = [w for w in words if len(w) > 3 and w not in ['with', 'for', 'and', 'the', 'inch', 'feet']]
        
        if core_words:
            variations.append(core_words[0])
            
            if len(core_words) > 1:
                variations.append(f"{core_words[0]} {core_words[1]}")
        
        pattern_words = re.findall(r'\b(?:table|chair|lamp|rug|sofa|bed|desk|cabinet|shelf|mirror)\b', 
                                 search_term.lower())
        variations.extend(pattern_words)
        
        return list(set(variations))
    
    def _create_recommendation(self, search_term_data: pd.Series, 
                             keyword_text: str, match_type: str,
                             keyword_df: pd.DataFrame) -> KeywordRecommendation:
        bid_multipliers = {'exact': 1.2, 'phrase': 1.0, 'broad': 0.8}
        impression_multipliers = {'exact': 0.3, 'phrase': 0.6, 'broad': 1.5}
        
        category_avg_cpc = self._get_category_average_cpc(keyword_df)
        
        base_bid = search_term_data['spend'] / search_term_data['clicks'] if search_term_data['clicks'] > 0 else category_avg_cpc
        suggested_bid = base_bid * bid_multipliers[match_type]
        
        if search_term_data['roas'] > self.target_roas:
            suggested_bid *= 1.15
        
        suggested_bid = max(0.50, min(suggested_bid, 5.00))
        
        expected_impressions = int(search_term_data['impressions'] * impression_multipliers[match_type])
        expected_roas = search_term_data['roas'] * (0.9 if match_type == 'broad' else 1.0)
        
        opportunity_score = self._calculate_opportunity_score(
            expected_impressions, expected_roas, search_term_data['supplier_share']
        )
        
        rationale = self._generate_rationale(search_term_data, match_type)
        
        return KeywordRecommendation(
            keyword_text=keyword_text,
            match_type=match_type,
            suggested_bid=round(suggested_bid, 2),
            expected_impressions=expected_impressions,
            expected_roas=round(expected_roas, 2),
            opportunity_score=round(opportunity_score, 2),
            rationale=rationale,
            source_search_terms=[search_term_data['search_term']]
        )
    
    def _get_category_average_cpc(self, keyword_df: pd.DataFrame) -> float:
        if len(keyword_df) == 0:
            return 1.50
        
        valid_cpcs = keyword_df[keyword_df['clicks'] > 0]['spend'] / keyword_df[keyword_df['clicks'] > 0]['clicks']
        return valid_cpcs.median() if len(valid_cpcs) > 0 else 1.50
    
    def _calculate_opportunity_score(self, impressions: int, roas: float, supplier_share: float) -> float:
        impression_score = min(impressions / 1000, 10) * 20
        roas_score = min(roas / self.target_roas, 2) * 40
        share_opportunity_score = (100 - supplier_share) / 100 * 40
        
        return impression_score + roas_score + share_opportunity_score
    
    def _generate_rationale(self, search_term_data: pd.Series, match_type: str) -> str:
        rationales = []
        
        if search_term_data['roas'] >= self.target_roas:
            rationales.append(f"High ROAS of {search_term_data['roas']:.1f}x")
        
        if search_term_data['conversions'] > 0:
            rationales.append(f"{int(search_term_data['conversions'])} conversions")
        
        if search_term_data['impressions'] >= 1000:
            rationales.append(f"{int(search_term_data['impressions'])} impressions")
        
        if search_term_data['supplier_share'] < 20:
            rationales.append(f"Low market share ({search_term_data['supplier_share']:.1f}%)")
        
        return f"{match_type.capitalize()} match: " + ", ".join(rationales)