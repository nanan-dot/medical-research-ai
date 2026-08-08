import pytest
from app.modules.feasibility.schema import DimensionScore
from app.modules.feasibility.scoring import calculate_score, ranking_changed

def _item(name, score, weight=1, source="system"):
 return DimensionScore(dimension=name,score=score,weight=weight,basis="依据",score_source=source)
def test_weighted_score_and_unknown_confidence():
 total, confidence, missing=calculate_score([_item("literature_base",80,2),_item("sample_availability",None,1,"unknown"),_item("data_availability",None,1,"unknown"),_item("timeline",None,1,"unknown")])
 assert total==80 and confidence=="low" and len(missing)==3
def test_zero_weights_are_excluded_and_empty_is_rejected():
 total,_,_=calculate_score([_item("literature_base",80,0),_item("technical_feasibility",60,1)])
 assert total==60
 with pytest.raises(ValueError): calculate_score([_item("literature_base",80,0)])
def test_weight_change_is_sensitive(): assert ranking_changed(60,61) and not ranking_changed(60,60)
