#!/usr/bin/env python3
"""
ESPHome Media Player Discovery Script
Queries Home Assistant API for ESPHome media players
"""
import os
import sys
import json
import requests
from typing import List, Dict

SUPERVISOR_TOKEN = os.environ.get('SUPERVISOR_TOKEN')
HA_API_URL = 'http://supervisor/core/api'

def get_headers():
    """Get authorization headers for HA API"""
    return {
        'Authorization': f'Bearer {SUPERVISOR_TOKEN}',
        'Content-Type': 'application/json',
    }

def discover_esphome_players() -> List[Dict]:
    """
    Discover ESPHome media players via Home Assistant API
    Returns list of media player entities
    """
    def fetch_entity_registry_media_players() -> List[str]:
        """Fetch media_player entities backed by the ESPHome integration."""
        endpoints = (
            ("POST", f"{HA_API_URL}/config/entity_registry/list", {}),
            ("GET", f"{HA_API_URL}/config/entity_registry", None),
        )

        for method, url, payload in endpoints:
            try:
                if method == "POST":
                    response = requests.post(
                        url,
                        headers=get_headers(),
                        json=payload,
                        timeout=10,
                    )
                else:
                    response = requests.get(
                        url,
                        headers=get_headers(),
                        timeout=10,
                    )

                if response.status_code == 405:
                    # Method not allowed, try the next approach
                    continue

                response.raise_for_status()
                payload_json = response.json()

                if isinstance(payload_json, dict):
                    entries = (
                        payload_json.get('data')
                        or payload_json.get('entries')
                        or payload_json.get('result', {}).get('data', [])
                    )
                elif isinstance(payload_json, list):
                    entries = payload_json
                else:
                    entries = []

                esphome_entities = [
                    entry.get('entity_id')
                    for entry in entries
                    if isinstance(entry, dict)
                    and entry.get('entity_id', '').startswith('media_player.')
                    and entry.get('platform') == 'esphome'
                ]

                if esphome_entities:
                    return esphome_entities

            except requests.exceptions.RequestException as err:
                print(f"Warning: Entity registry query failed ({method} {url}): {err}", file=sys.stderr)
            except Exception as err:  # pragma: no cover - defensive
                print(f"Warning: Unexpected error parsing entity registry response: {err}", file=sys.stderr)

        return []

    esphome_registry_entities = set(fetch_entity_registry_media_players())

    try:
        # Get all states
        response = requests.get(
            f'{HA_API_URL}/states',
            headers=get_headers(),
            timeout=10
        )
        response.raise_for_status()
        states = response.json()
        
        # Filter for ESPHome media players
        esphome_players = []
        for entity in states:
            entity_id = entity.get('entity_id', '')
            attributes = entity.get('attributes', {})
            
            # Check if it's a media player from ESPHome
            if not entity_id.startswith('media_player.'):
                continue

            attribution = attributes.get('attribution')
            if (
                attribution == 'ESPHome'
                or entity_id in esphome_registry_entities
                or attributes.get('platform') == 'esphome'
            ):
                
                esphome_players.append({
                    'entity_id': entity_id,
                    'friendly_name': attributes.get('friendly_name', entity_id),
                    'state': entity.get('state'),
                    'supported_features': attributes.get('supported_features', 0)
                })
        
        return esphome_players
        
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Home Assistant API: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error discovering ESPHome players: {e}", file=sys.stderr)
        return []

def main():
    """Main function"""
    if not SUPERVISOR_TOKEN:
        print("ERROR: SUPERVISOR_TOKEN not available", file=sys.stderr)
        print(json.dumps([]))
        sys.exit(0)
    
    players = discover_esphome_players()
    
    if not players:
        print("No ESPHome media players found", file=sys.stderr)
        print(json.dumps([]))
        sys.exit(0)
    
    print(f"Found {len(players)} ESPHome media player(s):")
    for player in players:
        print(f"  - {player['friendly_name']} ({player['entity_id']})")
    
    # Output as JSON for consumption by other scripts
    print(json.dumps(players, indent=2))

if __name__ == '__main__':
    main()
