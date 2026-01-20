export const DropdownMenu = {
  name: 'dropdown-menu',
  props: {
    label: { type: String, default: 'Menu' }
  },
  data() {
    return {
      open: false
    };
  },
  methods: {
    toggle() {
      this.open = !this.open;
    },
    close() {
      this.open = false;
    },
    handleOutsideClick(e) {
      if (!this.$el.contains(e.target)) {
        this.open = false;
      }
    }
  },
  mounted() {
    document.addEventListener('click', this.handleOutsideClick);
  },
  beforeDestroy() {
    document.removeEventListener('click', this.handleOutsideClick);
  },
  template: `
    <div class="dropdown" @keydown.esc="close">
      <button class="btn btn-secondary dropdown-toggle" type="button" @click="toggle">
        {{ label }}
      </button>
      <div class="dropdown-menu" :class="{ show: open }">
        <slot></slot>
      </div>
    </div>
  `
};