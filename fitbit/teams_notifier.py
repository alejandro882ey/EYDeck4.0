import os
import logging
import requests

logger = logging.getLogger(__name__)

def send_message(webhook_url: str, title: str, text: str):
    if not webhook_url:
        logger.info('TEAMS WEBHOOK not configured — would send: %s\n%s', title, text)
        return {'status': 'logged'}

    payload = {
        '@type': 'MessageCard',
        '@context': 'http://schema.org/extensions',
        'summary': title,
        'title': title,
        'text': text,
    }
    try:
        r = requests.post(webhook_url, json=payload, timeout=10)
        r.raise_for_status()
        return {'status': 'sent', 'http_status': r.status_code}
    except Exception as e:
        logger.exception('Failed to send Teams message')
        return {'status': 'error', 'error': str(e)}
