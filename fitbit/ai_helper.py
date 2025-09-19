import os
import logging
import json

logger = logging.getLogger(__name__)


def _stub_response(partner_name: str, comparison: dict) -> dict:
    ansr = comparison.get('ansr')
    hours = comparison.get('hours')
    ansr_diff = comparison.get('ansr_diff')
    hours_diff = comparison.get('hours_diff')

    summary = f"Partner: {partner_name}\nANSR: {ansr} (diff {ansr_diff})\nHours: {hours} (diff {hours_diff})"
    if ansr_diff is not None and ansr_diff < 0:
        suggestion = "Revisar asignación de recursos y reasignar horas a engagements claves."
    else:
        suggestion = "Mantener plan actual y monitorizar semanalmente."

    return {
        'summary': summary,
        'suggestion': suggestion,
        'raw_prompt': f"Analiza y propone acciones para {partner_name} con datos: {json.dumps(comparison)}",
    }


def generate_analysis(partner_name: str, comparison: dict) -> dict:
    """Generate an analysis and suggested solution for a partner.

    If `GOOGLE_API_KEY` is present in the environment, this function will attempt
    to call a (placeholder) Google API endpoint. Currently the project contains
    a safe stub fallback which is used when no API key or on any error.
    """
    google_key = os.environ.get('GOOGLE_API_KEY')
    if not google_key:
        logger.debug('No GOOGLE_API_KEY found, using stub analysis')
        return _stub_response(partner_name, comparison)

    # Placeholder for actual Google API integration. Many Google APIs require
    # specific client libraries and endpoints; integrate here when chosen.
    try:
        logger.debug('GOOGLE_API_KEY found — but no concrete integration implemented, using stub')
        # Example: call to a Google LLM or Vertex AI would go here
        return _stub_response(partner_name, comparison)
    except Exception as e:
        logger.exception('AI call failed, falling back to stub')
        return _stub_response(partner_name, comparison)

