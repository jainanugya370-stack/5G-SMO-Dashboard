// Topology data embedded directly — no fetch() needed, works inside Grafana iframes
const topologyData = {
  "nodes": [
    { "id": "core",         "label": "5G CORE",             "type": "core" },
    { "id": "ran",          "label": "RAN",                  "type": "ran" },
    { "id": "ims",          "label": "IMS",                  "type": "ims" },
    { "id": "upf",          "label": "UPF",                  "type": "upf" },
    { "id": "gnb1",         "label": "gNB-001:01:000ff19",   "type": "gnb" },
    { "id": "gnb2",         "label": "gNB-001:01:000000b",   "type": "gnb" },
    { "id": "gnb3",         "label": "gNB-001:01:000fff8",   "type": "gnb" },
    { "id": "gnb4",         "label": "gNB-001:01:000fff4",   "type": "gnb" },
    { "id": "gnb5",         "label": "gNB-001:01:000001f",   "type": "gnb" },
    { "id": "upf_instance", "label": "upf",                  "type": "upf_instance" }
  ],
  "edges": [
    { "source": "core", "target": "ran" },
    { "source": "core", "target": "ims" },
    { "source": "core", "target": "upf" },
    { "source": "ran",  "target": "gnb1" },
    { "source": "ran",  "target": "gnb2" },
    { "source": "ran",  "target": "gnb3" },
    { "source": "ran",  "target": "gnb4" },
    { "source": "ran",  "target": "gnb5" },
    { "source": "upf",  "target": "upf_instance" }
  ]
};

const positions = {
    core:         { x: 750,  y: 120 },
    ran:          { x: 450,  y: 300 },
    ims:          { x: 750,  y: 300 },
    upf:          { x: 1050, y: 300 },
    gnb1:         { x: 150,  y: 520 },
    gnb2:         { x: 370,  y: 520 },
    gnb3:         { x: 590,  y: 520 },
    gnb4:         { x: 810,  y: 520 },
    gnb5:         { x: 1030, y: 520 },
    upf_instance: { x: 1050, y: 480 }
};

(function () {

    const elements = [];

    topologyData.nodes.forEach(node => {
        elements.push({
            data: { id: node.id, label: node.label, type: node.type },
            position: positions[node.id]
        });
    });

    topologyData.edges.forEach(edge => {
        elements.push({
            data: { source: edge.source, target: edge.target }
        });
    });

    const cy = cytoscape({
        container: document.getElementById('cy'),
        elements,
        layout: { name: 'preset' },
        zoomingEnabled:     false,
        userZoomingEnabled: false,
        panningEnabled:     false,
        style: [
            {
                selector: 'edge',
                style: {
                    'width':      2,
                    'line-color': '#63d6ff'
                }
            },
            {
                selector: 'node[type="core"]',
                style: {
                    'shape':             'round-rectangle',
                    'width':             110, 'height': 90,
                    'background-color':  '#18243a',
                    'background-image':  'icons/server.png',
                    'background-fit':    'contain',
                    'background-width':  '65%',
                    'background-height': '65%',
                    'border-width':      4,
                    'border-color':      '#00ff88',
                    'label':             'data(label)',
                    'text-valign':       'top',
                    'text-margin-y':     -14,
                    'font-size':         '15px',
                    'font-weight':       'bold',
                    'color':             'white'
                }
            },
            {
                selector: 'node[type="ran"]',
                style: {
                    'shape':             'round-rectangle',
                    'width':             110, 'height': 90,
                    'background-color':  '#18243a',
                    'background-image':  'icons/antenna.png',
                    'background-fit':    'contain',
                    'background-width':  '65%',
                    'background-height': '65%',
                    'border-width':      4,
                    'border-color':      '#ff4d4d',
                    'label':             'data(label)',
                    'text-valign':       'top',
                    'text-margin-y':     -14,
                    'font-size':         '15px',
                    'font-weight':       'bold',
                    'color':             'white'
                }
            },
            {
                selector: 'node[type="ims"]',
                style: {
                    'shape':             'round-rectangle',
                    'width':             110, 'height': 90,
                    'background-color':  '#18243a',
                    'background-image':  'icons/phone.png',
                    'background-fit':    'contain',
                    'background-width':  '65%',
                    'background-height': '65%',
                    'border-width':      4,
                    'border-color':      '#ff4d4d',
                    'label':             'data(label)',
                    'text-valign':       'top',
                    'text-margin-y':     -14,
                    'font-size':         '15px',
                    'font-weight':       'bold',
                    'color':             'white'
                }
            },
            {
                selector: 'node[type="upf"]',
                style: {
                    'shape':            'ellipse',
                    'width':            90, 'height': 90,
                    'background-color': '#18243a',
                    'border-width':     4,
                    'border-color':     '#00ff88',
                    'label':            'data(label)',
                    'font-size':        '18px',
                    'font-weight':      'bold',
                    'color':            'white',
                    'text-valign':      'center'
                }
            },
            {
                selector: 'node[type="upf_instance"]',
                style: {
                    'shape':            'ellipse',
                    'width':            140, 'height': 40,
                    'background-color': '#18243a',
                    'border-width':     4,
                    'border-color':     '#00ff88',
                    'label':            'data(label)',
                    'font-size':        '12px',
                    'color':            'white',
                    'text-valign':      'center'
                }
            },
            {
                selector: 'node[type="gnb"]',
                style: {
                    'shape':            'ellipse',
                    'width':            150, 'height': 38,
                    'background-color': '#18243a',
                    'border-width':     4,
                    'border-color':     '#ff4d4d',
                    'label':            'data(label)',
                    'font-size':        '8px',
                    'color':            'white',
                    'text-wrap':        'none',
                    'text-valign':      'center',
                    'text-halign':      'center'
                }
            }
        ]
    });

    cy.fit();
    cy.center();

})();