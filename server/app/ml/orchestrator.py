import time
import hashlib
import json
from typing import Dict, List, Optional, Any, Set, Tuple
from app.ml.constraints import load_game_data, to_canonical_id, get_pokemon_species
from app.ml.data_loader import load_and_clean_data
from app.ml.model import ArchetypeModel, explain_prediction
from app.ml.synergy import analyze_team_synergy
from app.ml.recommender import recommend_moveset
from app.ml.optimizer import optimize_team
from app.core.config import settings
from app.core.utils import get_pokemon_data

class FeatureStep:
    def __init__(self, step_id: str, name: str, dependencies: List[str], description: str):
        self.step_id = step_id
        self.name = name
        self.dependencies = dependencies
        self.description = description

# Explicit Topological Dependency DAG
FEATURE_REGISTRY: List[FeatureStep] = [
    FeatureStep(
        step_id="team_validation",
        name="Team Validation & Canonicalization",
        dependencies=[],
        description="Validates team size, species existence in Pokédex, and formats canonical IDs."
    ),
    FeatureStep(
        step_id="archetype_prediction",
        name="Archetype Prediction (ML)",
        dependencies=["team_validation"],
        description="Predicts overarching team archetype (Rain, Sun, Trick Room, Hyper Offense, etc.) with feature explanations."
    ),
    FeatureStep(
        step_id="team_synergy",
        name="Team Synergy Analysis",
        dependencies=["team_validation"],
        description="Evaluates defensive weaknesses, offensive physical/special splits, and strategic synergies."
    ),
    FeatureStep(
        step_id="moveset_recommendation",
        name="Context-Aware Moveset & Item Recommender",
        dependencies=["team_validation", "archetype_prediction", "team_synergy"],
        description="Derives 4-move sets, prioritized items, and ability recommendations tailored to team strategy."
    ),
    FeatureStep(
        step_id="team_optimizer",
        name="Team Optimizer & Replacement Engine",
        dependencies=["team_validation", "team_synergy", "archetype_prediction"],
        description="Audits team gaps and generates candidate replacements to maximize synergy score."
    ),
]

def compute_hash(data: Any) -> str:
    """Computes a deterministic MD5/SHA256 hex digest for state tracking and invalidation."""
    try:
        serialized = json.dumps(data, sort_keys=True, default=str)
    except Exception:
        serialized = str(data)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

class PipelineOrchestrator:
    """
    Deterministic Dependency-Aware Pipeline Orchestration Engine.
    Executes features in topological DAG order with change detection and smart invalidation.
    """

    def __init__(self):
        self.model = None
        self.df_pokemon = None
        self.df_types = None
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _ensure_data_loaded(self):
        if self.df_pokemon is None or self.df_types is None or self.model is None:
            load_game_data()
            self.df_pokemon, self.df_types = load_and_clean_data(settings.POKEMON_CSV, settings.TYPES_CSV)
            self.model = ArchetypeModel(settings.MODEL_PATH, settings.ENCODER_PATH)

    def run_all(
        self,
        team: List[str],
        format_name: str = "gen9ou",
        target_archetype: Optional[str] = None,
        cached_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes all PokeSync features in dependency-aware order.
        Returns execution trace with status, duration, invalidation reasons, and combined output.
        """
        self._ensure_data_loaded()
        cached_state = cached_state or {}
        
        trace = []
        results = {}
        updated_cache = dict(cached_state)
        invalidated_steps: Set[str] = set()

        # Step 1: Team Validation
        step_def = FEATURE_REGISTRY[0]
        start_time = time.perf_counter()
        val_input_hash = compute_hash({"team": sorted(team), "format": format_name})
        prev_val_hash = cached_state.get("team_validation_hash")
        
        is_invalidated = (val_input_hash != prev_val_hash)
        if is_invalidated:
            invalidated_steps.add("team_validation")
            reason = "Team roster or format changed"
        else:
            reason = "Inputs unchanged (using cached result)"

        # Run Validation
        normalized_team = [p.lower().replace(" ", "-") for p in team]
        valid_names = set(self.df_pokemon["name"])
        invalid = [p for p in normalized_team if p not in valid_names]

        if len(team) != 6:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            trace.append({
                "order": 1,
                "step_id": step_def.step_id,
                "name": step_def.name,
                "status": "failed",
                "duration_ms": duration_ms,
                "executed": True,
                "invalidated": True,
                "invalidation_reason": "Invalid team size",
                "dependencies": step_def.dependencies,
                "error": "Team must contain exactly 6 Pokémon."
            })
            return {"success": False, "error": "Team must contain exactly 6 Pokémon.", "trace": trace, "results": {}}

        if invalid:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            trace.append({
                "order": 1,
                "step_id": step_def.step_id,
                "name": step_def.name,
                "status": "failed",
                "duration_ms": duration_ms,
                "executed": True,
                "invalidated": True,
                "invalidation_reason": f"Unknown Pokémon: {invalid}",
                "dependencies": step_def.dependencies,
                "error": f"Invalid Pokémon in team: {invalid}"
            })
            return {"success": False, "error": f"Invalid Pokémon: {invalid}", "trace": trace, "results": {}}

        team_data = get_pokemon_data(normalized_team, self.df_pokemon)
        val_result = {
            "normalized_team": normalized_team,
            "team_data": team_data,
            "format": format_name
        }
        results["validation"] = val_result
        updated_cache["team_validation_hash"] = val_input_hash
        updated_cache["team_validation_result"] = val_result
        
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        trace.append({
            "order": 1,
            "step_id": step_def.step_id,
            "name": step_def.name,
            "status": "completed",
            "duration_ms": duration_ms,
            "executed": True,
            "invalidated": is_invalidated,
            "invalidation_reason": reason if is_invalidated else "Validated",
            "dependencies": step_def.dependencies
        })

        # Step 2: Archetype Prediction
        step_def = FEATURE_REGISTRY[1]
        start_time = time.perf_counter()
        arch_input_hash = compute_hash(normalized_team)
        prev_arch_hash = cached_state.get("archetype_hash")
        
        arch_invalid = ("team_validation" in invalidated_steps) or (arch_input_hash != prev_arch_hash)
        if arch_invalid:
            invalidated_steps.add("archetype_prediction")
            pred_res = self.model.predict(normalized_team, self.df_pokemon)
            explanations = explain_prediction(normalized_team, pred_res["features"]) if pred_res else []
            arch_result = {
                "prediction": pred_res["prediction"] if pred_res else "balance",
                "probabilities": pred_res["probabilities"] if pred_res else {},
                "explanations": explanations
            }
            updated_cache["archetype_hash"] = arch_input_hash
            updated_cache["archetype_result"] = arch_result
            executed = True
            reason = "Team composition changed"
        else:
            arch_result = cached_state.get("archetype_result", {})
            executed = False
            reason = "No upstream changes; used cached prediction"

        results["archetype"] = arch_result
        predicted_arch = arch_result.get("prediction", "balance")
        effective_arch = target_archetype or predicted_arch
        
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        trace.append({
            "order": 2,
            "step_id": step_def.step_id,
            "name": step_def.name,
            "status": "completed" if executed else "skipped",
            "duration_ms": duration_ms,
            "executed": executed,
            "invalidated": arch_invalid,
            "invalidation_reason": reason,
            "dependencies": step_def.dependencies
        })

        # Step 3: Team Synergy
        step_def = FEATURE_REGISTRY[2]
        start_time = time.perf_counter()
        synergy_input_hash = compute_hash(normalized_team)
        prev_synergy_hash = cached_state.get("synergy_hash")
        
        synergy_invalid = ("team_validation" in invalidated_steps) or (synergy_input_hash != prev_synergy_hash)
        if synergy_invalid:
            invalidated_steps.add("team_synergy")
            synergy_data = analyze_team_synergy(normalized_team, self.df_pokemon, self.df_types)
            updated_cache["synergy_hash"] = synergy_input_hash
            updated_cache["synergy_result"] = synergy_data
            executed = True
            reason = "Team roster changed"
        else:
            synergy_data = cached_state.get("synergy_result", {})
            executed = False
            reason = "No upstream changes; used cached synergy"

        results["synergy"] = synergy_data
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        trace.append({
            "order": 3,
            "step_id": step_def.step_id,
            "name": step_def.name,
            "status": "completed" if executed else "skipped",
            "duration_ms": duration_ms,
            "executed": executed,
            "invalidated": synergy_invalid,
            "invalidation_reason": reason,
            "dependencies": step_def.dependencies
        })

        # Step 4: Moveset Recommendation (for all 6 members)
        step_def = FEATURE_REGISTRY[3]
        start_time = time.perf_counter()
        moveset_input_hash = compute_hash({
            "team": normalized_team,
            "arch": effective_arch,
            "format": format_name
        })
        prev_moveset_hash = cached_state.get("moveset_hash")
        
        moveset_invalid = ("archetype_prediction" in invalidated_steps or "team_synergy" in invalidated_steps or moveset_input_hash != prev_moveset_hash)
        if moveset_invalid:
            invalidated_steps.add("moveset_recommendation")
            team_movesets = {}
            for mon in normalized_team:
                teammates = [t for t in normalized_team if t != mon]
                rec = recommend_moveset(
                    pokemon_name=mon,
                    teammates=teammates,
                    archetype=effective_arch,
                    format_name=format_name,
                    top_n=4
                )
                team_movesets[mon] = rec
                
            updated_cache["moveset_hash"] = moveset_input_hash
            updated_cache["moveset_result"] = team_movesets
            executed = True
            reason = "Archetype or synergy changed" if ("archetype_prediction" in invalidated_steps or "team_synergy" in invalidated_steps) else "Strategy parameters changed"
        else:
            team_movesets = cached_state.get("moveset_result", {})
            executed = False
            reason = "No changes to strategy or synergy; used cached movesets"

        results["movesets"] = team_movesets
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        trace.append({
            "order": 4,
            "step_id": step_def.step_id,
            "name": step_def.name,
            "status": "completed" if executed else "skipped",
            "duration_ms": duration_ms,
            "executed": executed,
            "invalidated": moveset_invalid,
            "invalidation_reason": reason,
            "dependencies": step_def.dependencies
        })

        # Step 5: Team Optimizer
        step_def = FEATURE_REGISTRY[4]
        start_time = time.perf_counter()
        opt_input_hash = compute_hash({
            "team": normalized_team,
            "format": format_name,
            "arch": effective_arch
        })
        prev_opt_hash = cached_state.get("optimizer_hash")
        
        opt_invalid = ("team_synergy" in invalidated_steps or "archetype_prediction" in invalidated_steps or opt_input_hash != prev_opt_hash)
        if opt_invalid:
            invalidated_steps.add("team_optimizer")
            opt_res = optimize_team(
                team=normalized_team,
                df_pokemon=self.df_pokemon,
                df_types=self.df_types,
                format_name=format_name,
                target_archetype=effective_arch
            )
            updated_cache["optimizer_hash"] = opt_input_hash
            updated_cache["optimizer_result"] = opt_res
            executed = True
            reason = "Team synergy or strategy changed"
        else:
            opt_res = cached_state.get("optimizer_result", {})
            executed = False
            reason = "No upstream changes; used cached optimization"

        results["optimizer"] = opt_res
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        trace.append({
            "order": 5,
            "step_id": step_def.step_id,
            "name": step_def.name,
            "status": "completed" if executed else "skipped",
            "duration_ms": duration_ms,
            "executed": executed,
            "invalidated": opt_invalid,
            "invalidation_reason": reason,
            "dependencies": step_def.dependencies
        })

        return {
            "success": True,
            "format": format_name,
            "target_archetype": effective_arch,
            "trace": trace,
            "results": results,
            "cache_state": updated_cache
        }

# Global singleton orchestrator
orchestrator = PipelineOrchestrator()
