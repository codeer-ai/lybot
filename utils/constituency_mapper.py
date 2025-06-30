from typing import Optional

# Mapping between different constituency name formats
CONSTITUENCY_MAPPINGS = {
    # Taipei City - map various formats to official API format
    "台北市第一選區": "臺北市第1選舉區",
    "臺北市第一選區": "臺北市第1選舉區",
    "台北市第1選區": "臺北市第1選舉區",
    "臺北市第1選區": "臺北市第1選舉區",
    "台北市第二選區": "臺北市第2選舉區",
    "臺北市第二選區": "臺北市第2選舉區",
    "台北市第2選區": "臺北市第2選舉區",
    "臺北市第2選區": "臺北市第2選舉區",
    "台北市第三選區": "臺北市第3選舉區",
    "臺北市第三選區": "臺北市第3選舉區",
    "台北市第3選區": "臺北市第3選舉區",
    "臺北市第3選區": "臺北市第3選舉區",
    "台北市第四選區": "臺北市第4選舉區",
    "臺北市第四選區": "臺北市第4選舉區",
    "台北市第4選區": "臺北市第4選舉區",
    "臺北市第4選區": "臺北市第4選舉區",
    "台北市第五選區": "臺北市第5選舉區",
    "臺北市第五選區": "臺北市第5選舉區",
    "台北市第5選區": "臺北市第5選舉區",
    "臺北市第5選區": "臺北市第5選舉區",
    "台北市第六選區": "臺北市第6選舉區",
    "臺北市第六選區": "臺北市第6選舉區",
    "台北市第6選區": "臺北市第6選舉區",
    "臺北市第6選區": "臺北市第6選舉區",
    "台北市第七選區": "臺北市第7選舉區",
    "臺北市第七選區": "臺北市第7選舉區",
    "台北市第7選區": "臺北市第7選舉區",
    "臺北市第7選區": "臺北市第7選舉區",
    "台北市第八選區": "臺北市第8選舉區",
    "臺北市第八選區": "臺北市第8選舉區",
    "台北市第8選區": "臺北市第8選舉區",
    "臺北市第8選區": "臺北市第8選舉區",
    
    # Alternative names that people might use
    "臺北市北松山信義": "臺北市第7選舉區",
    "台北市北松山信義": "臺北市第7選舉區",
    "臺北市北松山‧信義": "臺北市第7選舉區",
    "台北市北松山‧信義": "臺北市第7選舉區",
}

def normalize_constituency(input_name: str) -> Optional[str]:
    """
    Normalize constituency name to match API format.
    
    Args:
        input_name: User input constituency name
        
    Returns:
        Normalized constituency name or None if not found
    """
    # Direct match
    if input_name in CONSTITUENCY_MAPPINGS:
        return CONSTITUENCY_MAPPINGS[input_name]
    
    # Try removing spaces and punctuation
    simplified = input_name.replace(" ", "").replace("，", "").replace("、", "‧")
    if simplified in CONSTITUENCY_MAPPINGS:
        return CONSTITUENCY_MAPPINGS[simplified]
    
    # Check if it's already in the correct format
    # (This would need to be validated against actual API data)
    if "‧" in input_name or "選區" not in input_name:
        return input_name
    
    # Try converting traditional/simplified
    traditional = input_name.replace("台", "臺")
    if traditional in CONSTITUENCY_MAPPINGS:
        return CONSTITUENCY_MAPPINGS[traditional]
    
    return None

def get_all_constituencies() -> list[str]:
    """Get all unique constituency names."""
    return list(set(CONSTITUENCY_MAPPINGS.values()))