from app.data.offers import OFFER_LIBRARY
from app.data.providers import PROVIDER_LIBRARY


def get_offer_summary():
    total = len(OFFER_LIBRARY)
    active = sum(1 for item in OFFER_LIBRARY if item['status'] == 'active')
    high_confidence = sum(1 for item in OFFER_LIBRARY if item['verified'] and item['score'] >= 85)
    needs_review = sum(1 for item in OFFER_LIBRARY if not item['verified'])
    categories = sorted({item['category'] for item in OFFER_LIBRARY})
    return {
        'total_offers': total,
        'active_offers': active,
        'high_confidence': high_confidence,
        'needs_review': needs_review,
        'categories': categories,
    }


def get_offers():
    return OFFER_LIBRARY


def get_providers():
    return PROVIDER_LIBRARY


def get_research_status():
    total_sources = sum(provider['source_count'] for provider in PROVIDER_LIBRARY)
    active_providers = sum(1 for provider in PROVIDER_LIBRARY if provider['status'] == 'active')
    avg_coverage = round(sum(provider['research_coverage'] for provider in PROVIDER_LIBRARY) / len(PROVIDER_LIBRARY), 1)
    return {
        'total_sources': total_sources,
        'active_providers': active_providers,
        'last_scan': '2026-10-27T12:00:00Z',
        'coverage_percent': avg_coverage,
        'needs_review': sum(1 for provider in PROVIDER_LIBRARY if provider['status'] == 'monitoring'),
    }
