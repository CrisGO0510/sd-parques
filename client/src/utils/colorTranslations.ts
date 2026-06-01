import type { Color } from 'src/types/domain';
import { Color as ColorEnum } from 'src/types/domain';

export const COLOR_LABELS: Record<Color, string> = {
  [ColorEnum.RED]: 'Rojo',
  [ColorEnum.BLUE]: 'Azul',
  [ColorEnum.GREEN]: 'Verde',
  [ColorEnum.YELLOW]: 'Amarillo',
};

/**
 * Traduce un color del enum al español
 */
export function colorToLabel(color: Color | null | undefined): string {
  if (!color) return 'Sin color';
  return COLOR_LABELS[color] ?? color;
}
