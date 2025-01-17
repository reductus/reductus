import {
  d3,
  rectangleInteractor,
  ellipseInteractor,
  xSliceInteractor,
  ySliceInteractor,
  angleSliceInteractor
} from '../../libraries.js';
import { plotter } from '../../plot.js';

let template = `
<div class="fields">
  <label>
    {{field.label}}
    <div v-for="(axis, index) in axes">
      <label>
        {{axis}}
        <input
          type="number"
          :placeholder="(field.default || [])[index]"
          v-model="local_value[index]"
          @change="changed"
        />
      </label>
    </div>
  </label>
</div>
`;

export const RangeUi = {
  name: "range-ui",
  props: ["field", "value", "num_datasets_in", "add_interactors"],
  data: function () {
    let axes_lookups = {
      'x': ['xmin', 'xmax'],
      'y': ['ymin', 'ymax'],
      'xy': ['xmin', 'xmax', 'ymin', 'ymax'],
      'ellipse': ['cx', 'cy', 'rx', 'ry'],
      'sector_centered': ['angle_offset', 'angle_width']
    };
    let axes = axes_lookups[this.field.typeattr.axis];
    let local_value = axes.map((a, i) => ((this.value || [])[i]));
    return {
      local_value,
      axes_lookups,
      interactors: [],
      plot_ranges: []
    }
  },
  computed: {
    axes() {
      return this.axes_lookups[this.axis_str] || [];
    },
    axis_str() {
      return this.field.typeattr.axis || "";
    },
    default_value() {
      return this.axes.map((a, i) => ((this.local_value && this.local_value[i] != null) ? this.local_value[i] : this.field.default[i]));
    }
  },
  methods: {
    changed(updateInteractors = true) {
      this.local_value.forEach((x,i) => { this.$set(this.local_value, i, (isNaN(+x) || x == null) ? null : +x) });
      this.$emit('change', this.field.id, this.local_value);
      if (updateInteractors) {
        this.interactors.forEach(I => {
          if (I.update) I.update()
        })
      }
    }
  },
  mounted: function () {
    // create the interactor here, if commanded
    if (this.add_interactors) {
      let chart = plotter.instance.active_plot;
      let x = chart.x();
      let y = chart.y();
      let buffer = 10;
      let xrange = x.range();
      let xdir = Math.sign(xrange[1] - xrange[0]);
      let yrange = y.range();
      let ydir = Math.sign(yrange[1] - yrange[0]);
      let xdomain = [x.invert(xrange[0] + buffer * xdir), x.invert(xrange[1] - buffer * xdir)].sort()
      let ydomain = [y.invert(yrange[0] + buffer * ydir), y.invert(yrange[1] - buffer * ydir)].sort()
      let interactor = interactorConnectors[this.axis_str](this, xdomain, ydomain);
      interactor.dispatch.on("end", () => { this.changed(false) })
      chart.interactors(interactor);
      this.interactors.push(interactor);
    }
  },
  template
}

var interactorConnectors = {
  'x': add_x_interactor,
  'y': add_y_interactor,
  'xy': add_xy_interactor,
  'ellipse': add_ellipse_interactor,
  'sector_centered': add_sector_centered_interactor
}

function add_x_interactor(vm, xrange, yrange) {
  let value = vm.local_value;
  var opts = {
    type: 'xrange',
    name: 'xrange',
    color1: 'blue',
    show_lines: true,
    get x1() { return (vm.default_value[0] == null) ? xrange[0] : vm.default_value[0] },
    get x2() { return (vm.default_value[1] == null) ? xrange[1] : vm.default_value[1] },
    set x1(x) { vm.$set(value, 0, x) },
    set x2(x) { vm.$set(value, 1, x) }
  }
  return new xSliceInteractor(opts, null, null, d3);
}

function add_y_interactor(vm, xrange, yrange) {
  let value = vm.local_value;
  var opts = {
    type: 'yrange',
    name: 'yrange',
    color1: 'red',
    show_lines: true,
    get y1() { return (vm.default_value[0] == null) ? yrange[0] : vm.default_value[0] },
    get y2() { return (vm.default_value[1] == null) ? yrange[1] : vm.default_value[1] },
    set y1(x) { vm.$set(value, 0, x) },
    set y2(x) { vm.$set(value, 1, x) }
  }
  return new ySliceInteractor(opts, null, null, d3);
}

function add_xy_interactor(vm, xrange, yrange) {
  let value = vm.local_value;
  let default_value = vm.default_value;
  var opts = {
    type: 'Rectangle',
    name: 'range',
    color1: 'red',
    color2: 'LightRed',
    fill: "none",
    show_center: false,
    get xmin() { return (vm.default_value[0] == null) ? xrange[0] : vm.default_value[0] },
    get xmax() { return (vm.default_value[1] == null) ? xrange[1] : vm.default_value[1] },
    get ymin() { return (vm.default_value[2] == null) ? yrange[0] : vm.default_value[2] },
    get ymax() { return (vm.default_value[3] == null) ? yrange[1] : vm.default_value[3] },
    set xmin(x) { vm.$set(value, 0, x) },
    set xmax(x) { vm.$set(value, 1, x) },
    set ymin(x) { vm.$set(value, 2, x) },
    set ymax(x) { vm.$set(value, 3, x) }
  }
  return new rectangleInteractor(opts, null, null, d3);
}

function add_ellipse_interactor(vm, xrange, yrange) {
  let value = this.local_value;
  var opts = {
    type: 'Ellipse',
    name: 'range',
    color1: 'red',
    color2: 'LightRed',
    fill: "none",
    show_center: true,
    show_points: true,
    get cx() { return (vm.default_value[0] == null) ? (xrange[0] + xrange[1]) / 2 : vm.default_value[0] },
    get cy() { return (vm.default_value[1] == null) ? (yrange[0] + yrange[1]) / 2 : vm.default_value[1] },
    get rx() { return (vm.default_value[2] == null) ? Math.abs(xrange[1] - xrange[0]) / 2 : vm.default_value[2] },
    get ry() { return (vm.default_value[3] == null) ? Math.abs(yrange[1] - yrange[0]) / 2 : vm.default_value[3] },
    set cx(x) { vm.$set(value, 0, x) },
    set cy(x) { vm.$set(value, 1, x) },
    set rx(x) { vm.$set(value, 2, x) },
    set ry(x) { vm.$set(value, 3, x) }
  }
  return new ellipseInteractor(opts, null, null, d3);
}

function add_sector_interactor(vm, xrange, yrange) {
  let value = vm.local_value;
  var opts = {
    type: 'Sector',
    name: 'sector',
    color1: 'red',
    color2: 'orange',
    show_lines: true,
    show_center: false,
    mirror: true,
    get cx() { return (vm.default_value[0] == null) ? 0 : vm.default_value[0] },
    get cy() { return (vm.default_value[1] == null) ? 0 : vm.default_value[1] },
    get angle_offset() { return ((vm.default_value[2] == null) ? 0 : vm.default_value[2]) * Math.PI / 180.0 },
    get angle_range() { return ((vm.default_value[3] == null) ? 90 : vm.default_value[3]) * Math.PI / 180.0 },
    set cx(x) { vm.$set(value, 0, x) },
    set cy(x) { vm.$set(value, 1, x) },
    set angle_offset(x) { vm.$set(value, 2, x * 180.0 / Math.PI) },
    set angle_range(x) { vm.$set(value, 3, x * 180.0 / Math.PI) }
  }
  return new angleSliceInteractor(opts, null, null, d3);
}

function add_sector_centered_interactor(vm, xrange, yrange) {
  let value = vm.local_value;
  var opts = {
    type: 'Sector',
    name: 'sector',
    color1: 'red',
    color2: 'orange',
    show_lines: true,
    show_center: false,
    mirror: true,
    cx: 0,
    cy: 0,
    get angle_offset() { return ((vm.default_value[0] == null) ? 0 : vm.default_value[0]) * Math.PI / 180.0 },
    get angle_range() { return ((vm.default_value[1] == null) ? 90 : vm.default_value[1]) * Math.PI / 180.0 },
    set angle_offset(x) { vm.$set(value, 0, x * 180.0 / Math.PI) },
    set angle_range(x) { vm.$set(value, 1, x * 180.0 / Math.PI) }
  }
  return new angleSliceInteractor(opts, null, null, d3);
}

function isEmpty(value, index) {
  return (value == null) || (value[index] == null) || (value[index] == "")
}