import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import BoardCanvas from './BoardCanvas.vue';

describe('BoardCanvas', () => {
  it('renders an SVG with the board image as background', () => {
    const wrapper = mount(BoardCanvas);
    const svg = wrapper.find('svg');
    expect(svg.exists()).toBe(true);
    expect(svg.attributes('viewBox')).toBe('0 0 1920 1920');
    expect(wrapper.find('image').exists()).toBe(true);
  });

  it('does not render debug dots by default', () => {
    const wrapper = mount(BoardCanvas);
    expect(wrapper.findAll('text').length).toBe(0);
  });

  it('renders 116 numbered dots when debug=true', () => {
    const wrapper = mount(BoardCanvas, { props: { debug: true } });
    // 68 circuit + 4 colors × (8 home stretch + 4 jail slots) = 116
    expect(wrapper.findAll('text').length).toBe(116);
  });
});
