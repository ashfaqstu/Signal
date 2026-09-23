export interface SpectrumStage {
  id: number;
  title: string;
  formula: string;
  layer: string;
}

export const SPECTRUM_STAGES: SpectrumStage[] = [
  {
    id: 0,
    title: "1. Problem",
    formula: "f_2(x,y) = f_1(x - x_0,\\; y - y_0)",
    layer: "f₁ | f₂",
  },
  {
    id: 1,
    title: "2. Shift Theorem",
    formula: "F_2(u,v) = F_1(u,v)\\, e^{-j2\\pi(u x_0 + v y_0)}",
    layer: "|F₁|",
  },
  {
    id: 2,
    title: "3. Magnitude",
    formula: "\\left|F_2\\right| = \\left|F_1\\right|",
    layer: "phase swap",
  },
  {
    id: 3,
    title: "4. Cross-Power",
    formula: "R = \\frac{F_2 \\overline{F_1}}{\\left|F_2 \\overline{F_1}\\right|}",
    layer: "∠R",
  },
  {
    id: 4,
    title: "5. Delta",
    formula: "\\mathcal{F}^{-1}\\{R\\} = \\delta(x - x_0,\\; y - y_0)",
    layer: "r(x,y)",
  },
  {
    id: 5,
    title: "6. Spike",
    formula: "(\\hat d_y, \\hat d_x) = \\arg\\max\\; r \\pmod{H, W}",
    layer: "residual",
  },
  {
    id: 6,
    title: "7. Fourier-Mellin",
    formula: "|F| \\text{ rotates with } f \\text{ and scales as } 1/s",
    layer: "log-polar A",
  },
];
