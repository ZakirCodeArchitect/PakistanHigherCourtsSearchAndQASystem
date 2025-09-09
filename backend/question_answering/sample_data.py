"""
Sample legal data for testing the QA system
"""

SAMPLE_LEGAL_DATA = [
    {
        'title': 'Bail Law in Pakistan',
        'content': 'Under Pakistani law, bail is a fundamental right. The Constitution of Pakistan guarantees the right to liberty. Bail can be granted in bailable and non-bailable offenses. For bailable offenses, bail is a matter of right, while for non-bailable offenses, it is at the discretion of the court. The court considers factors such as the nature of the offense, the character of the accused, and the likelihood of the accused appearing for trial.',
        'court': 'Supreme Court of Pakistan',
        'case_number': 'PLD 2023 SC 1',
        'category': 'Criminal Law',
        'keywords': ['bail', 'liberty', 'constitution', 'criminal law', 'fundamental right']
    },
    {
        'title': 'Writ Petition Procedure',
        'content': 'A writ petition is a formal written application to a court requesting judicial action. In Pakistan, writ petitions are filed under Article 199 of the Constitution. The procedure involves filing a petition with proper cause of action, supporting documents, and court fees. The petition must be supported by an affidavit and should clearly state the facts and legal grounds for relief.',
        'court': 'High Court',
        'case_number': 'W.P. No. 1234/2023',
        'category': 'Constitutional Law',
        'keywords': ['writ petition', 'article 199', 'constitution', 'judicial review', 'affidavit']
    },
    {
        'title': 'Constitutional Rights',
        'content': 'The Constitution of Pakistan guarantees fundamental rights including right to life, liberty, equality, freedom of speech, and freedom of religion. These rights are enforceable through the courts and any law inconsistent with fundamental rights is void. The Supreme Court has the power to strike down any law that violates fundamental rights.',
        'court': 'Supreme Court of Pakistan',
        'case_number': 'PLD 2022 SC 45',
        'category': 'Constitutional Law',
        'keywords': ['fundamental rights', 'constitution', 'life', 'liberty', 'equality', 'freedom of speech']
    },
    {
        'title': 'Criminal Appeal Procedure',
        'content': 'Criminal appeals in Pakistan are governed by the Code of Criminal Procedure. An appeal can be filed against conviction or sentence within 30 days. The appellate court can confirm, reverse, or modify the judgment of the lower court. The appeal must be filed with proper grounds and supporting documents.',
        'court': 'Sessions Court',
        'case_number': 'Crl. A. No. 567/2023',
        'category': 'Criminal Law',
        'keywords': ['criminal appeal', 'conviction', 'sentence', 'criminal procedure', 'appellate court']
    },
    {
        'title': 'Property Rights in Pakistan',
        'content': 'Property rights in Pakistan are protected under the Constitution and various laws. The right to property is a fundamental right, though it can be restricted for public purposes with compensation. The Transfer of Property Act governs the transfer of immovable property, while the Registration Act requires registration of certain documents.',
        'court': 'High Court',
        'case_number': 'C.P. No. 890/2023',
        'category': 'Property Law',
        'keywords': ['property rights', 'constitution', 'fundamental right', 'transfer of property', 'registration']
    },
    {
        'title': 'Family Law - Marriage and Divorce',
        'content': 'Family law in Pakistan is governed by various statutes including the Muslim Family Laws Ordinance. Marriage is a civil contract that requires offer, acceptance, and witnesses. Divorce can be initiated by either spouse, and the court can grant divorce on various grounds including cruelty, desertion, and incompatibility.',
        'court': 'Family Court',
        'case_number': 'F.C. No. 234/2023',
        'category': 'Family Law',
        'keywords': ['family law', 'marriage', 'divorce', 'muslim family laws', 'civil contract']
    }
]

def get_sample_data():
    """Return sample legal data"""
    return SAMPLE_LEGAL_DATA

def search_sample_data(query):
    """Simple search through sample data"""
    query_lower = query.lower()
    results = []
    
    # Extract key terms from query
    query_terms = query_lower.split()
    
    for doc in SAMPLE_LEGAL_DATA:
        score = 0
        doc_text = (doc['title'] + ' ' + doc['content'] + ' ' + ' '.join(doc['keywords'])).lower()
        
        # Check for exact phrase match
        if query_lower in doc_text:
            score += 5
        
        # Check for individual word matches
        for term in query_terms:
            if len(term) > 2:  # Only consider words longer than 2 characters
                if term in doc['title'].lower():
                    score += 3
                if term in doc['content'].lower():
                    score += 2
                if term in ' '.join(doc['keywords']).lower():
                    score += 1
        
        # Special handling for common legal terms
        legal_terms = {
            'writ': ['writ petition', 'article 199'],
            'bail': ['bail', 'liberty'],
            'constitution': ['constitutional', 'fundamental rights'],
            'appeal': ['criminal appeal', 'appellate'],
            'property': ['property rights', 'transfer'],
            'family': ['family law', 'marriage', 'divorce']
        }
        
        for term, synonyms in legal_terms.items():
            if term in query_lower:
                for synonym in synonyms:
                    if synonym in doc_text:
                        score += 2
        
        if score > 0:
            results.append({
                'document': doc,
                'score': score,
                'relevance': min(score / 8, 1.0)  # Normalize to 0-1
            })
    
    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:3]  # Return top 3 results
