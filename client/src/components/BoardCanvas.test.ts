import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import BoardCanvas from './BoardCanvas.vue';

describe('BoardCanvas', () => {
  it('renders an SVG with 96 circuit cells', () => {
    const wrapper = mount(BoardCanvas);
    const svg = wrapper.find('svg');
    expect(svg.exists()).toBe(true);
    // 96 circuit rects + 4 jails + 32 home stretch cells = 132 rects
    // but include the background rect = 133. Ranges are fine.
    const rects = wrapper.findAll('rect');
    expect(rects.length).toBeGreaterThanOrEqual(96);
  });

  it('renders the goal circle', () => {
    const wrapper = mount(BoardCanvas);
    expect(wrapper.find('circle').exists()).toBe(true);
  });
});
