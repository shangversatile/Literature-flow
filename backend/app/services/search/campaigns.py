import logging

from app.schemas.search import PaperSearchResult
from app.schemas.search_campaign import SearchCampaign
from app.services.search.aggregator import dedupe_key, merge_results, search_all_sources


logger = logging.getLogger(__name__)

CAMPAIGNS = [
    SearchCampaign(
        name="AI Systems / Inference Systems",
        description="Curated seed queries for LLM inference, serving, batching, attention, and KV cache systems.",
        default_limit_per_query=8,
        queries=[
            "FlashAttention Fast and Memory-Efficient Exact Attention with IO-Awareness",
            "FlashAttention-2 Faster Attention with Better Parallelism and Work Partitioning",
            "Efficient Memory Management for Large Language Model Serving with PagedAttention",
            "Orca A Distributed Serving System for Transformer-Based Generative Models",
            "SpecInfer Accelerating Generative Large Language Model Serving",
            "Fast Inference from Transformers via Speculative Decoding",
            "KV cache optimization LLM serving",
            "continuous batching LLM serving",
            "LLM serving systems",
        ],
    ),
    SearchCampaign(
        name="Trustworthy AI Systems",
        description="Curated seed queries for evaluation, calibration, red teaming, truthfulness, and agent evaluation.",
        default_limit_per_query=8,
        queries=[
            "HELM Holistic Evaluation of Language Models",
            "BIG-bench Beyond the Imitation Game Benchmark",
            "TruthfulQA Measuring How Models Mimic Human Falsehoods",
            "Automatic Red Teaming Language Models",
            "Discovering Language Model Behaviors with Model-Written Evaluations",
            "LLM calibration uncertainty",
            "multi-turn agent evaluation",
        ],
    ),
    SearchCampaign(
        name="Mechanistic Interpretability",
        description="Curated seed queries for transformer circuits, superposition, sparse autoencoders, and causal tracing.",
        default_limit_per_query=8,
        queries=[
            "A Mathematical Framework for Transformer Circuits",
            "Toy Models of Superposition",
            "Towards Monosemanticity Decomposing Language Models With Dictionary Learning",
            "Sparse Autoencoders Find Highly Interpretable Features in Language Models",
            "activation patching language models",
            "causal tracing language models",
        ],
    ),
    SearchCampaign(
        name="Scientific ML / AI for Science",
        description="Curated seed queries for neural operators, physics-informed ML, protein structure, docking, and scientific foundation models.",
        default_limit_per_query=8,
        queries=[
            "Fourier Neural Operator",
            "DeepONet Learning nonlinear operators",
            "Physics-informed neural networks",
            "GraphCast",
            "AlphaFold",
            "DiffDock",
            "MACE equivariant message passing neural networks",
        ],
    ),
    SearchCampaign(
        name="Embodied AI / World Models",
        description="Curated seed queries for world models, robot transformers, VLA models, and embodied generalization.",
        default_limit_per_query=8,
        queries=[
            "World Models Ha Schmidhuber",
            "DreamerV3",
            "RT-1 Robotics Transformer",
            "RT-2 Vision-Language-Action Models",
            "SayCan Do As I Can",
            "Open X-Embodiment",
            "VIMA General Robot Manipulation",
        ],
    ),
]


def list_campaigns() -> list[SearchCampaign]:
    return CAMPAIGNS


def get_campaign(name: str) -> SearchCampaign | None:
    for campaign in CAMPAIGNS:
        if campaign.name == name:
            return campaign
    return None


def clamp_limit_per_query(limit: int) -> int:
    return min(max(limit, 1), 20)


async def run_campaign_queries(
    campaign: SearchCampaign,
    limit_per_query: int,
) -> tuple[int, list[PaperSearchResult]]:
    safe_limit = clamp_limit_per_query(limit_per_query)
    total_raw_results = 0
    merged_by_key: dict[str, PaperSearchResult] = {}

    for query in campaign.queries:
        try:
            results = await search_all_sources(query=query, limit=safe_limit)
        except Exception as exc:
            logger.warning("Campaign query failed: %s: %s", query, exc)
            continue

        total_raw_results += len(results)
        for result in results:
            key = dedupe_key(result)
            if key in ("title:", "doi:"):
                continue
            if key not in merged_by_key:
                merged_by_key[key] = result
            else:
                merge_results(merged_by_key[key], result)

    unique_results = list(merged_by_key.values())
    unique_results.sort(
        key=lambda result: (
            result.final_score or 0.0,
            result.foundation_score or 0.0,
            result.authority_score or 0.0,
            result.citation_count or 0,
            result.year or 0,
        ),
        reverse=True,
    )
    return total_raw_results, unique_results
