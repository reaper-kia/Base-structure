import { useEffect, useRef, useState } from 'react';
import type { FeatureCollection, Point } from 'geojson';
import {
  Map as MapLibreMap,
  NavigationControl,
  Popup,
  type MapLayerMouseEvent,
  type StyleSpecification,
} from 'maplibre-gl';

import 'maplibre-gl/dist/maplibre-gl.css';
import './MapPage.css';

type PlaceProperties = {
  name: string;
  kind: 'school' | 'clinic' | 'culture';
};

type PlacesCollection = FeatureCollection<Point, PlaceProperties>;

const mapStyle: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '© OpenStreetMap contributors',
    },
  },
  layers: [
    {
      id: 'osm',
      type: 'raster',
      source: 'osm',
    },
  ],
};

export function MapPage() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let map: MapLibreMap | null = null;

    async function initializeMap() {
      try {
        const response = await fetch('/data/demo.json', {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Не удалось загрузить GeoJSON: ${response.status}`);
        }

        const places = (await response.json()) as PlacesCollection;

        if (!containerRef.current) {
          return;
        }

        map = new MapLibreMap({
          container: containerRef.current,
          style: mapStyle,
          center: [92.9, 56.03],
          zoom: 10,
        });

        map.addControl(
          new NavigationControl(),
          'top-right',
        );

        map.on('load', () => {
          if (!map) {
            return;
          }

          map.addSource('places', {
            type: 'geojson',
            data: places,
          });

          map.addLayer({
            id: 'places-points',
            type: 'circle',
            source: 'places',
            paint: {
              'circle-radius': 9,
              'circle-color': '#dc2626',
              'circle-stroke-width': 2,
              'circle-stroke-color': '#ffffff',
            },
          });

          map.on(
                'click',
                'places-points',
                (event: MapLayerMouseEvent) => {
            const feature = event.features?.[0];

            if (!feature || feature.geometry.type !== 'Point') {
              return;
            }

            const coordinates = feature.geometry.coordinates as [
              number,
              number,
            ];

            const name = String(
              feature.properties?.name ?? 'Объект',
            );

            new Popup()
              .setLngLat(coordinates)
              .setText(name)
              .addTo(map!);
          });

          map.on('mouseenter', 'places-points', () => {
            map!.getCanvas().style.cursor = 'pointer';
          });

          map.on('mouseleave', 'places-points', () => {
            map!.getCanvas().style.cursor = '';
          });
        });
      } catch (caughtError) {
        if (
          caughtError instanceof DOMException &&
          caughtError.name === 'AbortError'
        ) {
          return;
        }

        setError(
          caughtError instanceof Error
            ? caughtError.message
            : 'Неизвестная ошибка карты',
        );
      }
    }

    void initializeMap();

    return () => {
      controller.abort();
      map?.remove();
    };
  }, []);

  return (
    <section className="map-page">
      <header className="map-page__header">
        <p>Учебный геомодуль</p>
        <h1>Объекты инфраструктуры</h1>
      </header>

      {error && (
        <p className="map-page__error">
          {error}
        </p>
      )}

      <div
        ref={containerRef}
        className="map-page__canvas"
        aria-label="Карта объектов инфраструктуры"
      />
    </section>
  );
}