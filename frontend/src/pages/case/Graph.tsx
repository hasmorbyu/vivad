import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import cytoscape, { type Core } from 'cytoscape'
import { api } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { Field } from '../../components/ui'
import type { J } from '../../types'

const KIND_LABEL: Record<string, string> = {
  case: 'CENTERPIECE MAP ANCHOR',
  party: 'POLAROID PORTRAIT',
  claim: 'INDEX NOTE',
  evidence: 'FORENSIC EVIDENCE',
  event: 'NEWSPAPER CLIPPING',
  contradiction: 'SCENE DOSSIER ⚠',
  law: 'BALLISTICS & STATUTE §',
  hearing: 'HEARING',
  decision: 'DECISION ⚖',
}

function toUri(svg: string): string {
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg.trim())}`
}

// 1. Centerpiece City & River Map Anchor with Circled Points of Interest, Marked Crimson Route, 4 Corner Pushpins & Creases
const SVG_MAP_CENTER = toUri(`<svg xmlns="http://www.w3.org/2000/svg" width="240" height="160" viewBox="0 0 240 160">
  <defs>
    <radialGradient id="pinRed1" cx="35%" cy="35%" r="65%">
      <stop offset="0%" stop-color="#ff6b6b"/>
      <stop offset="70%" stop-color="#b91c1c"/>
      <stop offset="100%" stop-color="#450a0a"/>
    </radialGradient>
    <filter id="shadow1" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="2" dy="4" stdDeviation="3" flood-opacity="0.35"/>
    </filter>
  </defs>
  <!-- Map Paper Base -->
  <rect x="6" y="6" width="228" height="148" fill="#e8dac1" stroke="#8c7554" stroke-width="2" filter="url(#shadow1)"/>
  <!-- Fold Creases -->
  <line x1="80" y1="6" x2="80" y2="154" stroke="#b09d7d" stroke-width="1.5" stroke-dasharray="4,2"/>
  <line x1="160" y1="6" x2="160" y2="154" stroke="#b09d7d" stroke-width="1.5" stroke-dasharray="4,2"/>
  <line x1="6" y1="80" x2="234" y2="80" stroke="#b09d7d" stroke-width="1.5" stroke-dasharray="4,2"/>
  <!-- River Vector -->
  <path d="M 12 35 C 70 85, 110 20, 170 100 C 200 140, 220 120, 234 110" fill="none" stroke="#7ca5be" stroke-width="10" opacity="0.65"/>
  <path d="M 12 35 C 70 85, 110 20, 170 100 C 200 140, 220 120, 234 110" fill="none" stroke="#447294" stroke-width="2.5"/>
  <!-- City Grid Lines -->
  <path d="M 20 40 L 220 40 M 30 110 L 210 110 M 50 15 L 50 140 M 120 15 L 120 140 M 190 15 L 190 140" fill="none" stroke="#c2b295" stroke-width="1"/>
  <!-- Circled Points of Interest -->
  <circle cx="65" cy="55" r="15" fill="none" stroke="#dc2626" stroke-width="2.5"/>
  <circle cx="65" cy="55" r="3" fill="#dc2626"/>
  <circle cx="175" cy="95" r="13" fill="none" stroke="#dc2626" stroke-width="2.5"/>
  <circle cx="175" cy="95" r="3" fill="#dc2626"/>
  <circle cx="130" cy="45" r="11" fill="none" stroke="#dc2626" stroke-width="2"/>
  <circle cx="130" cy="45" r="3" fill="#dc2626"/>
  <!-- Intersecting Red Marked Route -->
  <polyline points="65,55 130,45 175,95 200,60" fill="none" stroke="#dc2626" stroke-width="3" stroke-dasharray="5,3"/>
  <!-- Corner Translucent Tape Strips -->
  <rect x="2" y="-2" width="30" height="14" fill="rgba(240,230,200,0.65)" stroke="rgba(200,180,140,0.5)" transform="rotate(-25 15 5)"/>
  <rect x="210" y="-2" width="30" height="14" fill="rgba(240,230,200,0.65)" stroke="rgba(200,180,140,0.5)" transform="rotate(25 225 5)"/>
  <!-- 4 Corner Spherical Red Pushpins with Shadows -->
  <ellipse cx="14" cy="18" rx="6" ry="3" fill="rgba(0,0,0,0.4)"/>
  <circle cx="14" cy="14" r="6" fill="url(#pinRed1)" stroke="#7f1d1d" stroke-width="0.8"/>
  <circle cx="12" cy="12" r="2" fill="#ff9999" opacity="0.8"/>
  <ellipse cx="226" cy="18" rx="6" ry="3" fill="rgba(0,0,0,0.4)"/>
  <circle cx="226" cy="14" r="6" fill="url(#pinRed1)" stroke="#7f1d1d" stroke-width="0.8"/>
  <circle cx="224" cy="12" r="2" fill="#ff9999" opacity="0.8"/>
  <ellipse cx="14" cy="150" rx="6" ry="3" fill="rgba(0,0,0,0.4)"/>
  <circle cx="14" cy="146" r="6" fill="url(#pinRed1)" stroke="#7f1d1d" stroke-width="0.8"/>
  <circle cx="12" cy="144" r="2" fill="#ff9999" opacity="0.8"/>
  <ellipse cx="226" cy="150" rx="6" ry="3" fill="rgba(0,0,0,0.4)"/>
  <circle cx="226" cy="146" r="6" fill="url(#pinRed1)" stroke="#7f1d1d" stroke-width="0.8"/>
  <circle cx="224" cy="144" r="2" fill="#ff9999" opacity="0.8"/>
</svg>`)

// 2. Polaroid Photo Portrait
const SVG_POLAROID = toUri(`<svg xmlns="http://www.w3.org/2000/svg" width="170" height="120" viewBox="0 0 170 120">
  <defs>
    <radialGradient id="pinRed2" cx="35%" cy="35%" r="65%">
      <stop offset="0%" stop-color="#ff6b6b"/>
      <stop offset="70%" stop-color="#b91c1c"/>
      <stop offset="100%" stop-color="#450a0a"/>
    </radialGradient>
  </defs>
  <!-- Polaroid Base -->
  <rect x="5" y="10" width="160" height="104" fill="#fcf9f2" stroke="#c7b8a1" stroke-width="1.5" rx="1"/>
  <!-- Photo Inner Window -->
  <rect x="15" y="18" width="140" height="64" fill="#2b241c"/>
  <circle cx="85" cy="46" r="16" fill="#6e5d48"/>
  <path d="M 68 70 C 68 54, 102 54, 102 70 Z" fill="#6e5d48"/>
  <path d="M 15 18 L 155 18 L 155 82 L 15 82 Z" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>
  <!-- Semi-translucent Adhesive Tape Strip Top Right -->
  <rect x="125" y="4" width="36" height="14" fill="rgba(240,230,200,0.75)" stroke="rgba(200,180,140,0.4)" transform="rotate(15 143 11)"/>
  <!-- Spherical Red Pushpin at Top Center -->
  <ellipse cx="85" cy="14" rx="5" ry="2.5" fill="rgba(0,0,0,0.4)"/>
  <circle cx="85" cy="10" r="6" fill="url(#pinRed2)" stroke="#7f1d1d" stroke-width="0.8"/>
  <circle cx="83" cy="8" r="2" fill="#ff9999" opacity="0.8"/>
</svg>`)

// 3. High-Contrast Black & White Fingerprint Analysis Card
const SVG_FINGERPRINT = toUri(`<svg xmlns="http://www.w3.org/2000/svg" width="170" height="110" viewBox="0 0 170 110">
  <defs>
    <radialGradient id="pinBlack1" cx="35%" cy="35%" r="65%">
      <stop offset="0%" stop-color="#555555"/>
      <stop offset="70%" stop-color="#1a1a1a"/>
      <stop offset="100%" stop-color="#000000"/>
    </radialGradient>
  </defs>
  <!-- Card Base -->
  <rect x="5" y="10" width="160" height="94" fill="#f3e8d2" stroke="#a89270" stroke-width="1.5"/>
  <text x="14" y="24" font-family="monospace" font-size="8" font-weight="bold" fill="#4a3b2c">FINGERPRINT ANALYSIS [AFIS]</text>
  <!-- Fingerprint Box -->
  <rect x="14" y="28" width="58" height="66" fill="#ffffff" stroke="#3d3124"/>
  <path d="M 26 62 C 26 42 60 42 60 62 M 30 62 C 30 46 56 46 56 62 M 34 62 C 34 50 52 50 52 62 M 38 62 C 38 54 48 54 48 62 M 43 62 L 43 57" fill="none" stroke="#111111" stroke-width="1.8"/>
  <!-- Biometric Data Blocks -->
  <rect x="80" y="30" width="75" height="5" fill="#2e261d"/>
  <rect x="80" y="40" width="60" height="5" fill="#2e261d"/>
  <rect x="80" y="50" width="70" height="5" fill="#2e261d"/>
  <text x="80" y="66" font-family="monospace" font-size="7" fill="#7a1a1a" font-weight="bold">MATCH CONFIRM: 98.4%</text>
  <text x="80" y="76" font-family="monospace" font-size="6.5" fill="#554433">LATENT RIDGE: ACC-09</text>
  <text x="80" y="86" font-family="monospace" font-size="6.5" fill="#554433">CLASSIF: WHORL-L</text>
  <!-- Black Pushpin -->
  <ellipse cx="85" cy="14" rx="5" ry="2.5" fill="rgba(0,0,0,0.4)"/>
  <circle cx="85" cy="10" r="6" fill="url(#pinBlack1)" stroke="#000" stroke-width="0.8"/>
  <circle cx="83" cy="8" r="2" fill="#888888" opacity="0.8"/>
</svg>`)

// 4. Dark Forensic Crime Scene Reference Card with Chalk Body Silhouette
const SVG_FORENSIC_SILHOUETTE = toUri(`<svg xmlns="http://www.w3.org/2000/svg" width="180" height="115" viewBox="0 0 180 115">
  <defs>
    <radialGradient id="pinRed3" cx="35%" cy="35%" r="65%">
      <stop offset="0%" stop-color="#ff6b6b"/>
      <stop offset="70%" stop-color="#b91c1c"/>
      <stop offset="100%" stop-color="#450a0a"/>
    </radialGradient>
  </defs>
  <!-- Dark Card Base -->
  <rect x="5" y="10" width="170" height="98" fill="#1a1715" stroke="#dc2626" stroke-width="2"/>
  <!-- Hazard Stripe Header Banner -->
  <rect x="5" y="10" width="170" height="12" fill="#eab308"/>
  <line x1="15" y1="10" x2="25" y2="22" stroke="#000" stroke-width="4"/>
  <line x1="35" y1="10" x2="45" y2="22" stroke="#000" stroke-width="4"/>
  <line x1="55" y1="10" x2="65" y2="22" stroke="#000" stroke-width="4"/>
  <line x1="75" y1="10" x2="85" y2="22" stroke="#000" stroke-width="4"/>
  <line x1="95" y1="10" x2="105" y2="22" stroke="#000" stroke-width="4"/>
  <line x1="115" y1="10" x2="125" y2="22" stroke="#000" stroke-width="4"/>
  <line x1="135" y1="10" x2="145" y2="22" stroke="#000" stroke-width="4"/>
  <line x1="155" y1="10" x2="165" y2="22" stroke="#000" stroke-width="4"/>
  <!-- Chalk Style Body Silhouette -->
  <circle cx="90" cy="44" r="8" fill="none" stroke="#ffffff" stroke-width="1.8" stroke-dasharray="3,1.5"/>
  <path d="M 90 52 L 90 82 M 90 60 L 68 72 M 90 60 L 112 66 M 90 82 L 74 102 M 90 82 L 106 100" fill="none" stroke="#ffffff" stroke-width="1.8" stroke-dasharray="3,1.5"/>
  <!-- Yellow Evidence Cones -->
  <polygon points="62,72 66,66 70,72" fill="#facc15"/>
  <text x="64" y="71" font-size="5" font-family="sans-serif" font-weight="bold" fill="#000">1</text>
  <polygon points="108,66 112,60 116,66" fill="#facc15"/>
  <text x="110" y="65" font-size="5" font-family="sans-serif" font-weight="bold" fill="#000">2</text>
  <!-- Red Pushpin -->
  <ellipse cx="90" cy="14" rx="5" ry="2.5" fill="rgba(0,0,0,0.4)"/>
  <circle cx="90" cy="10" r="6" fill="url(#pinRed3)" stroke="#7f1d1d" stroke-width="0.8"/>
  <circle cx="88" cy="8" r="2" fill="#ff9999" opacity="0.8"/>
</svg>`)

// 5. Ballistics Dossier Sheet with Bullet Profile & Spec Lines
const SVG_BALLISTICS = toUri(`<svg xmlns="http://www.w3.org/2000/svg" width="170" height="110" viewBox="0 0 170 110">
  <defs>
    <radialGradient id="pinRed4" cx="35%" cy="35%" r="65%">
      <stop offset="0%" stop-color="#ff6b6b"/>
      <stop offset="70%" stop-color="#b91c1c"/>
      <stop offset="100%" stop-color="#450a0a"/>
    </radialGradient>
  </defs>
  <!-- Technical Grid Paper Base -->
  <rect x="5" y="10" width="160" height="94" fill="#edf2f7" stroke="#475569" stroke-width="1.5"/>
  <path d="M 5 25 L 165 25 M 5 40 L 165 40 M 5 55 L 165 55 M 5 70 L 165 70 M 5 85 L 165 85 M 40 10 L 40 104 M 80 10 L 80 104 M 120 10 L 120 104" stroke="#cbd5e1" stroke-width="0.8"/>
  <text x="12" y="22" font-family="monospace" font-size="7.5" font-weight="bold" fill="#1e293b">BALLISTICS DOSSIER: SPEC-09</text>
  <!-- Bullet Illustration -->
  <rect x="25" y="55" width="40" height="24" fill="#ca8a04" stroke="#854d0e" stroke-width="1"/>
  <path d="M 65 55 C 80 55, 88 67, 88 67 C 88 67, 80 79, 65 79 Z" fill="#9a3412" stroke="#7c2d12" stroke-width="1"/>
  <line x1="30" y1="55" x2="30" y2="79" stroke="#a16207" stroke-width="1"/>
  <!-- Caliper Spec Dimension Lines -->
  <line x1="25" y1="46" x2="88" y2="46" stroke="#dc2626" stroke-width="1.2"/>
  <line x1="25" y1="42" x2="25" y2="50" stroke="#dc2626" stroke-width="1.2"/>
  <line x1="88" y1="42" x2="88" y2="50" stroke="#dc2626" stroke-width="1.2"/>
  <text x="45" y="43" font-family="monospace" font-size="6.5" fill="#dc2626" font-weight="bold">9mm PARABELLUM</text>
  <text x="100" y="65" font-family="monospace" font-size="6" fill="#334155">STRIATION: 6-R</text>
  <text x="100" y="75" font-family="monospace" font-size="6" fill="#334155">VELOCITY: 360m/s</text>
  <text x="100" y="85" font-family="monospace" font-size="6" fill="#334155">CASING: COPPER</text>
  <!-- Red Pushpin -->
  <ellipse cx="85" cy="14" rx="5" ry="2.5" fill="rgba(0,0,0,0.4)"/>
  <circle cx="85" cy="10" r="6" fill="url(#pinRed4)" stroke="#7f1d1d" stroke-width="0.8"/>
  <circle cx="83" cy="8" r="2" fill="#ff9999" opacity="0.8"/>
</svg>`)

// 6. Evidence Bag Card Containing Bloodied Combat Knife & Report Logs
const SVG_EVIDENCE_KNIFE = toUri(`<svg xmlns="http://www.w3.org/2000/svg" width="180" height="120" viewBox="0 0 180 120">
  <defs>
    <radialGradient id="pinBlack2" cx="35%" cy="35%" r="65%">
      <stop offset="0%" stop-color="#555555"/>
      <stop offset="70%" stop-color="#1a1a1a"/>
      <stop offset="100%" stop-color="#000000"/>
    </radialGradient>
  </defs>
  <!-- Plastic Evidence Bag Base -->
  <rect x="5" y="10" width="170" height="104" fill="rgba(245,247,250,0.92)" stroke="#94a3b8" stroke-width="1.5" rx="3"/>
  <line x1="5" y1="24" x2="175" y2="24" stroke="#64748b" stroke-width="1.5" stroke-dasharray="3,2"/>
  <!-- Red Evidence Seal Tag -->
  <rect x="15" y="28" width="150" height="16" fill="#b91c1c"/>
  <text x="22" y="39" font-family="monospace" font-size="8" font-weight="bold" fill="#ffffff">EVIDENCE BAG #402 - CONFIDENTIAL</text>
  <!-- Tactical Knife Vector -->
  <rect x="35" y="60" width="35" height="10" fill="#1e293b" rx="2"/>
  <polygon points="70,60 140,65 70,70" fill="#94a3b8" stroke="#475569" stroke-width="1"/>
  <!-- Blood Stain on Blade -->
  <path d="M 105 63 C 120 64, 135 65, 140 65 C 125 68, 110 68, 105 67 Z" fill="#7f1d1d"/>
  <!-- Report Log Table Lines -->
  <text x="15" y="90" font-family="monospace" font-size="6.5" fill="#334155">OFFICER: DET. VIVAD | DATE: 2026-10-02</text>
  <text x="15" y="100" font-family="monospace" font-size="6.5" fill="#334155">ITEM: COMBAT KNIFE WITH BIOLOGICAL TRACE</text>
  <!-- Translucent Tape Strip Top Left -->
  <rect x="2" y="4" width="32" height="12" fill="rgba(240,230,200,0.75)" transform="rotate(-15 15 10)"/>
  <!-- Black Pushpin -->
  <ellipse cx="90" cy="14" rx="5" ry="2.5" fill="rgba(0,0,0,0.4)"/>
  <circle cx="90" cy="10" r="6" fill="url(#pinBlack2)" stroke="#000" stroke-width="0.8"/>
  <circle cx="88" cy="8" r="2" fill="#888888" opacity="0.8"/>
</svg>`)

// 7. Torn Newspaper Clippings with Circled Columns
const SVG_NEWSPAPER_CLIPPING = toUri(`<svg xmlns="http://www.w3.org/2000/svg" width="170" height="105" viewBox="0 0 170 105">
  <defs>
    <radialGradient id="pinBlack3" cx="35%" cy="35%" r="65%">
      <stop offset="0%" stop-color="#555555"/>
      <stop offset="70%" stop-color="#1a1a1a"/>
      <stop offset="100%" stop-color="#000000"/>
    </radialGradient>
  </defs>
  <!-- Jagged Torn Edge Paper -->
  <path d="M 6 10 L 164 10 L 160 100 L 135 96 L 110 100 L 85 95 L 60 99 L 35 95 L 10 99 Z" fill="#eee7d5" stroke="#9e8a6e" stroke-width="1.5"/>
  <text x="16" y="24" font-family="serif" font-size="10" font-weight="bold" fill="#1c1917">THE DAILY CHRONICLE</text>
  <line x1="16" y1="27" x2="154" y2="27" stroke="#44403c" stroke-width="1"/>
  <!-- Dual Column Layout -->
  <rect x="16" y="32" width="62" height="58" fill="#e4dbcc"/>
  <rect x="86" y="32" width="68" height="58" fill="#e4dbcc"/>
  <!-- Red Wax Pencil Circle Around Key Article -->
  <ellipse cx="47" cy="60" rx="24" ry="16" fill="none" stroke="#dc2626" stroke-width="2.2"/>
  <!-- Black Pushpin -->
  <ellipse cx="85" cy="14" rx="5" ry="2.5" fill="rgba(0,0,0,0.4)"/>
  <circle cx="85" cy="10" r="6" fill="url(#pinBlack3)" stroke="#000" stroke-width="0.8"/>
  <circle cx="83" cy="8" r="2" fill="#888888" opacity="0.8"/>
</svg>`)

// 8. Printed Store Receipt Detailing Transaction Totals
const SVG_STORE_RECEIPT = toUri(`<svg xmlns="http://www.w3.org/2000/svg" width="150" height="115" viewBox="0 0 150 115">
  <defs>
    <radialGradient id="pinRed5" cx="35%" cy="35%" r="65%">
      <stop offset="0%" stop-color="#ff6b6b"/>
      <stop offset="70%" stop-color="#b91c1c"/>
      <stop offset="100%" stop-color="#450a0a"/>
    </radialGradient>
  </defs>
  <!-- Receipt Paper with Jagged Bottom -->
  <path d="M 10 10 L 140 10 L 140 102 L 130 108 L 120 102 L 110 108 L 100 102 L 90 108 L 80 102 L 70 108 L 60 102 L 50 108 L 40 102 L 30 108 L 20 102 L 10 108 Z" fill="#ffffff" stroke="#cbd5e1" stroke-width="1"/>
  <text x="35" y="24" font-family="monospace" font-size="8" font-weight="bold" fill="#0f172a">CORNER STORE #12</text>
  <line x1="20" y1="28" x2="130" y2="28" stroke="#94a3b8" stroke-width="0.8" stroke-dasharray="2,2"/>
  <text x="20" y="40" font-family="monospace" font-size="6.5" fill="#334155">1x HARDWARE ITEM  $14.99</text>
  <text x="20" y="50" font-family="monospace" font-size="6.5" fill="#334155">2x CLEANING PACK  $32.00</text>
  <line x1="20" y1="56" x2="130" y2="56" stroke="#94a3b8" stroke-width="0.8"/>
  <text x="20" y="68" font-family="monospace" font-size="7.5" font-weight="bold" fill="#0f172a">TOTAL CASH:       $46.99</text>
  <text x="20" y="78" font-family="monospace" font-size="6" fill="#64748b">TIME: 21:42:08 - CASHIER 04</text>
  <!-- Barcode Line -->
  <line x1="20" y1="88" x2="130" y2="88" stroke="#000000" stroke-width="4" stroke-dasharray="3,1,4,2,2,3,1"/>
  <!-- Top Tape Strip -->
  <rect x="55" y="3" width="40" height="12" fill="rgba(240,230,200,0.8)" transform="rotate(4 75 9)"/>
  <!-- Red Pushpin -->
  <ellipse cx="75" cy="14" rx="5" ry="2.5" fill="rgba(0,0,0,0.4)"/>
  <circle cx="75" cy="10" r="6" fill="url(#pinRed5)" stroke="#7f1d1d" stroke-width="0.8"/>
  <circle cx="73" cy="8" r="2" fill="#ff9999" opacity="0.8"/>
</svg>`)

// 9. Aged Yellowed Lined Index Card for Case Notes
const SVG_INDEX_CARD = toUri(`<svg xmlns="http://www.w3.org/2000/svg" width="170" height="95" viewBox="0 0 170 95">
  <defs>
    <radialGradient id="pinRed6" cx="35%" cy="35%" r="65%">
      <stop offset="0%" stop-color="#ff6b6b"/>
      <stop offset="70%" stop-color="#b91c1c"/>
      <stop offset="100%" stop-color="#450a0a"/>
    </radialGradient>
  </defs>
  <!-- Index Card Base -->
  <rect x="5" y="10" width="160" height="80" fill="#fef08a" stroke="#ca8a04" stroke-width="1.5"/>
  <!-- Margin & Ruled Lines -->
  <line x1="25" y1="10" x2="25" y2="90" stroke="#ef4444" stroke-width="1"/>
  <line x1="5" y1="26" x2="165" y2="26" stroke="#93c5fd" stroke-width="1"/>
  <line x1="5" y1="42" x2="165" y2="42" stroke="#93c5fd" stroke-width="1"/>
  <line x1="5" y1="58" x2="165" y2="58" stroke="#93c5fd" stroke-width="1"/>
  <line x1="5" y1="74" x2="165" y2="74" stroke="#93c5fd" stroke-width="1"/>
  <!-- Note Header -->
  <text x="32" y="22" font-family="monospace" font-size="7.5" font-weight="bold" fill="#713f12">INVESTIGATIVE FIELD NOTE</text>
  <!-- Red Pushpin -->
  <ellipse cx="85" cy="14" rx="5" ry="2.5" fill="rgba(0,0,0,0.4)"/>
  <circle cx="85" cy="10" r="6" fill="url(#pinRed6)" stroke="#7f1d1d" stroke-width="0.8"/>
  <circle cx="83" cy="8" r="2" fill="#ff9999" opacity="0.8"/>
</svg>`)

function resolveNodeSvg(node: cytoscape.NodeSingular): string {
  const kind = node.data('kind') || ''
  const label = (node.data('label') || '').toLowerCase()
  const detail = (node.data('detail') || '').toLowerCase()

  if (kind === 'case') return SVG_MAP_CENTER
  if (kind === 'party') return SVG_POLAROID
  if (kind === 'contradiction') return SVG_FORENSIC_SILHOUETTE
  if (kind === 'event') return SVG_NEWSPAPER_CLIPPING
  if (kind === 'claim') return SVG_INDEX_CARD
  if (kind === 'law') return SVG_BALLISTICS

  if (kind === 'evidence') {
    if (label.includes('bullet') || label.includes('gun') || label.includes('ballistics') || label.includes('firearm') || detail.includes('bullet')) {
      return SVG_BALLISTICS
    }
    if (label.includes('knife') || label.includes('weapon') || label.includes('blade') || label.includes('bag') || label.includes('blood') || detail.includes('knife')) {
      return SVG_EVIDENCE_KNIFE
    }
    if (label.includes('receipt') || label.includes('store') || label.includes('payment') || label.includes('transaction') || detail.includes('receipt')) {
      return SVG_STORE_RECEIPT
    }
    return SVG_FINGERPRINT
  }

  return SVG_INDEX_CARD
}

function styleSheet(): cytoscape.StylesheetJson {
  return [
    {
      selector: 'node',
      style: {
        shape: 'rectangle',
        'background-color': 'transparent',
        'background-image': (n: cytoscape.NodeSingular) => resolveNodeSvg(n),
        'background-fit': 'cover',
        'border-width': 0,
        label: 'data(label)',
        color: '#1a1612',
        'font-family': 'Special Elite, Courier New, monospace',
        'font-size': 9.5,
        'font-weight': 'bold',
        'text-wrap': 'wrap',
        'text-max-width': '140px',
        'text-valign': 'center',
        'text-halign': 'center',
        width: (n: cytoscape.NodeSingular) => (n.data('kind') === 'case' ? '240px' : n.data('kind') === 'contradiction' ? '180px' : '170px'),
        height: (n: cytoscape.NodeSingular) => (n.data('kind') === 'case' ? '160px' : n.data('kind') === 'contradiction' ? '115px' : '110px'),
      },
    },
    {
      selector: 'node[kind = "case"]',
      style: {
        'font-size': 11.5,
        'font-weight': 'bold',
        color: '#1a1612',
        'text-valign': 'bottom',
        'text-margin-y': -14,
      },
    },
    {
      selector: 'node[kind = "party"]',
      style: {
        'text-valign': 'bottom',
        'text-margin-y': -10,
        color: '#1a1612',
        'font-weight': 'bold',
      },
    },
    {
      selector: 'node[kind = "contradiction"]',
      style: {
        color: '#f87171',
        'font-weight': 'bold',
        'text-valign': 'center',
      },
    },
    {
      selector: 'node:selected',
      style: {
        'border-color': '#dc2626',
        'border-width': 3.5,
        'border-style': 'solid',
      },
    },
    {
      selector: '.dim',
      style: {
        opacity: 0.18,
      },
    },
    {
      selector: 'edge',
      style: {
        width: 3.5,
        'line-color': '#d32f2f', // BRIGHT CRIMSON RED STRING
        'line-style': 'solid',
        'target-arrow-color': '#b71c1c',
        'target-arrow-shape': 'circle', // Red Pushpin Head
        'source-arrow-color': '#b71c1c',
        'source-arrow-shape': 'circle', // Red Pushpin Head
        'curve-style': 'bezier',
        label: 'data(label)',
        color: '#ffffff',
        'font-family': 'Special Elite, Courier New, monospace',
        'font-size': 8.5,
        'text-rotation': 'autorotate',
        'text-background-color': '#b71c1c',
        'text-background-opacity': 0.95,
        'text-background-padding': '3px',
        'arrow-scale': 0.85,
      },
    },
    {
      selector: 'edge:selected',
      style: {
        width: 5.5,
        'line-color': '#ff0000',
        'source-arrow-color': '#ff0000',
        'target-arrow-color': '#ff0000',
      },
    },
  ] as cytoscape.StylesheetJson
}

export default function Graph() {
  const { caseData } = useCase()
  const box = useRef<HTMLDivElement>(null)
  const cy = useRef<Core | null>(null)
  const [info, setInfo] = useState({ n: 0, e: 0 })
  const [kinds, setKinds] = useState<string[]>([])
  const [hidden, setHidden] = useState<Set<string>>(new Set())
  const [selected, setSelected] = useState<J>(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const cid = caseData.id

  const toEls = (g: J) => {
    if (!g || !Array.isArray(g.nodes)) return []
    return [
      ...g.nodes.map((n: J) => ({ group: 'nodes' as const, data: n?.data || {} })),
      ...(Array.isArray(g.edges) ? g.edges : []).map((e: J) => ({ group: 'edges' as const, data: e?.data || {} })),
    ]
  }

  const layout = useCallback(() => {
    const w = box.current?.clientWidth || 1200
    const h = box.current?.clientHeight || 800
    cy.current
      ?.layout({
        name: 'cose',
        animate: false,
        randomize: true,
        nodeRepulsion: () => 350000,
        idealEdgeLength: () => 280,
        nodeOverlap: 80,
        gravity: 0.2,
        componentSpacing: 200,
        padding: 60,
        numIter: 3500,
        boundingBox: { x1: 0, y1: 0, w: w * 3, h: h * 3 },
      } as cytoscape.LayoutOptions)
      .run()
  }, [])

  const load = useCallback(async () => {
    if (!box.current) return
    setBusy(true)
    setErr('')
    try {
      const g = await api.get(`/cases/${cid}/graph`)
      if (!g || !Array.isArray(g.nodes)) {
        setInfo({ n: 0, e: 0 })
        return
      }
      if (!cy.current) {
        cy.current = cytoscape({
          container: box.current,
          elements: [],
          style: styleSheet(),
          wheelSensitivity: 0.25,
          minZoom: 0.1,
          maxZoom: 3,
        })
        cy.current.on('tap', 'node', (ev) => {
          if (!ev.target) return
          const d = ev.target.data()
          if (d) setSelected(d)
          cy.current?.elements().removeClass('dim')
          if (ev.target.closedNeighborhood) {
            cy.current?.elements().not(ev.target.closedNeighborhood()).addClass('dim')
          }
        })
        cy.current.on('tap', (ev) => {
          if (ev.target === cy.current) {
            setSelected(null)
            cy.current?.elements().removeClass('dim')
          }
        })
      }
      cy.current.elements().remove()
      cy.current.add(toEls(g))
      cy.current.resize()
      layout()
      cy.current.fit(undefined, 40)
      setInfo({ n: g.nodes.length, e: (g.edges || []).length })
      setKinds([...new Set<string>(g.nodes.map((n: J) => n.data?.kind || 'unknown'))].sort())
      setHidden(new Set())
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setBusy(false)
    }
  }, [cid, layout])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    const ro = new ResizeObserver(() => cy.current?.resize())
    if (box.current) ro.observe(box.current)
    return () => {
      ro.disconnect()
      cy.current?.destroy()
      cy.current = null
    }
  }, [])

  useEffect(() => {
    const c = cy.current
    if (!c) return
    try {
      c.batch(() => {
        c.nodes().forEach((n) => {
          const kind = n.data('kind')
          if (kind) {
            n.style('display', hidden.has(kind) ? 'none' : 'element')
          }
        })
      })
    } catch {
      /* empty */
    }
  }, [hidden, info])

  const deepLink = useMemo(() => {
    if (!selected) return null
    if (selected.evidence_id)
      return { to: `/cases/${cid}/evidence/${selected.evidence_id}`, text: 'OPEN EVIDENCE FILE' }
    if (selected.kind === 'claim')
      return { to: `/cases/${cid}/claims`, text: 'VIEW STATEMENTS & CLAIMS' }
    if (selected.kind === 'contradiction')
      return { to: `/cases/${cid}/contradictions`, text: 'INSPECT CONTRADICTION' }
    if (selected.kind === 'law')
      return { to: `/cases/${cid}/legal`, text: 'VIEW LEGAL STATUTES' }
    if (selected.kind === 'hearing')
      return { to: `/cases/${cid}/hearings`, text: 'VIEW HEARINGS' }
    return null
  }, [selected, cid])

  return (
    <div>
      {/* Top Evidence Board Toolbar */}
      <div className="flex flex-wrap items-center gap-2 mb-3 bg-[#1c1814] border border-[#4a3a28] p-2">
        <button
          className="btn btn-primary"
          onClick={() => {
            layout()
            cy.current?.fit(undefined, 40)
          }}
        >
          📌 [ RE-ARRANGE BOARD ]
        </button>
        <button
          className="btn"
          onClick={() => {
            setSelected(null)
            cy.current?.elements().removeClass('dim')
          }}
          disabled={!selected}
        >
          [ CLEAR FOCUS ]
        </button>
        <span className="lbl ml-auto text-[#d4af66]">
          {info.n} PINNED ASSETS · {info.e} CRIMSON STRING LINES {busy ? ' · INDEXING BOARD…' : ''}
        </span>
      </div>

      {/* Filter Checkboxes */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 mb-3 text-[12px] bg-[#171410] border border-[#36291a] px-3 py-2">
        <span className="lbl text-[#b59860]">FILTER BOARD ASSETS:</span>
        {kinds.map((k) => (
          <label key={k} className="cursor-pointer flex items-center gap-1 text-[#e0d6c3] font-mono">
            <input
              type="checkbox"
              checked={!hidden.has(k)}
              onChange={() =>
                setHidden((h) => {
                  const n = new Set(h)
                  if (n.has(k)) n.delete(k)
                  else n.add(k)
                  return n
                })
              }
            />{' '}
            {KIND_LABEL[k] || k.toUpperCase()}
          </label>
        ))}
      </div>

      {err && <div className="text-crit font-bold mb-2">{err}</div>}

      {/* Main Corkboard & Detective Notebook Layout */}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        
        {/* Corkboard Workspace Container */}
        <div
          className="cork-board-container overflow-hidden relative flex flex-col justify-between"
          style={{ height: 'calc(100vh - 250px)', minHeight: 620 }}
        >
          {/* Top Wooden Frame Brass Badge */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 z-10 pointer-events-none">
            <div className="cork-board-frame-label">
              📌 INVESTIGATIVE EVIDENCE CORKBOARD
            </div>
          </div>

          <div ref={box} style={{ width: '100%', height: '100%' }} />

          {info.n === 0 && !busy && (
            <div className="absolute inset-0 grid place-items-center text-[#d4af66] font-bold text-[14px]">
              NO EVIDENCE PINNED YET. RUN ANALYSIS TO BUILD THE BOARD.
            </div>
          )}
        </div>

        {/* Detective Field Notebook Inspector Panel */}
        <aside className="aged-paper-leaf p-4 border border-[#b8a483] flex flex-col justify-between min-h-[300px] font-mono text-[#1a1612] paper-stack-shadow">
          <div>
            <div className="flex items-center justify-between border-b-2 border-[#1a1612] pb-1 mb-3">
              <h3 className="text-[13px] tracking-[.14em] font-bold uppercase">
                FIELD NOTEBOOK INSPECTOR
              </h3>
              <span className="pushpin-badge" />
            </div>

            {!selected ? (
              <div className="quiet text-[12px] leading-relaxed">
                Click any pinned Polaroid snapshot, city map anchor, fingerprint card, or crimson string on the evidence board to inspect extracted relationships.
              </div>
            ) : (
              <div className="space-y-3">
                <Field k="Asset Category">
                  <span className="font-bold text-[#b91c1c]">
                    {KIND_LABEL[selected.kind] || selected.kind}
                  </span>
                </Field>
                <Field k="Asset Description">
                  <span className="font-bold text-[#1a1612]">{selected.label}</span>
                </Field>
                {selected.detail && (
                  <Field k="Forensic Notes">
                    <div className="bg-[#eee3ce] border border-[#c7b493] p-2 text-[11.5px] leading-snug">
                      {selected.detail}
                    </div>
                  </Field>
                )}
                {deepLink && (
                  <div className="pt-2">
                    <Link
                      className="btn btn-primary no-underline block text-center py-1.5 text-[11px] font-bold uppercase"
                      to={deepLink.to}
                    >
                      [ {deepLink.text} ]
                    </Link>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="text-[10px] tracking-wider text-[#6b5d4a] uppercase border-t border-[#c5b597] pt-2 mt-4 text-center font-bold">
            BRIGHT CRIMSON STRINGS LINK SCENE ASSETS &amp; TIMELINE LOGS
          </div>
        </aside>

      </div>
    </div>
  )
}
