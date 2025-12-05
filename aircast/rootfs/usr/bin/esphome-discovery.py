#!/usr/bin/env python3
"""
ESPHome Media Player Discovery Script
Queries Home Assistant API for ESPHome media players
"""
import os
import sys
import json
import requests
from typing import List, Dict, Any, Optional

EntityRegistryEntry = Dict[str, Any]

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
    entity_registry_cache: Dict[str, EntityRegistryEntry] = {}
    diagnostics_cache: Dict[str, List[Dict[str, Any]]] = {}

    def normalize_registry_payload(payload_json: Any) -> List[Dict]:
        """Normalize entity registry payload into a list of entries."""
        if isinstance(payload_json, list):
            return payload_json
        if isinstance(payload_json, dict):
            data = payload_json.get('data')
            if isinstance(data, list):
                return data
            result = payload_json.get('result')
            if isinstance(result, dict):
                result_data = result.get('data')
                if isinstance(result_data, list):
                    return result_data
            entries = payload_json.get('entries')
            if isinstance(entries, list):
                return entries
        return []

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
                entries = normalize_registry_payload(payload_json)

                esphome_entities = [
                    entry.get('entity_id')
                    for entry in entries
                    if isinstance(entry, dict)
                    and entry.get('entity_id', '').startswith('media_player.')
                    and entry.get('platform') == 'esphome'
                ]

                for entry in entries:
                    if isinstance(entry, dict) and entry.get('entity_id'):
                        entity_registry_cache[entry['entity_id']] = entry

                if esphome_entities:
                    return esphome_entities

            except requests.exceptions.RequestException as err:
                print(f"Warning: Entity registry query failed ({method} {url}): {err}", file=sys.stderr)
            except Exception as err:  # pragma: no cover - defensive
                print(f"Warning: Unexpected error parsing entity registry response: {err}", file=sys.stderr)

        return []

    esphome_registry_entities = set(fetch_entity_registry_media_players())

    def fetch_esphome_supported_formats(config_entry_id: Optional[str]) -> List[Dict[str, Any]]:
        """Retrieve ESPHome supported audio formats via HA diagnostics endpoint."""
        if not config_entry_id:
            return []

        if config_entry_id in diagnostics_cache:
            return diagnostics_cache[config_entry_id]

        url = f"{HA_API_URL}/diagnostics/config_entry/{config_entry_id}"
        try:
            response = requests.get(
                url,
                headers=get_headers(),
                timeout=10,
            )
            if response.status_code == 404:
                # Diagnostics not available for this entry.
                diagnostics_cache[config_entry_id] = []
                return []

            response.raise_for_status()
            payload = response.json()
            data = payload.get('data') if isinstance(payload, dict) else None
            storage = data.get('storage_data') if isinstance(data, dict) else None
            media_players = storage.get('media_player') if isinstance(storage, dict) else None

            supported_formats: List[Dict[str, Any]] = []
            if isinstance(media_players, list):
                for media_player in media_players:
                    formats = media_player.get('supported_formats') if isinstance(media_player, dict) else None
                    if isinstance(formats, list):
                        for fmt in formats:
                            if isinstance(fmt, dict):
                                supported_formats.append(fmt)

            diagnostics_cache[config_entry_id] = supported_formats
            return supported_formats

        except requests.exceptions.RequestException as err:
            print(f"Warning: Failed to fetch diagnostics for {config_entry_id}: {err}", file=sys.stderr)
        except Exception as err:  # pragma: no cover - defensive
            print(f"Warning: Unexpected diagnostics error for {config_entry_id}: {err}", file=sys.stderr)

        diagnostics_cache[config_entry_id] = []
        return []

    def fetch_single_registry_entry(entity_id: str) -> Optional[EntityRegistryEntry]:
        if entity_id in entity_registry_cache:
            return entity_registry_cache[entity_id]

        try:
            response = requests.post(
                f'{HA_API_URL}/config/entity_registry/get',
                headers=get_headers(),
                json={'entity_id': entity_id},
                timeout=10,
            )

            if response.status_code == 405:
                response = requests.get(
                    f'{HA_API_URL}/config/entity_registry/entity/{entity_id}',
                    headers=get_headers(),
                    timeout=10,
                )

            if response.ok:
                payload_json = response.json()
                if isinstance(payload_json, dict):
                    entry: Any = payload_json.get('data') if 'data' in payload_json else payload_json
                    if isinstance(entry, dict):
                        entity_registry_cache[entity_id] = entry
                        return entry

        except requests.exceptions.RequestException as err:
            print(f"Warning: Failed to get registry entry for {entity_id}: {err}", file=sys.stderr)
        except Exception as err:  # pragma: no cover - defensive
            print(f"Warning: Unexpected error retrieving registry entry for {entity_id}: {err}", file=sys.stderr)

        return None

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
            registry_entry = fetch_single_registry_entry(entity_id)
            platform = registry_entry.get('platform') if isinstance(registry_entry, dict) else None
            config_entry_id = (
                registry_entry.get('config_entry_id')
                if isinstance(registry_entry, dict)
                else None
            )
            if (
                attribution == 'ESPHome'
                or entity_id in esphome_registry_entities
                or attributes.get('platform') == 'esphome'
                or platform == 'esphome'
            ):

                supported_formats = fetch_esphome_supported_formats(config_entry_id)

                esphome_players.append({
                    'entity_id': entity_id,
                    'friendly_name': attributes.get('friendly_name', entity_id),
                    'state': entity.get('state'),
                    'supported_features': attributes.get('supported_features', 0),
                    'config_entry_id': config_entry_id,
                    'esphome_supported_formats': supported_formats,
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
