from experiments.multivector.utils import VectorPlan


def test_estimates_storage_without_building_production_index():
    plan = VectorPlan(("title", "abstract"), 384, 10)
    assert plan.estimated_vector_count() == 20 and plan.estimated_bytes() == 20 * 384 * 4

def test_rejects_invalid_or_duplicate_fields():
    try: VectorPlan(("title", "title"), 384, 1)
    except ValueError: pass
    else: raise AssertionError("duplicate fields must fail")

def test_report_keeps_metrics_explicitly_optional():
    report = VectorPlan(("abstract",), 384, 1).report()
    assert report["recall_at_k"] is None and report["estimated_vectors"] == 1
