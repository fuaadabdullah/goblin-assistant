// Type shim for lucide-react icons that are missing from the generated .d.ts exports
// See: https://github.com/lucide-icons/lucide/issues/new — namespace re-export bug in v0.469.0
import type { LucideProps } from 'lucide-react';
import type { ForwardRefExoticComponent, RefAttributes } from 'react';

declare module 'lucide-react' {
  export const Code: ForwardRefExoticComponent<
    Omit<LucideProps, 'ref'> & RefAttributes<SVGSVGElement>
  >;
  export const CodeXml: ForwardRefExoticComponent<
    Omit<LucideProps, 'ref'> & RefAttributes<SVGSVGElement>
  >;
  export const Square: ForwardRefExoticComponent<
    Omit<LucideProps, 'ref'> & RefAttributes<SVGSVGElement>
  >;
}
