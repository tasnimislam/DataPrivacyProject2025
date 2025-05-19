# --- Imports ---
from dash import Dash, html, dcc, Input, Output, State, ctx
import dash_cytoscape as cyto
from flask_caching import Cache
from arango import ArangoClient
import random, re
import dash

# --- ArangoDB Setup ---
client = ArangoClient()
db = client.db("DP_Project", username="root", password="openSesame")

# --- App Setup ---
app = Dash(__name__)
app.title = "Company-Third Party Graph"
cache = Cache(app.server, config={"CACHE_TYPE": "SimpleCache"})

# --- Utility Functions ---
def normalize_class_name(name):
    return name.strip().lower().replace(" ", "_").replace("-", "_")

@cache.memoize(timeout=300)
def get_data_types_and_colors():
    companies = list(db.collection('companies1').all())
    data_types = sorted(set(dtype.strip() for c in companies for dtype in c.get('DataShared', []) if dtype.strip()))

    palette = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
        "#bcbd22", "#17becf"
    ]
    color_map = {
        normalize_class_name(dtype): palette[i % len(palette)]
        for i, dtype in enumerate(data_types)
    }
    return data_types, color_map

@cache.memoize(timeout=300)
def fetch_graph(filtered_types=None, limit=5000):
    elements, edge_count = [], 0
    companies = {c['_key']: c for c in db.collection('companies1').all()}
    third_parties = {tp['_key']: tp for tp in db.collection('third_parties1').all()}
    edges = db.collection('shares_with1').all()
    color_map = get_data_types_and_colors()[1]
    used_ids = set()

    for edge in edges:
        if edge_count >= limit:
            break
        source, target = edge['_from'].split('/')[-1], edge['_to'].split('/')[-1]
        company = companies.get(source)
        third_party = third_parties.get(target)
        if not company or not third_party:
            continue

        for dtype in company.get('DataShared', []):
            dtype_clean = dtype.strip()
            if not dtype_clean or (filtered_types and dtype_clean not in filtered_types):
                continue
            class_name = normalize_class_name(dtype_clean)
            elements.append({
                'data': {
                    'id': f"{source}->{target}->{class_name}",
                    'source': source,
                    'target': target,
                    'label': dtype_clean
                },
                'classes': class_name
            })
            used_ids.update([source, target])
            edge_count += 1

    for uid in used_ids:
        if uid in companies:
            company = companies[uid]
            elements.append({'data': {'id': uid, 'label': company['companyName'], 'type': 'company'}})
        elif uid in third_parties:
            tp = third_parties[uid]
            elements.append({'data': {'id': uid, 'label': tp['companyName'], 'type': 'third_party'}})

    return elements, color_map

# --- Layout Setup ---
data_types, color_map = get_data_types_and_colors()
preloaded_elements, color_map = fetch_graph()
default_layout = {'name': 'concentric', 'spacingFactor': 1.5}

app.layout = html.Div([
    html.Link(href='https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap', rel='stylesheet'),

    html.H1("📊 Company–Third Party Data Sharing", style={
        'textAlign': 'center',
        'fontFamily': 'Inter',
        'fontWeight': '600',
        'color': '#222',
        'margin': '20px 0'
    }),

    html.Div([
        html.Div([
            html.Label("🎯 Filter by data type", style={'marginBottom': '5px'}),
            dcc.Dropdown(
                id='filter-dropdown',
                options=[{'label': dt, 'value': dt} for dt in data_types],
                multi=True,
                placeholder="Choose data types...",
                style={'marginBottom': '20px'}
            ),

            html.Label("📐 Graph Layout", style={'marginBottom': '5px'}),
            dcc.Dropdown(
                id='layout-dropdown',
                options=[{'label': name.title(), 'value': name} for name in ['concentric', 'cose', 'breadthfirst']],
                value='concentric',
                clearable=False
            ),

            html.Div([
                html.H5("🎨 Legend", style={'marginTop': '25px', 'marginBottom': '10px'}),
                html.Ul([
                    html.Li([
                        html.Span(style={
                            'display': 'inline-block', 'width': '12px', 'height': '12px',
                            'backgroundColor': color, 'marginRight': '8px', 'verticalAlign': 'middle', 'borderRadius': '50%'
                        }),
                        html.Span(dtype, style={'fontSize': '13px'})
                    ], style={'listStyleType': 'none', 'marginBottom': '6px'})
                    for dtype, color in color_map.items()
                ], style={'paddingLeft': '0'})
            ])
        ], style={
            'flex': '1',
            'padding': '20px',
            'backgroundColor': '#f7f9fc',
            'borderRadius': '10px',
            'boxShadow': '0 3px 10px rgba(0,0,0,0.05)',
            'minWidth': '260px'
        }),

        html.Div([
            html.Label("💬 Ask a question", style={'marginBottom': '5px'}),
            dcc.Input(id='query-input', placeholder='Type your question...', debounce=True, style={
                'width': '100%', 'padding': '10px', 'borderRadius': '8px', 'border': '1px solid #ccc'
            }),
            html.Div([
                html.Button('Submit', id='submit-button', n_clicks=0, className='action-btn'),
                html.Button('Reset Graph', id='reset-button', n_clicks=0, className='action-btn', style={'marginLeft': '10px'})
            ], style={'marginTop': '10px'})
        ], style={
            'flex': '1',
            'padding': '20px',
            'backgroundColor': '#f7f9fc',
            'borderRadius': '10px',
            'boxShadow': '0 3px 10px rgba(0,0,0,0.05)',
            'minWidth': '260px'
        }),
    ], style={
        'display': 'flex',
        'gap': '30px',
        'flexWrap': 'wrap',
        'justifyContent': 'center',
        'margin': '30px auto',
        'maxWidth': '1000px'
    }),

    html.Div(id='chat-response', style={
        'whiteSpace': 'pre-line',
        'margin': '20px auto',
        'width': '90%',
        'backgroundColor': '#fff',
        'padding': '15px',
        'borderRadius': '8px',
        'boxShadow': '0 2px 6px rgba(0,0,0,0.04)',
        'fontFamily': 'Inter'
    }),

    cyto.Cytoscape(
        id='cytoscape',
        layout=default_layout,
        style={'width': '100%', 'height': '700px', 'marginTop': '10px'},
        elements=preloaded_elements,
        zoom=1,
        stylesheet=[
            {
                'selector': '[type = "company"]',
                'style': {
                    'background-color': '#4B7BE5',
                    'label': 'data(label)',
                    'width': 65,
                    'height': 65,
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'font-size': 13,
                    'color': '#fff',
                    'text-outline-color': '#4B7BE5',
                    'text-outline-width': 2,
                    'border-color': '#fff',
                    'border-width': 2
                }
            },
            {
                'selector': '[type = "third_party"]',
                'style': {
                    'background-color': '#E85151',
                    'label': 'data(label)',
                    'width': 55,
                    'height': 55,
                    'font-size': 12,
                    'color': '#fff',
                    'text-outline-color': '#E85151',
                    'text-outline-width': 2,
                    'border-color': '#fff',
                    'border-width': 2
                }
            },
            {
                'selector': 'edge',
                'style': {
                    'curve-style': 'bezier',
                    'target-arrow-shape': 'triangle',
                    'arrow-scale': 1,
                    'line-color': '#ccc',
                    'target-arrow-color': '#ccc',
                    'width': 2,
                    'opacity': 0.6
                }
            },
            {
                'selector': '.highlight',
                'style': {
                    'background-color': '#FFD700',
                    'line-color': '#FFD700',
                    'target-arrow-color': '#FFD700',
                    'transition-property': 'background-color, line-color, target-arrow-color',
                    'transition-duration': '0.5s'
                }
            },
            *[
                {'selector': f'.{cls}', 'style': {
                    'line-color': color,
                    'target-arrow-color': color
                }} for cls, color in color_map.items()
            ]
        ]
    )
], style={'fontFamily': 'Inter'})


# --- Callback ---
@app.callback(
    Output('cytoscape', 'elements'),
    Output('cytoscape', 'layout'),
    Output('cytoscape', 'zoom'),
    Output('cytoscape', 'pan'),
    Output('chat-response', 'children'),
    Input('submit-button', 'n_clicks'),
    Input('filter-dropdown', 'value'),
    Input('reset-button', 'n_clicks'),
    Input('layout-dropdown', 'value'),
    Input('cytoscape', 'tapNode'),
    State('query-input', 'value'),
    prevent_initial_call=True
)
def update_graph(n_submit, filters, n_reset, layout_choice, tapped_node, query):
    triggered = ctx.triggered_id
    response = ""

    layout_map = {
        'concentric': {
            'name': 'concentric',
            'spacingFactor': 0.3,
            'minNodeSpacing': 8,
            'equidistant': True,
            'avoidOverlap': True,
            'animate': False
        },
        'cose': {
            'name': 'cose',
            'nodeRepulsion': 80000,
            'idealEdgeLength': 100
        },
        'breadthfirst': {
    'name': 'breadthfirst',
    'spacingFactor': 3.0,
    'directed': True,
    'padding': 30,
    'animate': False,
    'avoidOverlap': True}

    }

    layout = layout_map.get(layout_choice, {'name': 'preset'})

    # Reset button
    if triggered == 'reset-button':
        elements, _ = fetch_graph()
        return elements, layout_map['concentric'], 1, {'x': 0, 'y': 0}, ""

    # Submit button for queries
    if triggered == 'submit-button' and query:
        q = query.lower()

        if "most third parties" in q:
            n_match = re.search(r"which (\d+) companies", q)
            n = int(n_match.group(1)) if n_match else 1
            companies = db.collection('companies1').all()
            edges = db.collection('shares_with1').all()

            conn_count = {}
            for edge in edges:
                source = edge['_from'].split('/')[-1]
                conn_count[source] = conn_count.get(source, 0) + 1

            top_companies = sorted(conn_count.items(), key=lambda x: x[1], reverse=True)[:n]
            response_lines = []
            for cid, count in top_companies:
                company = db.collection('companies1').get(cid)
                if company:
                    response_lines.append(f"⭐ {company['companyName']} — {count} third parties")

            response = "\n".join(response_lines)
            elements, _ = fetch_graph()
            return elements, layout, 1, {'x': 0, 'y': 0}, response

        elif match := re.search(r"companies.*share.* ([\w\s]+?) data", q):
            dtype = match.group(1).strip().title()
            elements, _ = fetch_graph(filtered_types=[dtype])
            ids = {el['data']['id'] for el in elements if el['data'].get('type') == 'company'}
            names = [db.collection('companies1').get(cid)['companyName'] for cid in ids]
            response = f"📌 Companies sharing {dtype} data:\n" + "\n".join(names)
            return elements, layout, 1, {'x': 0, 'y': 0}, response

        elif match := re.search(r"graph.*(?:for|of) (.+)", q):
            name = match.group(1).strip().lower()
            companies = list(db.collection('companies1').all())
            match_company = next((c for c in companies if name in c['companyName'].lower()), None)

            if match_company:
                match_id = match_company['_key']
                edges = db.collection('shares_with1').all()
                connected_edges = [e for e in edges if e['_from'].split('/')[-1] == match_id]
                third_party_ids = {e['_to'].split('/')[-1] for e in connected_edges}
                elements = []

                for e in connected_edges:
                    source = match_id
                    target = e['_to'].split('/')[-1]
                    company = db.collection('companies1').get(source)
                    for dtype in company.get('DataShared', []):
                        class_name = normalize_class_name(dtype)
                        elements.append({
                            'data': {
                                'id': f"{source}->{target}->{class_name}",
                                'source': source,
                                'target': target,
                                'label': dtype
                            },
                            'classes': class_name + ' highlight'
                        })

                elements.append({
                    'data': {
                        'id': match_id,
                        'label': match_company['companyName'],
                        'type': 'company'
                    },
                    'classes': 'highlight'
                })

                for tp_id in third_party_ids:
                    tp = db.collection('third_parties1').get(tp_id)
                    if tp:
                        elements.append({
                            'data': {
                                'id': tp_id,
                                'label': tp['companyName'],
                                'type': 'third_party'
                            },
                            'classes': 'highlight'
                        })

                response = f"🔍 Showing graph for {match_company['companyName']} and its third parties."
                return elements, layout, 1, {'x': 0, 'y': 0}, response
            else:
                response = f"❌ No company found with name matching '{name}'."
                elements, _ = fetch_graph(filtered_types=filters if filters else None)
                return elements, layout, 1, {'x': 0, 'y': 0}, response

            return elements, layout, 1, {'x': 0, 'y': 0}, response

        else:
            response = "❓ Try asking:\n- Which 5 companies have most third parties?\n- Which companies share health data?\n- Show me the graph of UPS."
            elements, _ = fetch_graph(filtered_types=filters if filters else None)
            return elements, layout, 1, {'x': 0, 'y': 0}, response

    # Tapped node
    if triggered == 'cytoscape' and tapped_node:
        node_id = tapped_node['data']['id']
        elements, _ = fetch_graph(filtered_types=filters if filters else None)

        connected_node_ids = set()
        for el in elements:
            el['classes'] = ' '.join(cls for cls in el.get('classes', '').split() if cls != 'highlight')

        for el in elements:
            data = el.get('data', {})
            source = data.get('source')
            target = data.get('target')
            if source == node_id or target == node_id:
                el['classes'] = el.get('classes', '') + ' highlight'
                connected_node_ids.update([source, target])

        for el in elements:
            if el.get('data', {}).get('id') in connected_node_ids:
                el['classes'] = el.get('classes', '') + ' highlight'

        # Fetch metadata from database
        node_doc = db.collection('companies1').get(node_id) or db.collection('third_parties1').get(node_id)
        if node_doc:
            if 'companyInfo' in node_doc:
                purpose = node_doc['companyInfo'].get('companyPurpose', 'N/A')
                origin = node_doc['companyInfo'].get('companyOrigin', 'N/A')
                response = (
                    f"📍 **{node_doc['companyName']}**\n\n"
                    f"🧭 Purpose: {purpose}\n"
                    f"🌍 Origin: {origin}\n"
                )
            elif 'thirdPartyInfo' in node_doc:
                purpose = node_doc['thirdPartyInfo'].get('companyPurpose', 'N/A')
                origin = node_doc['thirdPartyInfo'].get('companyOrigin', 'N/A')
                source = node_doc.get('infoSourceURL', 'N/A')
                response = (
                    f"📍 **{node_doc['companyName']}**\n\n"
                    f"🧭 Purpose: {purpose}\n"
                    f"🌍 Origin: {origin}\n"
                    f"🔗 Source: {source}"
                )
            else:
                purpose = origin = source = "N/A"
                response = (
                    f"📍 **{node_doc['companyName']}**\n\n"
                    f"🧭 Purpose: {purpose}\n"
                    f"🌍 Origin: {origin}\n"
                    f"🔗 Source: {source}"
                )
        else:
            response = f"⚠️ Metadata for node `{node_id}` not found."

        return elements, layout, dash.no_update, dash.no_update, response

    # Default fetch for filter or fallback
    elements, _ = fetch_graph(filtered_types=filters if filters else None)
    return elements, layout, 1, {'x': 0, 'y': 0}, response



# --- Main ---
if __name__ == '__main__':
    cache.clear()
    app.run(debug=True)
