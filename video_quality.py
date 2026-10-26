"""Validated, persistent output profiles. Applied at application startup."""
import json
PROFILES = {'540p': (960, 540), '720p': (1280, 720), '1080p': (1920, 1080)}
def load_quality(storage):
    try:
        value = json.loads((storage/'video.json').read_text(encoding='utf-8')).get('quality')
        return value if value in PROFILES else '720p'
    except (OSError, ValueError, AttributeError, TypeError):
        return '720p'
def save_quality(storage, value):
    if value not in PROFILES:
        raise ValueError('Unsupported video quality')
    storage.mkdir(parents=True, exist_ok=True)
    temporary = storage/'video.tmp'
    temporary.write_text(json.dumps({'quality': value}), encoding='utf-8')
    temporary.replace(storage/'video.json')
