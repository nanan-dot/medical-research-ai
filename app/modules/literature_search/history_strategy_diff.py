"""策略修订差异计算；只比较持久化事实。"""
def build_strategy_diff(previous:dict[str,object],current:dict[str,object])->dict[str,object]:
    changes:dict[str,object]={}
    for field in ("original_query","search_string","filters","model_version","term_groups","mesh_terms","start_year","end_year"):
        if previous.get(field)!=current.get(field): changes[field]={"from":previous.get(field),"to":current.get(field)}
    return changes


