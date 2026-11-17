import * as d3 from 'd3';
import { plotter } from '../../plot.js';

// Field for the "region" datatype: a list of shapes (rectangle, circle,
// free-form polygon) drawn on the 2D plot, in plot coordinates.  The server
// masks the pixels inside them (see reductus/dataflow/lib/regions.py).
//
//   {type: "rectangle", xmin, xmax, ymin, ymax}
//   {type: "circle", cx, cy, r}
//   {type: "polygon", points: [[x, y], ...]}

const TOOLS = ['none', 'rectangle', 'circle', 'free-form'];

// Free-form paths are thinned before they are stored: points closer than
// MIN_STEP_PX to the previous one are dropped while drawing, then the path is
// simplified to within SIMPLIFY_PX pixels so the saved region stays small.
const MIN_STEP_PX = 3;
const SIMPLIFY_PX = 1.5;

let template = `
<div class="fields region-field">
  <label>{{field.label}}</label>
  <div v-if="add_interactors" class="region-tools">
    <label
      v-for="opt in tools"
      :key="opt"
      style="border:1px solid grey;border-radius:2px;margin-right:2px;"
      >
      <input type="radio" name="region-tool" :value="opt" v-model="tool"/>
      {{opt == 'none' ? 'zoom' : opt}}
    </label>
  </div>
  <div
    class="region-item"
    v-for="(region, index) in local_value"
    :key="index"
    >
    <button style="color:red;font-weight:bold;" @click="remove(index)">x</button>
    <span class="region-summary">{{describe(region)}}</span>
  </div>
  <div v-if="local_value.length">
    <button @click="clear_all">clear all</button>
  </div>
</div>
`;

export const RegionUi = {
  name: 'region-ui',
  props: ['field', 'value', 'num_datasets_in', 'add_interactors'],
  data() {
    return {
      local_value: Array.isArray(this.value) ? this.value.map(r => ({ ...r })) : [],
      tool: 'rectangle',
      tools: TOOLS
    }
  },
  watch: {
    tool() { this.sync_tool() }
  },
  methods: {
    describe(region) {
      const f = (v) => (+v).toPrecision(4);
      if (region.type == 'rectangle') {
        return `rectangle x:[${f(region.xmin)}, ${f(region.xmax)}] y:[${f(region.ymin)}, ${f(region.ymax)}]`;
      }
      else if (region.type == 'circle') {
        return `circle center:(${f(region.cx)}, ${f(region.cy)}) r:${f(region.r)}`;
      }
      return `free-form, ${region.points.length} points`;
    },
    changed() {
      this.$emit('change', this.field.id, this.local_value.map(r => ({ ...r })));
      this.redraw();
    },
    add(region) {
      this.local_value.push(region);
      this.changed();
    },
    remove(index) {
      this.local_value.splice(index, 1);
      this.changed();
    },
    clear_all() {
      this.local_value.splice(0, this.local_value.length);
      this.changed();
    },

    // ---- drawing on the plot ----
    plot_group(chart) {
      // regions are drawn in the same coordinate system as chart.x()/y():
      // use the group that holds the data series, if there is one.
      const root = chart.svg.node();
      const series = root.querySelector('g.series');
      return (series && series.parentNode) ? series.parentNode : root;
    },
    redraw() {
      if (!this.overlay) { return }
      const x = this.chart.x(), y = this.chart.y();
      const shapes = this.overlay.select('g.region-shapes');
      shapes.selectAll('*').remove();
      const draw = (r, cls) => {
        if (r.type == 'rectangle') {
          const x1 = x(r.xmin), x2 = x(r.xmax), y1 = y(r.ymin), y2 = y(r.ymax);
          shapes.append('rect').attr('class', cls)
            .attr('x', Math.min(x1, x2)).attr('y', Math.min(y1, y2))
            .attr('width', Math.abs(x2 - x1)).attr('height', Math.abs(y2 - y1));
        }
        else if (r.type == 'circle') {
          // a circle in data coordinates; drawn as an ellipse if the axes
          // are not at equal scale, matching what is masked on the server
          shapes.append('ellipse').attr('class', cls)
            .attr('cx', x(r.cx)).attr('cy', y(r.cy))
            .attr('rx', Math.abs(x(r.cx + r.r) - x(r.cx)))
            .attr('ry', Math.abs(y(r.cy + r.r) - y(r.cy)));
        }
        else if (r.type == 'polygon') {
          shapes.append('polygon').attr('class', cls)
            .attr('points', r.points.map(p => `${x(p[0])},${y(p[1])}`).join(' '));
        }
      };
      this.local_value.forEach(r => draw(r, 'region-shape'));
      if (this.pending) { draw(this.pending, 'region-shape region-pending') }
      shapes.selectAll('.region-shape')
        .style('fill', 'red').style('fill-opacity', 0.25)
        .style('stroke', 'red').style('stroke-width', 1.5)
        .style('pointer-events', 'none');
      shapes.selectAll('.region-pending').style('stroke-dasharray', '4,3');
    },
    sync_tool() {
      // the capture layer only takes pointer events while a drawing tool
      // is active, so that zooming and panning still work with "zoom".
      if (!this.capture) { return }
      this.capture.style('pointer-events', (this.tool == 'none') ? 'none' : 'all')
        .style('cursor', (this.tool == 'none') ? null : 'crosshair');
    },
    setup_drawing(chart) {
      const vm = this;
      const group = this.plot_group(chart);
      const x = () => chart.x(), y = () => chart.y();
      const xr = x().range(), yr = y().range();

      const overlay = d3.select(group).append('g').attr('class', 'region-overlay');
      overlay.append('g').attr('class', 'region-shapes');
      const capture = overlay.append('rect')
        .attr('class', 'region-capture')
        .attr('x', Math.min(...xr)).attr('y', Math.min(...yr))
        .attr('width', Math.abs(xr[1] - xr[0])).attr('height', Math.abs(yr[1] - yr[0]))
        .style('fill', 'none');
      this.overlay = overlay;
      this.capture = capture;
      this.chart = chart;

      let start = null;   // [px, py] where the drag began
      let path = null;    // free-form: pixel points so far

      const to_data = (p) => [x().invert(p[0]), y().invert(p[1])];
      const pointer = (event) => d3.pointer(event, overlay.node());

      capture.on('pointerdown', function (event) {
        if (vm.tool == 'none') { return }
        event.preventDefault();
        event.stopPropagation();
        this.setPointerCapture(event.pointerId);
        start = pointer(event);
        path = [start];
      });

      capture.on('pointermove', function (event) {
        if (!start) { return }
        const p = pointer(event);
        if (vm.tool == 'rectangle') {
          const a = to_data(start), b = to_data(p);
          vm.pending = {
            type: 'rectangle',
            xmin: Math.min(a[0], b[0]), xmax: Math.max(a[0], b[0]),
            ymin: Math.min(a[1], b[1]), ymax: Math.max(a[1], b[1])
          };
        }
        else if (vm.tool == 'circle') {
          // radius is measured along x, in data units
          const c = to_data(start), e = to_data(p);
          const dx = e[0] - c[0], dy = e[1] - c[1];
          vm.pending = { type: 'circle', cx: c[0], cy: c[1], r: Math.hypot(dx, dy) };
        }
        else {
          const last = path[path.length - 1];
          if (Math.hypot(p[0] - last[0], p[1] - last[1]) >= MIN_STEP_PX) {
            path.push(p);
          }
          if (path.length >= 3) {
            vm.pending = { type: 'polygon', points: path.map(to_data) };
          }
        }
        vm.redraw();
      });

      const finish = function (event) {
        if (!start) { return }
        const pending = vm.pending;
        const pts = path;
        start = null;
        path = null;
        vm.pending = null;
        if (vm.tool == 'free-form') {
          const simple = simplify(pts, SIMPLIFY_PX);
          if (simple.length >= 3) {
            vm.add({ type: 'polygon', points: simple.map(to_data) });
            return;
          }
        }
        else if (pending && vm.is_nonempty(pending)) {
          vm.add(pending);
          return;
        }
        vm.redraw();  // a click with no drag draws nothing
      };
      capture.on('pointerup', finish);
      capture.on('pointercancel', finish);

      // keep drawn shapes in place when the plot is zoomed or resized
      const svg = chart.svg.node().ownerSVGElement || chart.svg.node();
      const refresh = () => requestAnimationFrame(() => vm.redraw());
      svg.addEventListener('wheel', refresh, { passive: true });
      svg.addEventListener('pointerup', refresh);
      this.teardown = () => {
        svg.removeEventListener('wheel', refresh);
        svg.removeEventListener('pointerup', refresh);
        overlay.remove();
      };

      this.sync_tool();
      this.redraw();
    },
    is_nonempty(region) {
      if (region.type == 'rectangle') {
        return region.xmax > region.xmin && region.ymax > region.ymin;
      }
      return region.r > 0;
    }
  },
  mounted() {
    if (!this.add_interactors) { return }
    const chart = plotter.instance.active_plot;
    if (!chart || !chart.svg || typeof chart.x !== 'function') {
      console.warn('No active 2D chart found, cannot add region tools');
      return;
    }
    this.setup_drawing(chart);
  },
  beforeUnmount() {
    if (this.teardown) { this.teardown() }
  },
  template
}

// Ramer-Douglas-Peucker line simplification, on pixel points.
function simplify(points, epsilon) {
  if (points.length < 3) { return points }
  const keep = new Array(points.length).fill(false);
  keep[0] = keep[points.length - 1] = true;
  const stack = [[0, points.length - 1]];
  while (stack.length) {
    const [first, last] = stack.pop();
    let max_dist = 0, index = -1;
    for (let i = first + 1; i < last; i++) {
      const d = distance_to_segment(points[i], points[first], points[last]);
      if (d > max_dist) { max_dist = d; index = i }
    }
    if (index > -1 && max_dist > epsilon) {
      keep[index] = true;
      stack.push([first, index], [index, last]);
    }
  }
  return points.filter((p, i) => keep[i]);
}

function distance_to_segment(p, a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const len2 = dx * dx + dy * dy;
  if (len2 == 0) { return Math.hypot(p[0] - a[0], p[1] - a[1]) }
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / len2));
  return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy));
}
