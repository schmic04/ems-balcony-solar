"""
SMARD API Modul

Dieses Modul enthält Funktionen zum Abrufen und Verwalten von Daten der SMARD-API.
Es unterstützt sowohl den direkten Abruf aus dem Internet als auch die lokale Speicherung
und Wiederverwendung von Daten.

Author: Generated from Jupyter Notebook
Date: 2025-09-14
"""

import requests
import json
import os
import pandas as pd
from datetime import datetime, timedelta, date
from pathlib import Path

# Globale Variablen (werden beim Import gesetzt)
local_enable = False
local_data_dir = "smard_data"


def set_config(enable_local=False, data_dir="smard_data"):
    """
    Konfiguriert die globalen Einstellungen für das Modul
    
    Args:
        enable_local (bool): True = lokale Daten verwenden, False = Netz-Daten verwenden
        data_dir (str): Verzeichnis für lokale JSON-Dateien
    """
    global local_enable, local_data_dir
    local_enable = enable_local
    local_data_dir = data_dir
    
    # Stelle sicher, dass das lokale Verzeichnis existiert
    if not os.path.exists(local_data_dir):
        os.makedirs(local_data_dir)
        print(f"Verzeichnis '{local_data_dir}' wurde erstellt.")


def save_timestamps_to_file(timestamps, filter_param, region, resolution):
    """
    Speichert Zeitstempel in eine lokale JSON-Datei
    
    Args:
        timestamps (list): Liste der Zeitstempel
        filter_param (str): Filter-Parameter
        region (str): Region
        resolution (str): Zeitauflösung
    
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    filename = f"{local_data_dir}/timestamps_{filter_param}_{region}_{resolution}.json"
    data = {
        'filter': filter_param,
        'region': region, 
        'resolution': resolution,
        'timestamps': timestamps,
        'saved_at': datetime.now().isoformat()
    }
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Zeitstempel gespeichert in: {filename}")
        return True
    except Exception as e:
        print(f"Fehler beim Speichern der Zeitstempel: {e}")
        return False


def load_timestamps_from_file(filter_param, region, resolution):
    """
    Lädt Zeitstempel aus einer lokalen JSON-Datei
    
    Args:
        filter_param (str): Filter-Parameter
        region (str): Region
        resolution (str): Zeitauflösung
    
    Returns:
        list: Liste der Zeitstempel oder leere Liste bei Fehler
    """
    filename = f"{local_data_dir}/timestamps_{filter_param}_{region}_{resolution}.json"
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Zeitstempel geladen aus: {filename}")
        print(f"Gespeichert am: {data.get('saved_at', 'Unbekannt')}")
        return data.get('timestamps', [])
    except FileNotFoundError:
        print(f"Lokale Datei nicht gefunden: {filename}")
        return []
    except Exception as e:
        print(f"Fehler beim Laden der Zeitstempel: {e}")
        return []


def fetch_smard_timestamps(filter_param, region, resolution):
    """
    Lädt Zeitstempel von der SMARD API oder aus lokaler Datei
    
    Args:
        filter_param (str): Filter-Parameter (z.B. "1223" für Stromerzeugung)
        region (str): Region (z.B. "DE" für Deutschland)
        resolution (str): Zeitauflösung (z.B. "hour", "day", "week", "month", "year")
    
    Returns:
        list: Liste der verfügbaren Zeitstempel
    """
    # Prüfe ob lokale Daten verwendet werden sollen
    if local_enable:
        print("=== Verwende lokale Zeitstempel-Daten ===")
        timestamps = load_timestamps_from_file(filter_param, region, resolution)
        if timestamps:
            print(f"Erfolgreich geladen! Anzahl Zeitstempel: {len(timestamps)}")
            return timestamps
        else:
            print("Keine lokalen Daten gefunden, lade aus dem Netz...")
    
    # Lade aus dem Netz
    print("=== Lade Zeitstempel aus dem Netz ===")
    url = f"https://www.smard.de/app/chart_data/{filter_param}/{region}/index_{resolution}.json"
    
    try:
        print(f"Lade Daten von: {url}")
        
        # HTTP-Request senden
        response = requests.get(url)
        response.raise_for_status()  # Fehler bei HTTP-Statuscodes >= 400
        
        # JSON-Daten parsen
        data = response.json()
        timestamps = data.get('timestamps', [])
        
        print(f"Erfolgreich geladen! Anzahl Zeitstempel: {len(timestamps)}")
        
        # Speichere die Daten lokal
        save_timestamps_to_file(timestamps, filter_param, region, resolution)
        
        return timestamps
        
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Laden der Daten: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Fehler beim Parsen der JSON-Daten: {e}")
        return []


def save_data_to_file(data, filter_param, region, filter_copy, region_copy, resolution, timestamp):
    """
    Speichert Daten in eine lokale JSON-Datei
    
    Args:
        data (dict): Die zu speichernden Daten
        filter_param (str): Filter-Parameter
        region (str): Region
        filter_copy (str): Kopie des Filter-Parameters
        region_copy (str): Kopie der Region
        resolution (str): Zeitauflösung
        timestamp (int): Unix-Zeitstempel
    
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    filename = f"{local_data_dir}/data_{filter_param}_{region}_{filter_copy}_{region_copy}_{resolution}_{timestamp}.json"
    data_to_save = {
        'filter': filter_param,
        'region': region,
        'filter_copy': filter_copy,
        'region_copy': region_copy,
        'resolution': resolution,
        'timestamp': timestamp,
        'data': data,
        'saved_at': datetime.now().isoformat()
    }
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        print(f"Daten gespeichert in: {filename}")
        return True
    except Exception as e:
        print(f"Fehler beim Speichern der Daten: {e}")
        return False


def load_data_from_file(filter_param, region, filter_copy, region_copy, resolution, timestamp):
    """
    Lädt Daten aus einer lokalen JSON-Datei
    
    Args:
        filter_param (str): Filter-Parameter
        region (str): Region
        filter_copy (str): Kopie des Filter-Parameters
        region_copy (str): Kopie der Region
        resolution (str): Zeitauflösung
        timestamp (int): Unix-Zeitstempel
    
    Returns:
        dict or None: Geladene Daten oder None bei Fehler
    """
    filename = f"{local_data_dir}/data_{filter_param}_{region}_{filter_copy}_{region_copy}_{resolution}_{timestamp}.json"
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data_container = json.load(f)
        print(f"Daten geladen aus: {filename}")
        print(f"Gespeichert am: {data_container.get('saved_at', 'Unbekannt')}")
        return data_container.get('data', {})
    except FileNotFoundError:
        print(f"Lokale Datei nicht gefunden: {filename}")
        return None
    except Exception as e:
        print(f"Fehler beim Laden der Daten: {e}")
        return None


def fetch_smard_data(filter_param, region, filter_copy, region_copy, resolution, timestamp):
    """
    Lädt die eigentlichen Werte von der SMARD API oder aus lokaler Datei
    
    Args:
        filter_param (str): Filter-Parameter
        region (str): Region
        filter_copy (str): Kopie des Filter-Parameters 
        region_copy (str): Kopie der Region
        resolution (str): Zeitauflösung
        timestamp (int): Unix-Zeitstempel
    
    Returns:
        dict or None: JSON-Daten mit den Werten oder None bei Fehler
    """
    # Prüfe ob lokale Daten verwendet werden sollen
    if local_enable:
        print("=== Verwende lokale Daten ===")
        data = load_data_from_file(filter_param, region, filter_copy, region_copy, resolution, timestamp)
        if data:
            print(f"Erfolgreich geladen! Anzahl Datenpunkte: {len(data.get('series', []))}")
            return data
        else:
            print("Keine lokalen Daten gefunden, lade aus dem Netz...")
    
    # Lade aus dem Netz
    print("=== Lade Daten aus dem Netz ===")
    url = f"https://www.smard.de/app/chart_data/{filter_param}/{region}/{filter_copy}_{region_copy}_{resolution}_{timestamp}.json"
    
    try:
        print(f"Lade Daten von: {url}")
        
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        print(f"Erfolgreich geladen! Anzahl Datenpunkte: {len(data.get('series', []))}")
        
        # Speichere die Daten lokal
        save_data_to_file(data, filter_param, region, filter_copy, region_copy, resolution, timestamp)
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Laden der Daten: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Fehler beim Parsen der JSON-Daten: {e}")
        return None


def convert_timestamps_to_datetime(timestamps):
    """
    Konvertiert Unix-Zeitstempel in lesbare Datetime-Objekte
    
    Args:
        timestamps (list): Liste von Unix-Zeitstempeln
    
    Returns:
        list: Liste von Datetime-Objekten
    """
    datetime_list = []
    for ts in timestamps:
        try:
            # Unix-Zeitstempel (Millisekunden) in Datetime konvertieren
            dt = datetime.fromtimestamp(ts / 1000)
            datetime_list.append(dt)
        except (ValueError, OSError) as e:
            print(f"Fehler bei Zeitstempel {ts}: {e}")
    
    return datetime_list


def list_local_files():
    """
    Zeigt alle lokal gespeicherten JSON-Dateien an
    """
    print("=== Lokale Datendateien ===")
    
    # Zeitstempel-Dateien
    data_path = Path(local_data_dir)
    timestamp_files = list(data_path.glob("timestamps_*.json"))
    print(f"\nZeitstempel-Dateien ({len(timestamp_files)}):")
    for file in sorted(timestamp_files):
        filename = file.name
        size = file.stat().st_size
        mtime = datetime.fromtimestamp(file.stat().st_mtime)
        print(f"  {filename} ({size} Bytes, {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
    
    # Daten-Dateien
    data_files = list(data_path.glob("data_*.json"))
    print(f"\nDaten-Dateien ({len(data_files)}):")
    for file in sorted(data_files):
        filename = file.name
        size = file.stat().st_size
        mtime = datetime.fromtimestamp(file.stat().st_mtime)
        print(f"  {filename} ({size} Bytes, {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
    
    if not timestamp_files and not data_files:
        print("Keine lokalen Dateien gefunden.")


def clear_local_cache():
    """
    Löscht alle lokalen Cache-Dateien
    """
    data_path = Path(local_data_dir)
    json_files = list(data_path.glob("*.json"))
    deleted_count = 0
    
    for file in json_files:
        try:
            file.unlink()
            deleted_count += 1
            print(f"Gelöscht: {file.name}")
        except Exception as e:
            print(f"Fehler beim Löschen von {file}: {e}")
    
    print(f"\n{deleted_count} Dateien gelöscht.")

def configure_time_range(start_date=None, end_date=None, start_time=None, end_time=None):
    """
    Konfiguriere den Zeitbereich für die Datenabfrage.
    
    Args:
        start_date: Startdatum (date) - optional, default: heute
        end_date: Enddatum (date) - optional, default: None (offenes Ende)
        start_time: Startzeit als String "HH:MM" - optional, default: "00:00"
        end_time: Endzeit als String "HH:MM" - optional, default: None
        
    Returns:
        tuple: (start_datetime, end_datetime)
        
    Beispiele:
        # Heute ab 00:00 mit offenem Ende (Standard):
        configure_time_range()
        
        # Spezifisches Datum und Zeit:
        configure_time_range(start_date=date(2025,9,18), end_date=date(2025,9,20))
        
        # Geschäftszeiten heute:
        configure_time_range(start_time="08:00", end_time="18:00")
        
        # Mehrere Tage:
        configure_time_range(start_date=date(2025,9,18), end_date=date(2025,9,20))
    """
    
    # Verwende start_date oder fallback auf heute 
    actual_start_date = start_date if start_date else date.today()
    
    # Parse Startzeit - default 00:00 wenn None
    actual_start_time = start_time if start_time is not None else "00:00"
    try:
        start_time_obj = datetime.strptime(actual_start_time, "%H:%M").time()
    except ValueError:
        print(f"⚠️ Ungültige Startzeit '{actual_start_time}', verwende 00:00")
        start_time_obj = datetime.min.time()
    
    # Erstelle start_datetime
    start_datetime = datetime.combine(actual_start_date, start_time_obj)
    
    # Erstelle end_datetime
    end_datetime = None
    if end_date:
        if end_time:
            try:
                end_time_obj = datetime.strptime(end_time, "%H:%M").time()
            except ValueError:
                print(f"⚠️ Ungültige Endzeit '{end_time}', verwende 23:59")
                end_time_obj = datetime.max.time().replace(microsecond=0)
        else:
            # Wenn nur end_date aber keine end_time: verwende Ende des Tages
            end_time_obj = datetime.max.time().replace(microsecond=0)
            
        end_datetime = datetime.combine(end_date, end_time_obj)
    elif end_time:
        # Wenn end_time aber kein end_date: verwende start_date als end_date
        try:
            end_time_obj = datetime.strptime(end_time, "%H:%M").time()
            end_datetime = datetime.combine(actual_start_date, end_time_obj)
        except ValueError:
            print(f"⚠️ Ungültige Endzeit '{end_time}', verwende offenes Ende")
            end_datetime = None
    
    # Debug-Ausgabe
    print(f"   ⚙️ Zeitbereich konfiguriert:")
    print(f"      🟢 Start: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    if end_datetime:
        print(f"      🔴 Ende:  {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        days_span = (end_datetime.date() - start_datetime.date()).days + 1
        print(f"      📅 Zeitspanne: {days_span} Tag(e)")
    else:
        print(f"      🔴 Ende:  Offenes Ende (alle verfügbaren Daten)")
    
    return start_datetime, end_datetime


def find_optimal_start_timestamp(timestamps, datetime_list, start_datetime):
    """
    Findet den optimalen Startzeitstempel durch Rückwärtssuche.
    Beginnt vom letzten (neuesten) Zeitstempel und geht rückwärts bis der erste 
    Zeitstempel gefunden wird, der kleiner ist als das Startdatum.
    
    Args:
        timestamps: Liste der verfügbaren Zeitstempel
        datetime_list: Konvertierte Datetime-Objekte der Zeitstempel
        start_datetime: Gewünschte Startzeit
        
    Returns:
        int: Index des optimalen Startzeitstempels oder None wenn nicht gefunden
    """
    start_date = start_datetime.date()
    
    print(f"   🔍 Suche vom neuesten Zeitstempel rückwärts...")
    print(f"   📅 Zieldatum: {start_date}")
    
    # Beginne vom letzten (neuesten) Element und gehe rückwärts
    for i in range(len(timestamps) - 1, -1, -1):
        timestamp_date = datetime_list[i].date()
        
        print(f"   📋 Index {i}: {timestamp_date} {'<' if timestamp_date < start_date else '>=' if timestamp_date > start_date else '='} {start_date}")
        
        # Finde den ersten Zeitstempel der kleiner ist als das Startdatum
        if timestamp_date < start_date:
            print(f"   ✅ Optimaler Startzeitstempel gefunden!")
            print(f"   📍 Index: {i} (Zeitstempel: {timestamps[i]})")
            print(f"   📅 Datum: {timestamp_date} < {start_date}")
            return i
        
        # Exakte Übereinstimmung auch akzeptieren
        elif timestamp_date == start_date:
            print(f"   ✅ Exakte Übereinstimmung gefunden!")
            print(f"   📍 Index: {i} (Zeitstempel: {timestamps[i]})")
            print(f"   📅 Datum: {timestamp_date} = {start_date}")
            return i
    
    # Wenn kein passender Zeitstempel gefunden wurde
    print(f"   ❌ Kein Zeitstempel < {start_date} gefunden")
    print(f"   💡 Verwende ältesten verfügbaren Zeitstempel (Index 0)")
    return 0

def load_data_from_timestamp(timestamps, datetime_list, start_index, start_datetime, end_datetime, config):
    """
    Lädt Daten ab einem bestimmten Startzeitstempel-Index.
    Optimierte Version die ab dem gefundenen optimalen Startzeitstempel beginnt.
    
    Args:
        timestamps: Liste der verfügbaren Zeitstempel
        datetime_list: Konvertierte Datetime-Objekte der Zeitstempel
        start_index: Index des Startzeitstempels
        start_datetime: Startzeit für den Datenbereich (datetime)
        end_datetime: Endzeit für den Datenbereich (datetime) oder None für offenes Ende
        config: Konfigurationsdictionary
        
    Returns:
        tuple: (pandas.DataFrame, used_timestamps)
            - DataFrame mit Spalten: timestamp_ms, datetime, date, time, value, source_timestamp
            - used_timestamps: Liste der verwendeten Zeitstempel-IDs
    """
    
    all_data_points = []
    used_timestamps = []
    
    print(f"📊 Lade Daten ab Index {start_index}:")
    print(f"   🟢 Start: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    if end_datetime:
        print(f"   🔴 Ende:  {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"   🔴 Ende:  Offenes Ende (alle verfügbaren Daten)")
    
    start_date = start_datetime.date()
    end_date = end_datetime.date() if end_datetime else None
    
    # Beginne beim gefundenen Startzeitstempel und gehe vorwärts
    print(f"\n🔄 Lade Daten ab Startzeitstempel (Index {start_index} vorwärts)")
    
    for i in range(start_index, len(timestamps)):
        timestamp = timestamps[i]
        timestamp_dt = datetime_list[i]
        
        print(f"\n⏰ Prüfe Zeitstempel {timestamp} ({timestamp_dt.strftime('%Y-%m-%d')})...")
        
        try:
            # Lade Daten für diesen Zeitstempel
            data = fetch_smard_data(
                config['filter_param'], config['region'], 
                config['filter_param'], config['region'], 
                config['resolution'], timestamp
            )
            
            if not data or 'series' not in data:
                print(f"   ❌ Keine Daten verfügbar")
                continue
            
            # Sammle Daten im angegebenen Zeitbereich
            timestamp_points = []
            found_start_data = False
            found_end_data = False
            
            for serie in data['series']:
                if isinstance(serie, list) and len(serie) >= 2 and serie[1] is not None:
                    dt = datetime.fromtimestamp(serie[0] / 1000)
                    
                    # Prüfe ob Daten im gewünschten Zeitbereich liegen
                    in_range = dt >= start_datetime
                    if end_datetime:
                        in_range = in_range and dt <= end_datetime
                    
                    if in_range:
                        data_point = {
                            'timestamp_ms': serie[0],
                            'datetime': dt,
                            'date': dt.date(),
                            'time': dt.time(),
                            'value': serie[1],
                            'source_timestamp': timestamp
                        }
                        timestamp_points.append(data_point)
                        
                        # Prüfe ob Start-/Enddaten gefunden
                        if dt.date() == start_date:
                            found_start_data = True
                        if end_date and dt.date() == end_date:
                            found_end_data = True
            
            # Speichere die Daten
            if timestamp_points:
                # Vermeide Duplikate
                existing_timestamps = {dp['timestamp_ms'] for dp in all_data_points}
                new_points = [dp for dp in timestamp_points if dp['timestamp_ms'] not in existing_timestamps]
                
                if new_points:
                    all_data_points.extend(new_points)
                    used_timestamps.append(timestamp)
                    print(f"   ✅ {len(new_points)} neue Datenpunkte im Zeitbereich geladen")
                    
                    # Debug: Zeige erste und letzte 5 Einträge
                    show_data_preview(new_points)
                    
                    if found_start_data:
                        print(f"   🎯 Startdatum {start_date} gefunden!")
                        
                        # Bei festem Ende: Prüfe ob Enddatum erreicht
                        if end_datetime and found_end_data:
                            print(f"   🏁 Enddatum {end_date} erreicht!")
                            break
                else:
                    print(f"   ℹ️ Daten bereits vorhanden (Duplikate)")
            else:
                print(f"   ❌ Keine Daten im Zeitbereich")
                
        except Exception as e:
            print(f"   ⚠️ Fehler: {str(e)}")
            continue
    
    # Konvertiere zu pandas DataFrame
    if all_data_points:
        df = pd.DataFrame(all_data_points)
        print(f"\n✅ === ZUSAMMENFASSUNG ===")
        print(f"📊 DataFrame erstellt: {len(df)} Datenpunkte")
        print(f"📅 Verwendete Zeitstempel: {len(used_timestamps)}")
        print(f"📋 DataFrame Spalten: {list(df.columns)}")
        return df, used_timestamps
    else:
        print(f"\n❌ Keine Daten gefunden - leeres DataFrame zurückgegeben")
        return pd.DataFrame(), used_timestamps


def show_data_preview(timestamp_points):
    """Zeige erste und letzte 5 Dateneinträge für Debug-Zwecke"""
    print(f"   📋 Erste 5 Einträge:")
    for j, point in enumerate(timestamp_points[:5]):
        print(f"      {j+1}. {point['datetime'].strftime('%Y-%m-%d %H:%M')} - {point['value']:.2f} €/MWh")
    
    if len(timestamp_points) > 5:
        print(f"   📋 Letzte 5 Einträge:")
        for j, point in enumerate(timestamp_points[-5:]):
            idx = len(timestamp_points) - 4 + j
            print(f"      {idx}. {point['datetime'].strftime('%Y-%m-%d %H:%M')} - {point['value']:.2f} €/MWh")

def analyze_data(df, target_date, used_timestamps):
    """Analysiere die geladenen Daten"""
    print(f"\n📊 === DATENANALYSE ===")
    print(f"📍 Zeitstempel verwendet: {len(used_timestamps)}")
    print(f"📈 Datenpunkte: {len(df)}")
    
    if len(df) > 0:
        start_time = df['datetime'].min()
        end_time = df['datetime'].max()
        print(f"⏰ Zeitraum: {start_time.strftime('%Y-%m-%d %H:%M')} bis {end_time.strftime('%Y-%m-%d %H:%M')}")
        
        # Preisstatistiken
        print(f"\n💰 Preisstatistiken:")
        print(f"   Min: {df['value'].min():.2f} €/MWh")
        print(f"   Max: {df['value'].max():.2f} €/MWh")
        print(f"   Ø:   {df['value'].mean():.2f} €/MWh")
        print(f"   Median: {df['value'].median():.2f} €/MWh")
        
        # Tagesanalyse
        unique_dates = sorted(df['date'].unique())
        print(f"\n📅 Abgedeckte Tage: {len(unique_dates)}")
        for date_val in unique_dates:
            count = len(df[df['date'] == date_val])
            marker = "🎯" if date_val == target_date else "📅"
            print(f"   {marker} {date_val}: {count} Datenpunkte")


def export_csv(df, target_date, data_dir):
    """Exportiere Daten als CSV"""
    if len(df) == 0:
        print("❌ Keine Daten zum Exportieren")
        return
    
    # Bereite Export-DataFrame vor
    export_df = df[['datetime', 'date', 'time', 'value']].copy()
    export_df.columns = ['Zeitstempel', 'Datum', 'Uhrzeit', 'Preis_EUR_MWh']
    
    # Bestimme Dateinamen
    start_date = df['date'].min()
    end_date = df['date'].max()
    
    if start_date == end_date:
        filename = f"smard_data_{start_date.strftime('%Y%m%d')}.csv"
    else:
        filename = f"smard_data_{start_date.strftime('%Y%m%d')}_bis_{end_date.strftime('%Y%m%d')}.csv"
    
    filepath = os.path.join(data_dir, filename)
    
    # Stelle sicher, dass das Verzeichnis existiert
    os.makedirs(data_dir, exist_ok=True)
    
    # Exportiere
    export_df.to_csv(filepath, index=False, encoding='utf-8')
    
    print(f"\n💾 === CSV-EXPORT ===")
    print(f"📁 Datei: {filepath}")
    print(f"📊 Datenpunkte: {len(export_df)}")
    print(f"📅 Zeitraum: {start_date} bis {end_date}")
    print(f"📦 Dateigröße: {os.path.getsize(filepath)} Bytes")


def convert_euro_mwh_to_ct_kwh(value_euro_mwh):
    """
    Wandelt Energiepreise von Euro/MWh in Cent/kWh um.
    
    Args:
        value_euro_mwh: Preis in Euro/MWh (float oder int)
        
    Returns:
        float: Preis in Cent/kWh
        
    Beispiel:
        >>> convert_euro_mwh_to_ct_kwh(120.0)  # 120 Euro/MWh
        12.0  # = 12 Cent/kWh
        
    Umrechnungsformel:
        1 Euro/MWh = 0.1 Cent/kWh
        (da 1 MWh = 1000 kWh und 1 Euro = 100 Cent)
    """
    if value_euro_mwh is None:
        return None
    
    try:
        # 1 Euro/MWh = 0.1 Cent/kWh
        value_ct_kwh = float(value_euro_mwh) * 0.1
        return round(value_ct_kwh, 4)  # 4 Nachkommastellen für Präzision
    except (ValueError, TypeError):
        print(f"⚠️ Ungültiger Wert für Umrechnung: {value_euro_mwh}")
        return None


def get_all_data_values(df, column_name='value'):
    """
    Extrahiert alle Werte aus einer pandas DataFrame-Spalte.
    
    Args:
        df: pandas DataFrame mit den Daten
        column_name: Name der Spalte aus der die Werte extrahiert werden sollen (default: 'value')
        
    Returns:
        list: Liste aller Werte (ohne None/NaN-Werte)
        
    Beispiel:
        >>> df = pd.DataFrame({'value': [120.5, None, 130.2], 'other': [1, 2, 3]})
        >>> get_all_data_values(df, 'value')
        [120.5, 130.2]
    """
    
    if df.empty:
        print(f"⚠️ DataFrame ist leer")
        return []
    
    if column_name not in df.columns:
        print(f"⚠️ Spalte '{column_name}' nicht im DataFrame gefunden")
        print(f"   Verfügbare Spalten: {list(df.columns)}")
        return []
    
    # Entferne None/NaN Werte und konvertiere zu Liste
    values = df[column_name].dropna().tolist()
    
    print(f"📊 {len(values)} Werte aus Spalte '{column_name}' extrahiert ({len(df)} Zeilen gesamt)")
    return values