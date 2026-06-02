def calculate_bayesian_conviction(fundamental_quality: float, causal_signals: dict, patterns: dict) -> dict:
    """
    Calculate the Bayesian Conviction Probability of a 50%+ Upside Breakout.
    
    Formula (simplified Bayesian Updating):
    P(H) = Prior probability of a massive breakout (e.g. 15% base rate)
    P(E|H) / P(E|~H) = Likelihood Ratio
    
    We update the prior using a series of Likelihood Ratios (Bayes Factor)
    based on independent evidence:
    1. Fundamental Quality Score
    2. Causal Volume Lead (Granger Causality)
    3. Edwards & Magee Pattern Breakouts (Trendline, Double Bottom, Flag)
    """
    
    # Prior probability of a stock having a massive 50%+ upside run in 90 days.
    # Base rate in the stock market is quite low.
    prior = 0.15 
    
    # Convert prior to odds
    odds = prior / (1 - prior)
    
    evidence_log = []
    
    # 1. Fundamental Evidence (Quality Score out of 100)
    # A high quality score (>80) significantly increases the odds of sustained upside.
    if fundamental_quality >= 80:
        odds *= 2.5
        evidence_log.append(f"Top-tier Fundamentals (Score: {fundamental_quality}%) -> 2.5x Odds")
    elif fundamental_quality >= 60:
        odds *= 1.5
        evidence_log.append(f"Solid Fundamentals (Score: {fundamental_quality}%) -> 1.5x Odds")
    elif fundamental_quality < 40:
        odds *= 0.5
        evidence_log.append(f"Poor Fundamentals (Score: {fundamental_quality}%) -> 0.5x Odds")
        
    # 2. Causal Volume Evidence
    # If Granger causality shows volume leads price, smart money is accumulating.
    scm_path = causal_signals.get("scm_path", {})
    granger = causal_signals.get("granger", {})
    
    if granger.get("significant", False):
        odds *= 2.0
        evidence_log.append("Causal Lead: Volume statistically predicts price (Granger Sig) -> 2.0x Odds")
    
    # 3. Edwards & Magee Technical Pattern Evidence
    high_volume = patterns.get("high_volume_event", False)
    vol_multiplier = 1.5 if high_volume else 1.0
    
    if patterns.get("trendline_breakout", False):
        odds *= (2.0 * vol_multiplier)
        msg = "Edwards & Magee: Trendline Breakout" + (" on High Volume" if high_volume else "")
        evidence_log.append(f"{msg} -> {2.0 * vol_multiplier}x Odds")
        
    if patterns.get("double_bottom", False):
        odds *= (1.8 * vol_multiplier)
        msg = "Edwards & Magee: Double Bottom Breakout" + (" on High Volume" if high_volume else "")
        evidence_log.append(f"{msg} -> {1.8 * vol_multiplier}x Odds")
        
    if patterns.get("flag_breakout", False):
        odds *= (2.2 * vol_multiplier)
        msg = "Edwards & Magee: Bull Flag Breakout" + (" on High Volume" if high_volume else "")
        evidence_log.append(f"{msg} -> {2.2 * vol_multiplier}x Odds")
        
    if patterns.get("gap") == "gap_up" and high_volume:
        odds *= 1.5
        evidence_log.append("Edwards & Magee: Breakaway Gap Up on High Volume -> 1.5x Odds")
        
    # Convert back to probability
    posterior = odds / (1 + odds)
    
    # Cap posterior at 95% because nothing is 100% guaranteed in markets
    posterior = min(posterior, 0.95)
    
    return {
        "prior": prior,
        "posterior_prob": posterior,
        "evidence_log": evidence_log
    }
