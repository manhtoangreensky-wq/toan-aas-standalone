import os
import gzip
import json
from pathlib import Path

def get_file_info(filepath: Path):
    content = filepath.read_bytes()
    raw_size = len(content)
    try:
        gzip_size = len(gzip.compress(content))
    except Exception:
        gzip_size = raw_size
    return raw_size, gzip_size

def build_tree(root_dir: Path):
    tree = {"name": "root", "children": [], "size": 0, "gzip_size": 0}
    scan_dirs = ["static", "templates", "docs"]

    for s_dir in scan_dirs:
        base = root_dir / s_dir
        if not base.exists(): continue

        for p in base.rglob("*"):
            if p.is_file() and not p.name.startswith("."):
                rel_parts = p.relative_to(root_dir).parts
                raw_size, gzip_size = get_file_info(p)

                curr = tree
                for part in rel_parts[:-1]:
                    found = next((c for c in curr["children"] if c["name"] == part), None)
                    if not found:
                        found = {"name": part, "children": [], "size": 0, "gzip_size": 0}
                        curr["children"].append(found)
                    curr = found

                curr["children"].append({
                    "name": rel_parts[-1],
                    "path": str(p.relative_to(root_dir)).replace("\\", "/"),
                    "size": raw_size,
                    "gzip_size": gzip_size,
                    "ext": p.suffix
                })

    def rollup(node):
        if "children" in node and node["children"]:
            node["size"] = sum(rollup(c) for c in node["children"])
            node["gzip_size"] = sum(c.get("gzip_size", 0) for c in node["children"])
        return node["size"]

    rollup(tree)
    return tree

def generate_treemap_html(data, output_path: Path):
    data_json = json.dumps(data, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TOAN AAS — Interactive Bundle Treemap Visualizer</title>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: #0b1329;
      color: #f8fafc;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      height: 100vh;
    }}
    header {{
      background: #1e293b;
      padding: 10px 16px;
      display: flex;
      align-items: center;
      gap: 16px;
      border-bottom: 1px solid #334155;
      font-size: 13px;
    }}
    .filter-group {{
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .filter-group label {{
      color: #94a3b8;
      font-weight: 500;
    }}
    .filter-group input {{
      background: #0f172a;
      border: 1px solid #475569;
      border-radius: 4px;
      color: #f8fafc;
      padding: 5px 10px;
      font-size: 13px;
      min-width: 180px;
      outline: none;
    }}
    .filter-group input:focus {{
      border-color: #38bdf8;
    }}
    .breadcrumbs {{
      margin-left: auto;
      display: flex;
      align-items: center;
      gap: 6px;
      color: #38bdf8;
      font-weight: 600;
      cursor: pointer;
    }}
    .breadcrumbs span:hover {{
      text-decoration: underline;
    }}
    #chart-container {{
      flex: 1;
      position: relative;
      background: #060913;
    }}
    svg {{
      width: 100%;
      height: 100%;
      display: block;
    }}
    .node {{
      cursor: pointer;
      stroke: #0f172a;
      stroke-width: 1px;
      transition: fill-opacity 0.2s, stroke-width 0.2s;
    }}
    .node:hover {{
      stroke: #f8fafc;
      stroke-width: 2px;
    }}
    .node-label {{
      font-size: 11px;
      font-weight: 600;
      fill: #ffffff;
      pointer-events: none;
      text-shadow: 0 1px 3px rgba(0,0,0,0.8);
      user-select: none;
    }}
    .node-sublabel {{
      font-size: 9px;
      font-weight: 400;
      fill: rgba(255,255,255,0.85);
      pointer-events: none;
      text-shadow: 0 1px 2px rgba(0,0,0,0.8);
      user-select: none;
    }}
    .tooltip {{
      position: absolute;
      pointer-events: none;
      background: rgba(15, 23, 42, 0.95);
      border: 1px solid #38bdf8;
      border-radius: 6px;
      padding: 10px 14px;
      font-size: 12px;
      color: #f8fafc;
      box-shadow: 0 10px 25px rgba(0,0,0,0.5);
      backdrop-filter: blur(8px);
      z-index: 100;
      display: none;
    }}
    .tooltip-title {{
      font-weight: 700;
      color: #38bdf8;
      margin-bottom: 4px;
      word-break: break-all;
    }}
    .tooltip-stat {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      margin-top: 2px;
      color: #cbd5e1;
    }}
  </style>
</head>
<body>
  <header>
    <div style="font-weight:700; color:#38bdf8; font-size:14px; display:flex; align-items:center; gap:6px;">
      <span>📊 TOAN AAS Bundle Treemap Visualizer</span>
    </div>
    <div class="filter-group">
      <label>Exclude:</label>
      <input type="text" id="exclude-input" placeholder="*/**/*.min.js">
    </div>
    <div class="filter-group">
      <label>Include:</label>
      <input type="text" id="include-input" placeholder="*/**/*.js">
    </div>
    <div class="breadcrumbs" id="breadcrumbs">
      <span onclick="zoomTo(rootNode)">root</span>
    </div>
  </header>
  <div id="chart-container">
    <div class="tooltip" id="tooltip"></div>
    <svg id="treemap-svg"></svg>
  </div>

  <script>
    const data = {data_json};
    const colors = [
      "#6366f1", "#8b5cf6", "#ec4899", "#f43f5e",
      "#10b981", "#14b8a6", "#06b6d4", "#0ea5e9",
      "#f59e0b", "#d97706", "#84cc16", "#a855f7",
      "#3b82f6", "#22c55e", "#e11d48", "#7c3aed"
    ];

    let colorMap = {{}};
    let colorIdx = 0;
    function getColor(name) {{
      if (!colorMap[name]) {{
        colorMap[name] = colors[colorIdx % colors.length];
        colorIdx++;
      }}
      return colorMap[name];
    }}

    function formatBytes(bytes) {{
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }}

    const svg = d3.select("#treemap-svg");
    const container = document.getElementById("chart-container");
    const tooltip = document.getElementById("tooltip");
    const breadcrumbs = document.getElementById("breadcrumbs");

    let width = container.clientWidth;
    let height = container.clientHeight;
    let rootNode, currentFocus;

    function renderTreemap() {{
      width = container.clientWidth;
      height = container.clientHeight;
      svg.attr("viewBox", `0 0 ${{width}} ${{height}}`);

      const root = d3.hierarchy(data)
        .sum(d => d.children ? 0 : d.size)
        .sort((a, b) => b.value - a.value);

      d3.treemap()
        .size([width, height])
        .paddingTop(18)
        .paddingRight(2)
        .paddingInner(2)
        .round(true)(root);

      rootNode = root;
      currentFocus = root;
      updateChart(root);
    }}

    function updateChart(focusNode) {{
      currentFocus = focusNode;
      svg.selectAll("*").remove();

      let crumbs = [];
      let curr = focusNode;
      while (curr) {{
        crumbs.unshift(curr);
        curr = curr.parent;
      }}
      breadcrumbs.innerHTML = crumbs.map((c, i) =>
        `<span onclick="zoomToDepth(${{i}})">${{c.data.name}}</span>`
      ).join(" / ");

      d3.treemap()
        .size([width, height])
        .paddingTop(18)
        .paddingRight(2)
        .paddingInner(2)
        .round(true)(focusNode);

      const cell = svg.selectAll("g")
        .data(focusNode.leaves())
        .enter().append("g")
        .attr("transform", d => `translate(${{d.x0}},${{d.y0}})`);

      cell.append("rect")
        .attr("class", "node")
        .attr("width", d => Math.max(0, d.x1 - d.x0))
        .attr("height", d => Math.max(0, d.y1 - d.y0))
        .attr("fill", d => {{
          const group = d.ancestors().reverse()[1] || d;
          return getColor(group.data.name);
        }})
        .attr("fill-opacity", 0.75)
        .on("click", (e, d) => {{
          if (d.parent && d.parent !== focusNode) updateChart(d.parent);
        }})
        .on("mousemove", (e, d) => {{
          tooltip.style.display = "block";
          tooltip.style.left = (e.pageX + 15) + "px";
          tooltip.style.top = (e.pageY + 15) + "px";
          tooltip.innerHTML = `
            <div class="tooltip-title">${{d.data.path || d.data.name}}</div>
            <div class="tooltip-stat"><span>Parsed Size:</span><strong>${{formatBytes(d.data.size)}}</strong></div>
            <div class="tooltip-stat"><span>Gzip Estimate:</span><strong>${{formatBytes(d.data.gzip_size)}}</strong></div>
            <div class="tooltip-stat"><span>Share:</span><strong>${{((d.value / rootNode.value) * 100).toFixed(1)}}%</strong></div>
          `;
        }})
        .on("mouseleave", () => {{
          tooltip.style.display = "none";
        }});

      cell.append("text")
        .attr("class", "node-label")
        .attr("x", 4)
        .attr("y", 14)
        .text(d => (d.x1 - d.x0 > 50 && d.y1 - d.y0 > 25) ? d.data.name : "");

      cell.append("text")
        .attr("class", "node-sublabel")
        .attr("x", 4)
        .attr("y", 26)
        .text(d => (d.x1 - d.x0 > 70 && d.y1 - d.y0 > 38) ? formatBytes(d.data.size) : "");
    }}

    window.zoomTo = function(node) {{
      updateChart(node);
    }};

    window.zoomToDepth = function(depth) {{
      let curr = currentFocus;
      let crumbs = [];
      while (curr) {{
        crumbs.unshift(curr);
        curr = curr.parent;
      }}
      if (crumbs[depth]) updateChart(crumbs[depth]);
    }};

    window.addEventListener("resize", renderTreemap);
    renderTreemap();
  </script>
</body>
</html>'''

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"Generated Bundle Visualizer Treemap at: {output_path}")

if __name__ == "__main__":
    web_root = Path(__file__).resolve().parent.parent
    data = build_tree(web_root)
    out = web_root / "reports" / "bundle_analyzer.html"
    generate_treemap_html(data, out)
    out_static = web_root / "static" / "portal" / "bundle_analyzer.html"
    generate_treemap_html(data, out_static)
