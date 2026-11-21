export interface ExternalLinkItem {
  id: string;
  label: string;
  url: string;
  description: string;
}

/**
 * Centralized external navigation links configuration.
 * When clicked in the Navbar, these open the target website in a new tab.
 */
export const EXTERNAL_LINKS: Record<'imagine' | 'digitize', ExternalLinkItem> = {
  imagine: {
    id: 'imagine',
    label: 'Imagine',
    url: 'https://collectmangadataset.vercel.app/',
    description: 'Generative AI Visual Storyboards & Conceptual Artwork'
  },
  digitize: {
    id: 'digitize',
    label: 'Digitize',
    url: 'https://manuscript-ai-two.vercel.app/',
    description: 'Manuscript Digitization & Archival Processing'
  }
};
