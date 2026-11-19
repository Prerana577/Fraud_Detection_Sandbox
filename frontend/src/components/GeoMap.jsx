import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix standard Leaflet default icon path issues in bundlers
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const createCustomIcon = (decision) => {
  const color = decision === 'BLOCK' ? '#ef4444' : decision === 'FLAG' ? '#f59e0b' : '#22c55e'
  return L.divIcon({
    className: 'custom-geo-marker',
    html: `<div style="
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: ${color};
      border: 2px solid #ffffff;
      box-shadow: 0 0 10px ${color};
    "></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  })
}

// City coordinates mapping for impossible travel source lookup
const CITY_COORDS = {
  bengaluru: [12.9716, 77.5946],
  mumbai: [19.076, 72.8777],
  delhi: [28.6139, 77.209],
  chennai: [13.0827, 80.2707],
  hyderabad: [17.385, 78.4867],
  pune: [18.5204, 73.8567],
  kolkata: [22.5726, 88.3639],
  guwahati: [26.1445, 91.7362],
  jaipur: [26.9124, 75.7873],
  ahmedabad: [23.0225, 72.5714],
}

const MAP_THEMES = {
  google_roadmap: {
    name: 'Google Maps (Road)',
    url: 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
    attribution: '&copy; Google Maps',
    maxZoom: 20,
  },
  google_satellite: {
    name: 'Google Satellite',
    url: 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
    attribution: '&copy; Google Maps Satellite',
    maxZoom: 20,
  },
  google_terrain: {
    name: 'Google Terrain',
    url: 'https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
    attribution: '&copy; Google Maps Terrain',
    maxZoom: 20,
  },
  dark_voyager: {
    name: 'Dark Mode (Voyager)',
    url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    attribution: '&copy; CARTO &copy; OpenStreetMap',
    maxZoom: 19,
  },
}

export default function GeoMap({ transactions = [] }) {
  const mapContainerRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const currentTileLayerRef = useRef(null)
  const markersLayerRef = useRef(null)
  const arcsLayerRef = useRef(null)

  const [mapTheme, setMapTheme] = useState('google_roadmap') // 'google_roadmap' | 'google_satellite' | 'google_terrain' | 'dark_voyager'
  const [filter, setFilter] = useState('all') // 'all' | 'fraud' | 'travel'
  const [activeTravels, setActiveTravels] = useState([])

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return

    // Center on India
    const map = L.map(mapContainerRef.current, {
      center: [20.5937, 78.9629],
      zoom: 5,
      zoomControl: true,
      minZoom: 4,
      maxZoom: 18,
    })

    // Default to Google Maps Roadmap
    const themeConfig = MAP_THEMES.google_roadmap
    currentTileLayerRef.current = L.tileLayer(themeConfig.url, {
      attribution: themeConfig.attribution,
      maxZoom: themeConfig.maxZoom,
    }).addTo(map)

    markersLayerRef.current = L.layerGroup().addTo(map)
    arcsLayerRef.current = L.layerGroup().addTo(map)
    mapInstanceRef.current = map

    return () => {
      map.remove()
      mapInstanceRef.current = null
    }
  }, [])

  // Switch Tile Layer when mapTheme changes
  useEffect(() => {
    if (!mapInstanceRef.current) return
    const themeConfig = MAP_THEMES[mapTheme] || MAP_THEMES.google_roadmap

    if (currentTileLayerRef.current) {
      mapInstanceRef.current.removeLayer(currentTileLayerRef.current)
    }

    currentTileLayerRef.current = L.tileLayer(themeConfig.url, {
      attribution: themeConfig.attribution,
      maxZoom: themeConfig.maxZoom,
      subdomains: themeConfig.url.includes('{s}') ? 'abcd' : '',
    }).addTo(mapInstanceRef.current)

    // Bring markers and arcs to front
    markersLayerRef.current?.bringToFront?.()
    arcsLayerRef.current?.bringToFront?.()
  }, [mapTheme])

  // Update Markers and Flight Arcs when transactions or filter changes
  useEffect(() => {
    if (!mapInstanceRef.current || !markersLayerRef.current || !arcsLayerRef.current) return

    markersLayerRef.current.clearLayers()
    arcsLayerRef.current.clearLayers()

    const detectedTravels = []

    // Process transactions
    transactions.slice(0, 100).forEach((txn) => {
      if (!txn.lat || !txn.lon) return

      const isBlock = txn.decision === 'BLOCK'
      const isFlag = txn.decision === 'FLAG'
      const isFraud = isBlock || isFlag

      // Check for Impossible Travel rule
      const travelReason = (txn.reasons || []).find((r) => r.rule === 'impossible_travel')

      if (filter === 'fraud' && !isFraud) return
      if (filter === 'travel' && !travelReason) return

      // Add marker
      const marker = L.marker([txn.lat, txn.lon], {
        icon: createCustomIcon(txn.decision),
      })

      const popupHtml = `
        <div style="font-family: inherit; font-size: 0.85rem; color: #111;">
          <strong style="color: ${isBlock ? '#dc2626' : isFlag ? '#d97706' : '#16a34a'}">
            ● ${txn.decision} (Risk Score: ${txn.risk_score}/100)
          </strong>
          <div style="margin-top: 4px; font-weight: 600;">₹${(txn.amount || 0).toLocaleString()} • ${txn.merchant || 'Store'}</div>
          <div style="color: #555;">City: ${txn.city}</div>
          <div style="color: #666; font-size: 0.75rem; margin-top: 4px;">User: ${txn.user_name || txn.user_id}</div>
          ${travelReason ? `<div style="margin-top: 6px; padding: 4px 6px; background: #fee2e2; border-left: 3px solid #ef4444; color: #b91c1c; font-size: 0.75rem;">✈ ${travelReason.detail}</div>` : ''}
        </div>
      `
      marker.bindPopup(popupHtml)
      markersLayerRef.current.addLayer(marker)

      // If impossible travel triggered, draw flight arc
      if (travelReason) {
        // Parse previous city from reason string e.g. "Impossible travel: Bengaluru → Guwahati in 4 min"
        let fromCityCoords = null
        for (const [cityKey, coords] of Object.entries(CITY_COORDS)) {
          if (travelReason.detail?.toLowerCase().includes(`impossible travel: ${cityKey}`) ||
              travelReason.detail?.toLowerCase().includes(`${cityKey} →`)) {
            fromCityCoords = coords
            break
          }
        }

        if (!fromCityCoords && txn.user?.home_city) {
          fromCityCoords = CITY_COORDS[txn.user.home_city.toLowerCase()]
        }

        if (fromCityCoords) {
          const latlngs = [fromCityCoords, [txn.lat, txn.lon]]
          const polyline = L.polyline(latlngs, {
            color: '#ef4444',
            weight: 3,
            opacity: 0.85,
            dashArray: '6, 8',
          })
          polyline.bindPopup(`
            <div style="color:#b91c1c; font-size:0.85rem; font-weight:600;">
              ✈ Impossible Travel Anomaly
              <div style="color:#444; font-weight:normal; margin-top:4px;">${travelReason.detail}</div>
            </div>
          `)
          arcsLayerRef.current.addLayer(polyline)

          detectedTravels.push({
            id: txn.txn_id,
            user: txn.user_name || txn.user_id,
            detail: travelReason.detail,
            amount: txn.amount,
          })
        }
      }
    })

    setActiveTravels(detectedTravels)
  }, [transactions, filter])

  const resetView = () => {
    mapInstanceRef.current?.setView([20.5937, 78.9629], 5)
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 16, height: '620px' }}>
      {/* Map Container */}
      <div style={{ position: 'relative', borderRadius: 12, overflow: 'hidden', border: '1px solid var(--color-border)' }}>
        <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} />

        {/* Map Top-Right Filter & Theme Bar */}
        <div style={{
          position: 'absolute',
          top: 12,
          right: 12,
          zIndex: 1000,
          background: 'rgba(15, 23, 42, 0.9)',
          backdropFilter: 'blur(8px)',
          padding: '6px 10px',
          borderRadius: 8,
          border: '1px solid rgba(255,255,255,0.15)',
          display: 'flex',
          gap: 6,
          alignItems: 'center',
          boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
        }}>
          {/* Map Layer Switcher (Google Maps / Satellite / Dark) */}
          <select
            value={mapTheme}
            onChange={(e) => setMapTheme(e.target.value)}
            style={{
              padding: '4px 8px',
              borderRadius: 6,
              background: '#1e293b',
              color: '#f8fafc',
              border: '1px solid #475569',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
            title="Switch Map Tiles"
          >
            <option value="google_roadmap">🗺️ Google Maps</option>
            <option value="google_satellite">🛰️ Google Satellite</option>
            <option value="google_terrain">⛰️ Google Terrain</option>
            <option value="dark_voyager">🌙 Dark Mode</option>
          </select>

          <div style={{ width: 1, height: 16, background: 'rgba(255,255,255,0.2)' }} />

          <button
            className={`btn ${filter === 'all' ? 'btn-primary' : 'btn-ghost'}`}
            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
            onClick={() => setFilter('all')}
          >
            All Live Txns
          </button>
          <button
            className={`btn ${filter === 'fraud' ? 'btn-warning' : 'btn-ghost'}`}
            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
            onClick={() => setFilter('fraud')}
          >
            Fraud Only
          </button>
          <button
            className={`btn ${filter === 'travel' ? 'btn-danger' : 'btn-ghost'}`}
            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
            onClick={() => setFilter('travel')}
          >
            ✈ Travel Arcs ({activeTravels.length})
          </button>
          <button
            className="btn btn-ghost"
            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
            onClick={resetView}
            title="Reset Map View to India"
          >
            ⟲
          </button>
        </div>
      </div>

      {/* Geo Insights Side Panel */}
      <div style={{
        background: 'var(--color-card)',
        borderRadius: 12,
        padding: 16,
        border: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
        overflowY: 'auto',
      }}>
        <div>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6 }}>
            🗺️ Geospatial Telemetry
          </h3>
          <p style={{ fontSize: '0.8rem', color: '#888', marginTop: 4 }}>
            Real-time coordinates and Haversine speed tracking across Indian metropolitan clusters.
          </p>
        </div>

        {/* Legend */}
        <div style={{ background: 'var(--color-bg)', padding: 12, borderRadius: 8, fontSize: '0.8rem', display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ fontWeight: 600, color: '#aaa', marginBottom: 2 }}>MAP LEGEND</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#22c55e' }} />
            <span>Approved (Low Latency / Local)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#f59e0b' }} />
            <span>Flagged (Medium Risk Anomaly)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#ef4444' }} />
            <span>Blocked (Fraud Teleportation)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 16, height: 2, background: '#ef4444', borderTop: '2px dashed #ef4444' }} />
            <span>Impossible Flight Trajectory (&gt;900 km/h)</span>
          </div>
        </div>

        {/* Impossible Travel Incidents List */}
        <div style={{ flex: 1 }}>
          <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: '#ef4444', display: 'flex', alignItems: 'center', gap: 4 }}>
            ✈ Active Impossible Travel Trajectories ({activeTravels.length})
          </h4>

          {activeTravels.length === 0 ? (
            <p style={{ fontSize: '0.75rem', color: '#666', marginTop: 8 }}>
              No impossible travel events currently active. Click "✈ Impossible Travel" in Simulator Controls above to trigger one.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
              {activeTravels.map((travel, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: 10,
                    borderRadius: 8,
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.25)',
                    fontSize: '0.75rem',
                  }}
                >
                  <div style={{ fontWeight: 600, color: '#ef4444' }}>{travel.user} • ₹{travel.amount?.toLocaleString()}</div>
                  <div style={{ color: '#ccc', marginTop: 4 }}>{travel.detail}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
