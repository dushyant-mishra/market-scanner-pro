"""
Market Scanner V2 — Robust FinBERT Sentiment Analysis
Leverages HuggingFace transformers and ProsusAI/finbert to analyze financial news.
"""

from __future__ import annotations

import streamlit as st
import numpy as np

# Use try/except so the rest of the app doesn't crash if transformers isn't installed yet
try:
    from transformers import pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

@st.cache_resource
def get_finbert_pipeline():
    """Lazily load the FinBERT model into Streamlit's global cache."""
    if not HAS_TRANSFORMERS:
        return None
    # Use ProsusAI/finbert, specifically fine-tuned on financial tone
    try:
        # Load the pipeline. Use device=-1 (CPU) to ensure broad compatibility, 
        # though it can be set to 0 if CUDA is available.
        return pipeline("sentiment-analysis", model="ProsusAI/finbert")
    except Exception as e:
        print(f"Error loading FinBERT: {e}")
        return None

def calculate_news_sentiment(news_texts: list[str]) -> dict:
    """Analyze a list of news headlines/summaries and return an aggregate sentiment score.
    
    Returns
    -------
    dict
        {
            'score': float (-1.0 to 1.0, where >0 is bullish, <0 is bearish),
            'status': str ('success', 'no_news', 'no_model', 'error')
        }
    """
    if not news_texts:
        return {"score": 0.0, "status": "no_news"}
        
    finbert = get_finbert_pipeline()
    if not finbert:
        return {"score": 0.0, "status": "no_model"}
        
    try:
        # FinBERT has a max token limit (usually 512). We'll truncate strings just in case.
        truncated_texts = [text[:1000] for text in news_texts]
        
        results = finbert(truncated_texts)
        
        # Results look like: [{'label': 'positive', 'score': 0.85}, {'label': 'negative', 'score': 0.99}]
        scores = []
        for res in results:
            label = res['label'].lower()
            confidence = res['score']
            
            if label == "positive":
                scores.append(confidence)
            elif label == "negative":
                scores.append(-confidence)
            else:
                # Neutral
                scores.append(0.0)
                
        # Average sentiment across all recent news
        avg_score = float(np.mean(scores)) if scores else 0.0
        
        return {
            "score": avg_score,
            "status": "success"
        }
    except Exception as e:
        print(f"Sentiment analysis error: {e}")
        return {"score": 0.0, "status": "error"}
