import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import PieceToken from './PieceToken.vue';
import { Color, PieceState } from 'src/types/domain';
import { makePiece } from 'src/test-utils/factories';

describe('PieceToken', () => {
  it('renders a circle when the piece is ON_BOARD', () => {
    const wrapper = mount(PieceToken, {
      props: {
        piece: makePiece({ state: PieceState.ON_BOARD, circuit_position: 10 }),
        color: Color.RED,
        selectable: false,
      },
    });
    expect(wrapper.find('circle').exists()).toBe(true);
  });

  it('does not render for CROWNED pieces', () => {
    const wrapper = mount(PieceToken, {
      props: {
        piece: makePiece({ state: PieceState.CROWNED }),
        color: Color.RED,
        selectable: false,
      },
    });
    expect(wrapper.find('circle').exists()).toBe(false);
  });

  it('adds selectable class when selectable', () => {
    const wrapper = mount(PieceToken, {
      props: {
        piece: makePiece({ state: PieceState.ON_BOARD, circuit_position: 10 }),
        color: Color.RED,
        selectable: true,
      },
    });
    expect(wrapper.classes()).toContain('selectable');
  });
});
