# meta_v2/diversity_config.py
"""Diversity Penalty Configuration - 统一配置"""

# Jaccard similarity threshold (0.0-1.0)
# Experts with top-6 overlap > this threshold will be penalized
JACCARD_THRESHOLD = 0.80

# Penalty factor for correlated experts
# When similarity > JACCARD_THRESHOLD, weaker expert's weight is multiplied by this
JACCARD_PENALTY = 0.70

# Exploration configuration
EXPLORE_PROB_MIN = 0.05
EXPLORE_PROB_MAX = 0.20
ENTROPY_THRESHOLD = 2.2
