import numpy as np
import logging
from typing import List, Tuple, Optional, Dict, Any
from ..database import load_all_enrolled_templates_sync

logger = logging.getLogger(__name__)

class MultiTemplateVectorMatcher:
    """
    In-memory vectorized BLAS cosine similarity matcher.
    Supports multi-template matching per user (Front, Left, Right, Aggregate) in <0.4ms.
    """
    def __init__(self):
        self.user_ids: List[int] = []
        self.labels: List[str] = []
        self.embedding_matrix: np.ndarray = np.empty((0, 512), dtype=np.float32)
        self.reload()

    def reload(self):
        """Reload all active user embeddings from database into RAM."""
        try:
            self.user_ids, self.labels, self.embedding_matrix = load_all_enrolled_templates_sync()
            logger.info(f"Loaded {len(self.labels)} templates across {len(set(self.user_ids))} users into RAM vector index.")
        except Exception as e:
            logger.error(f"Error loading templates into vector matcher: {e}")
            self.user_ids = []
            self.labels = []
            self.embedding_matrix = np.empty((0, 512), dtype=np.float32)

    def match_single(self, query_embedding: np.ndarray, threshold: float = 0.68) -> Tuple[Optional[int], str, float, List[Dict[str, Any]]]:
        """
        Matches a single 512-d normalized embedding against all enrolled templates.
        Returns:
            (best_user_id, best_label, max_similarity, top_matches_list)
        """
        if len(self.user_ids) == 0 or self.embedding_matrix.shape[0] == 0:
            return None, "Unknown", 0.0, []

        # Vectorized dot product (Cosine Similarity since both vectors are L2-normalized)
        similarities = np.dot(self.embedding_matrix, query_embedding)

        # Aggregate by User ID (take max similarity across all angles for each user)
        unique_users = {}
        for idx, u_id in enumerate(self.user_ids):
            sim = float(similarities[idx])
            lbl = self.labels[idx]
            if u_id not in unique_users or sim > unique_users[u_id]["similarity"]:
                unique_users[u_id] = {
                    "user_id": u_id,
                    "label": lbl,
                    "similarity": sim
                }

        # Sort users by similarity descending
        sorted_users = sorted(unique_users.values(), key=lambda x: x["similarity"], reverse=True)
        top_matches = sorted_users[:5]

        best_match = sorted_users[0]
        if best_match["similarity"] >= threshold:
            # Ambiguity guard: verify top candidate is distinct if multiple people pass threshold
            if len(sorted_users) > 1 and sorted_users[1]["similarity"] >= threshold:
                margin = best_match["similarity"] - sorted_users[1]["similarity"]
                if margin < 0.05:
                    return None, "Unknown", best_match["similarity"], top_matches

            return best_match["user_id"], best_match["label"], best_match["similarity"], top_matches
        else:
            return None, "Unknown", best_match["similarity"], top_matches
