import {
  d3,
  extend,
  rectangleInteractor,
  ellipseInteractor,
  xSliceInteractor,
  ySliceInteractor
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
    return {
      local_value: extend(true, [], this.value || this.field.default),
      axes_lookups: {
        'x': ['xmin', 'xmax'],
        'y': ['ymin', 'ymax'],
        'xy': ['xmin', 'xmax', 'ymin', 'ymax'],
        'ellipse': ['cx', 'cy', 'rx', 'ry'],
        'sector_centered': ['angle_offset', 'angle_width']
      },
      interactors: []
    }
  },
  computed: {
    axes() {
      return this.axes_lookups[this.axis_str] || [];
    },
    axis_str() {
      return this.field.typeattr.axis || "";
    }
  },
  methods: {
    changed(updateInteractors = true) {
      this.$emit('change', this.field.id, this.local_value.map(x => +x));
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
      let xrange = chart.x().domain();
      let yrange = chart.y().domain();
      let interactor = interactorConnectors[this.axis_str](this, xrange, yrange);
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
    get x1() { return (value[0] == null || value[0] == "") ? xrange[0] : value[0] },
    get x2() { return (value[1] == null || value[1] == "") ? xrange[1] : value[1] },
    set x1(x) { vm.$set(value, 0, x); vm.changed(false); },
    set x2(x) { vm.$set(value, 1, x); vm.changed(false); }
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
    get y1() { return (value[0] == null || value[0] == "") ? yrange[0] : value[0] },
    get y2() { return (value[1] == null || value[1] == "") ? yrange[1] : value[1] },
    set y1(x) { vm.$set(value, 0, x); vm.changed(false); },
    set y2(x) { vm.$set(value, 1, x); vm.changed(false); }
  }
  return new ySliceInteractor(opts, null, null, d3);
}

function add_xy_interactor(vm, xrange, yrange) {
  let value = vm.local_value;
  var opts = {
    type: 'Rectangle',
    name: 'range',
    color1: 'red',
    color2: 'LightRed',
    fill: "none",
    show_center: false,
    get xmin() { return (value[0] == null || value[0] == "") ? xrange[0] : value[0] },
    get xmax() { return (value[1] == null || value[1] == "") ? xrange[1] : value[1] },
    get xmin() { return (value[2] == null || value[2] == "") ? yrange[0] : value[2] },
    get xmax() { return (value[2] == null || value[3] == "") ? yrange[1] : value[3] },
    set xmin(x) { vm.$set(value, 0, x); vm.changed(false); },
    set xmax(x) { vm.$set(value, 1, x); vm.changed(false); },
    set ymin(x) { vm.$set(value, 2, x); vm.changed(false); },
    set ymax(x) { vm.$set(value, 3, x); vm.changed(false); }
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
    get cx() { return (value[0] == null || value[0] == "") ? (xrange[0] + xrange[1]) / 2 : value[0] },
    get cy() { return (value[1] == null || value[1] == "") ? (yrange[0] + yrange[1]) / 2 : value[1] },
    get rx() { return (value[2] == null || value[2] == "") ? (xrange[0] + xrange[1]) / 2 : value[2] },
    get ry() { return (value[2] == null || value[3] == "") ? (yrange[0] + yrange[1]) / 2 : value[3] },
    set cx(x) { vm.$set(value, 0, x); vm.changed(false); },
    set cy(x) { vm.$set(value, 1, x); vm.changed(false); },
    set rx(x) { vm.$set(value, 2, x); vm.changed(false); },
    set ry(x) { vm.$set(value, 3, x); vm.changed(false); }
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
    get cx() { return (value[0] == null || value[0] == "") ? 0 : value[0] },
    get cy() { return (value[1] == null || value[1] == "") ? 0 : value[1] },
    get angle_offset() { return ((value[2] == null || value[2] == "") ? 0 : value[2]) * Math.PI / 180.0 },
    get angle_range() { return ((value[2] == null || value[3] == "") ? 90 : value[3]) * Math.PI / 180.0 },
    set cx(x) { vm.$set(value, 0, x); vm.changed(false); },
    set cy(x) { vm.$set(value, 1, x); vm.changed(false); },
    set angle_offset(x) { vm.$set(value, 2, x * 180.0 / Math.PI); vm.changed(false); },
    set angle_range(x) { vm.$set(value, 3, x * 180.0 / Math.PI); vm.changed(false); }
  }
  return new angleSliceInteractor.default(opts);
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
    get angle_offset() { return ((value[0] == null || value[0] == "") ? 0 : value[0]) * Math.PI / 180.0 },
    get angle_range() { return ((value[1] == null || value[1] == "") ? 90 : value[1]) * Math.PI / 180.0 },
    set angle_offset(x) { vm.$set(value, 0, x * 180.0 / Math.PI); vm.changed(false); },
    set angle_range(x) { vm.$set(value, 1, x * 180.0 / Math.PI); vm.changed(false); }
  }
  return new angleSliceInteractor.default(opts);
}